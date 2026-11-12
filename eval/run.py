"""Eval runner (PRD 13): every case in eval/cases.yaml through the real API (FastAPI TestClient over data/recipes.db),
programmatic assertions on the JSON the UI gets, then eval/REPORT.md.

Run: python eval/run.py            live: the real LLM when GEMINI_API_KEY is set (answers are cached)
     python eval/run.py --replay   cache only (LLM_REPLAY=1): no quota, no network; a cache miss behaves like an
                                   LLM outage (rule parser), so a replay of a live run takes the same paths
Exit 1 if any assertion fails. Assertions re-check results with their own SQL (recipe_tags, ingredient_lines,
unverified), not with the code under test; stats are compared with eval/oracle.py's pure-Python numbers
(eval/oracle_values.json, written by every oracle run).
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
EVAL = ROOT / "eval"


def setup(replay: bool):
    """Import the app after LLM_REPLAY is set (llm reads it per call; set early anyway)."""
    if replay:
        os.environ["LLM_REPLAY"] = "1"
    from fastapi.testclient import TestClient  # noqa: E402
    from app import api, stats, substitute  # noqa: E402
    return TestClient, api, stats, substitute


class Checker:
    """Every assertion key of cases.yaml: check(key, value, response, ctx) -> '' or a failure message."""

    def __init__(self, con, ds, stats, substitute, oracle):
        self.con, self.ds, self.stats, self.sub, self.oracle = con, ds, stats, substitute, oracle

    def ids(self, p):
        return [c["id"] for c in p.get("cards", [])]

    def q(self, sql, args=()):
        return {r for r, in self.con.execute(sql, args)}

    def tagged(self, ids, tag, levels=("contains",)):
        ph = ",".join("?" * len(ids))
        return self.q(f"SELECT recipe_id FROM recipe_tags WHERE tag = ? AND level IN ({','.join('?' * len(levels))}) "
                      f"AND recipe_id IN ({ph})", (tag, *levels, *ids)) if ids else set()

    def unverified(self, ids, tag):
        ph = ",".join("?" * len(ids))
        return self.q(f"SELECT recipe_id FROM unverified WHERE tag = ? AND recipe_id IN ({ph})", (tag, *ids)) if ids else set()

    def check(self, key, v, r, ctx) -> str:
        p, ids = r["payload"], self.ids(r["payload"])
        parts = p.get("parts") or []
        part = parts[0] if parts else {}
        a = p.get("adaptation")
        tags = lambda: v if isinstance(v, list) else [v]
        if key == "type":
            return "" if p["type"] == v else f"type is {p['type']}, expected {v}"
        if key == "total_gt":
            return "" if p.get("total", 0) > v else f"total {p.get('total')} is not > {v}"
        if key == "total_eq":
            return "" if p.get("total") == v else f"total {p.get('total')} != {v}"
        if key == "n_cards_ge":
            return "" if len(ids) >= v else f"{len(ids)} cards < {v}"
        if key == "ids_exist":
            rid = [p["recipe"]["id"]] if p["type"] == "recipe" else []
            got = ids + rid
            ok = self.q(f"SELECT id FROM recipes WHERE valid = 1 AND id IN ({','.join('?' * len(got))})", got) if got else set()
            return "" if got and ok == set(got) else f"ids not valid recipes: {sorted(set(got) - ok)[:3]}"
        if key == "max_steps_le":
            bad = [c["id"] for c in p["cards"] if c["n_steps"] > v]
            return "" if not bad else f"{len(bad)} results have more than {v} steps"
        if key == "all_results_lack_tag":
            bad = {t: self.tagged(ids, t) for t in tags()}
            bad = {t: b for t, b in bad.items() if b}
            return "" if not bad else f"results contain {', '.join(bad)} (e.g. {next(iter(next(iter(bad.values()))))})"
        if key == "strict_results_lack_tag":
            bad = self.tagged(ids, v, ("contains", "may_contain")) | self.unverified(ids, v)
            return "" if not bad else f"{len(bad)} results contain, may contain or can't be verified for {v}"
        if key == "verified_before_unverified":
            unv = self.unverified(ids, v)
            flags = [i in unv for i in ids]
            return "" if flags == sorted(flags) else "an unverified result is ranked above a verified one"
        if key == "all_results_lack_ingredient":
            t = self.stats.term(v, self.ds)
            ph = ",".join("?" * len(ids))
            bad = self.q(f"SELECT recipe_id FROM ingredient_lines WHERE is_alt = 0 AND is_header = 0 AND "
                         f"(canonical = ? OR family = ?) AND recipe_id IN ({ph})", (t.canonical, t.family, *ids)) if ids else set()
            return "" if not bad else f"{len(bad)} results contain {v}"
        if key == "all_results_lack_ingredient_broad":  # family + its broad list ('no sugar' also drops marshmallow)
            from app.normalize import BROAD
            t = self.stats.term(v, self.ds)
            names = [t.family, *BROAD.get(t.family, [])]
            ph, nh = ",".join("?" * len(ids)), ",".join("?" * len(names))
            bad = self.q(f"SELECT recipe_id FROM ingredient_lines WHERE is_alt = 0 AND is_header = 0 AND (family IN ({nh}) "
                         f"OR canonical IN ({nh})) AND recipe_id IN ({ph})", (*names, *names, *ids)) if ids else set()
            return "" if not bad else f"{len(bad)} results contain {v} (broad)"
        if key == "dropped":
            got = [d["item"] for d in p.get("dropped", [])]
            miss = [x for x in v if not any(x in g for g in got)]
            return "" if not miss else f"{miss} not dropped (dropped: {got})"
        if key == "recipe_is_result":
            prev = ctx.get("last_cards") or []
            want = prev[v - 1] if len(prev) >= v else None
            got = p.get("recipe", {}).get("id")
            return "" if want and got == want else f"opened {got}, result #{v} was {want}"
        if key == "stat_equals_oracle":
            got = {c["label"]: c["value"] for c in p.get("calc", [])}
            bad = []
            for mode, path in v.items():
                exp = self.oracle
                for k in path.split("."):
                    exp = exp[k]
                if got.get(mode) != exp:
                    bad.append(f"{mode} {got.get(mode)} != oracle {exp}")
            return "; ".join(bad)
        if key == "rank_equals_oracle":
            return "" if ids == self.oracle[v] else f"ids {ids} != oracle {self.oracle[v]}"
        if key == "no_match":
            return "" if (p.get("total") == 0) == v else f"total is {p.get('total')}"
        if key == "alternatives_flagged":
            alts = p.get("alternatives") or []
            return "" if alts and all(x["violates"] for x in alts) else "no flagged alternatives"
        if key == "match_has_qty_chip":
            return "" if any(ch["kind"] in ("ok", "violation") for c in p["cards"] for ch in c["chips"]) else \
                "no quantity check on any result"
        if key == "refusal":
            return "" if (p["type"] == "unsupported") == v else f"type is {p['type']}, not a refusal"
        if key == "reply_contains":
            text = (r["reply_md"] + " " + (r.get("voice") or "")).lower()
            miss = [w for w in v if w.lower() not in text]
            return "" if not miss else f"reply lacks {miss}"
        if key == "state_tags_include":
            miss = [t for t in v if t not in r["state"]["exclude_tags"]]
            return "" if not miss else f"restrictions lack {miss} (have {r['state']['exclude_tags']})"
        if key == "state_tags_exclude":
            extra = [t for t in v if t in r["state"]["exclude_tags"]]
            return "" if not extra else f"restrictions still have {extra}"
        if key == "sub_strength_in":
            return "" if part.get("strength") in v else f"strength {part.get('strength')} not in {v}"
        if key == "sub_chosen_not":
            return "" if part.get("chosen") not in v else f"chose {part.get('chosen')}"
        if key == "sub_rejected":
            names = [x["name"] for x in part.get("rejected", [])]
            miss = [n for n in v if n not in names]
            return "" if not miss else f"{miss} not rejected (rejected: {names[:5]})"
        if key == "sub_cited_ids_valid":
            return self.cited(parts)
        if key == "sub_dataset_only":
            vocab = self.q("SELECT canonical FROM vocab WHERE recipe_count >= ?", (self.ds_min,))
            bad = [c["name"] for pt in parts for c in pt["candidates"]
                   if c["kind"] != "user" and c["name"] not in vocab and c["name"] not in self.sub.DECLARED]
            return "" if not bad else f"not dataset ingredients: {bad}"
        if key == "sub_steps_valid":
            if not a:
                return "no adaptation"
            bad = [s["n"] for s in a["steps"] if not s["changed"] and s["text"] != s["old"]]
            return "" if not bad else f"steps {bad} changed but not marked"
        if key == "sub_gate_fails":
            return "" if a and a["gate"] else "the final gate passed (expected a failure)"
        if key == "sub_gate_passes":
            return "" if a and not a["gate"] else f"gate: {(a or {}).get('gate')}"
        if key == "sub_question":
            return "" if bool(p.get("question")) == v else f"question: {p.get('question')!r}"
        if key == "sub_adapted":
            return "" if bool(a) == v else f"adaptation {'missing' if v else 'built'}"
        if key == "llm_calls_le":
            n = r["planner"]["calls"] + r["planner"]["cache_hits"]
            return "" if n <= v else f"{n} LLM calls"
        return f"unknown assertion {key}"

    def cited(self, parts) -> str:
        """Every cited id (chosen candidate's supporting + explicit ids) is valid, lacks the removed item and
        contains the candidate: own SQL, not evidence.cited."""
        bad = []
        for pt in parts:
            c = next((x for x in pt["candidates"] if x["name"] == pt["chosen"]), None)
            if not c:
                continue
            spec = self.sub.spec_for(pt["item"], self.ds)
            for rid in set(c["ids"] + c["explicit"]):
                if spec.tag:
                    has = self.q("SELECT recipe_id FROM recipe_tags WHERE recipe_id = ? AND tag = ? AND level = "
                                 "'contains'", (rid, spec.tag))
                else:
                    col, val = ("family", spec.family) if spec.canonical == spec.family else ("canonical", spec.canonical)
                    has = self.q(f"SELECT recipe_id FROM ingredient_lines WHERE recipe_id = ? AND is_alt = 0 AND "
                                 f"{col} = ?", (rid, val))
                uses = self.q("SELECT recipe_id FROM ingredient_lines WHERE recipe_id = ? AND is_alt = 0 AND (canonical "
                              "= ? OR family = ? OR canonical LIKE ?)", (rid, c["name"], c["name"], f"% {c['name']}"))
                if has or not uses:
                    bad.append(rid)
        return "" if not bad else f"{len(bad)} cited ids fail the re-check: {bad[:3]}"


def pct(xs, q):
    return round(statistics.quantiles(xs, n=10)[q // 10 - 1]) if len(xs) >= 2 else (xs[0] if xs else 0)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true", help="LLM cache only (no network, no quota)")
    args = ap.parse_args()
    TestClient, api, stats, substitute = setup(args.replay)
    from app.config import VOCAB_MIN
    cases = yaml.safe_load((EVAL / "cases.yaml").read_text(encoding="utf-8"))
    oracle = json.loads((EVAL / "oracle_values.json").read_text(encoding="utf-8"))
    api.RATE = 10_000
    rows, turns = [], []
    with TestClient(api.app) as client:
        api.APP["sub_warm"].join()  # latency is measured after the startup warm-up, like a deployed server
        ck = Checker(api.APP["con"], api.APP["ds"], stats, substitute, oracle)
        ck.ds_min = VOCAB_MIN
        fp = client.get("/api/health").json().get("fingerprint", {})
        for case in cases:
            sid, ctx, fails = None, {}, []
            for i, turn in enumerate(case["turns"], 1):
                t0 = time.perf_counter()
                if "say" in turn:
                    res = client.post("/api/chat", json={"session_id": sid, "message": turn["say"]})
                else:
                    res = client.patch(f"/api/session/{sid}/state", json=turn["patch"])
                wall = round((time.perf_counter() - t0) * 1000)
                if res.status_code != 200:
                    fails.append(f"turn {i}: HTTP {res.status_code}")
                    break
                r = res.json()
                sid = r["session_id"]
                for key, v in (turn.get("expect") or {}).items():
                    try:
                        msg = ck.check(key, v, r, ctx)
                    except Exception as e:  # noqa: BLE001  (a crashing check is a failure, not a crash)
                        msg = f"check crashed: {type(e).__name__}: {e}"
                    if msg:
                        fails.append(f"turn {i} `{key}`: {msg}")
                if r["payload"]["type"] in ("search", "match"):
                    ctx["last_cards"] = ck.ids(r["payload"])
                pl = r["planner"]
                turns.append({"case": case["id"], "turn": i, "type": r["payload"]["type"], "ms": wall,
                              "server_ms": pl["turn_ms"], "calls": pl["calls"], "cache_hits": pl["cache_hits"],
                              "errors": pl["errors"], "planner": pl["label"]})
            rows.append((case, fails))
            print(f"{'PASS' if not fails else 'FAIL'}  {case['id']}" + "".join(f"\n      {f}" for f in fails))
    write_report(rows, turns, args.replay, fp)
    sys.exit(1 if any(f for _, f in rows) else 0)


def lat(turns, pick=lambda t: True):
    xs = [t["ms"] for t in turns if pick(t)]
    return f"{pct(xs, 50):,} / {pct(xs, 90):,} ms (n={len(xs)})" if xs else "–"


def write_report(rows, turns, replay: bool, fp: dict) -> None:
    """eval/REPORT.md: pass/fail table, failures, latency, LLM calls per turn, baseline, notes."""
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    n_pass = sum(not f for _, f in rows)
    stats_now = {"p50_p90_all": lat(turns), "p50_p90_substitute": lat(turns, lambda t: t["type"] == "substitute"),
                 "calls_mean": round(statistics.mean(t["calls"] + t["cache_hits"] for t in turns), 2),
                 "calls_max": max(t["calls"] + t["cache_hits"] for t in turns),
                 "llm_errors": sum(len(t["errors"]) for t in turns), "turns": len(turns),
                 "when": datetime.now().strftime("%Y-%m-%d %H:%M")}
    live_file = EVAL / "live_stats.json"
    if not replay:
        live_file.write_text(json.dumps(stats_now, indent=1), encoding="utf-8")
    live = json.loads(live_file.read_text(encoding="utf-8")) if live_file.exists() else None
    md = ["# Evaluation report", "",
          f"Mode: **{'replay (LLM cache only)' if replay else 'live LLM'}** · {stats_now['when']} · commit `{commit}` · "
          f"DB fingerprint `{json.dumps(fp, sort_keys=True)}`", "",
          f"**{n_pass} / {len(rows)} cases pass** ({sum(len(c['turns']) for c, _ in rows)} turns). Every check is "
          "programmatic (eval/cases.yaml, eval/run.py): results are re-checked with independent SQL, stats against "
          "eval/oracle.py's pure-Python recount.", "",
          "| case | result | what failed |", "|---|---|---|"]
    md += [f"| {c['name']} | {'✅ pass' if not f else '❌ fail'} | {'; '.join(f)[:300] if f else ''} |" for c, f in rows]
    md += ["", "## Latency and LLM calls", "",
           "Server-side wall time per turn (TestClient, same process), measured after the startup warm-up.", "",
           "| run | all turns p50 / p90 | substitution turns p50 / p90 | LLM calls per turn (mean / max) | LLM errors |",
           "|---|---|---|---|---|"]
    for label, s in (("this run" + (" (replay)" if replay else " (live)"), stats_now), ) + (
            (("last live run, " + live["when"], live),) if replay and live else ()):
        md.append(f"| {label} | {s['p50_p90_all']} | {s['p50_p90_substitute']} | {s['calls_mean']} / {s['calls_max']} | "
                  f"{s['llm_errors']} |")
    md += ["", "In a replay every LLM answer comes from the cache (0 ms), so replay latency is the engine alone.", "",
           "Slowest turns this run: " + "; ".join(f"{t['case']} #{t['turn']} {t['ms']:,} ms ({t['planner']}"
                                                 + (f", LLM errors: {', '.join(t['errors'])}" if t["errors"] else "") + ")"
                                                 for t in sorted(turns, key=lambda t: -t["ms"])[:5]), ""]
    base = EVAL / "baseline.json"
    if base.exists():
        md += baseline_section(json.loads(base.read_text(encoding="utf-8")))
    notes = EVAL / "REPORT_NOTES.md"
    if notes.exists():
        md += ["", notes.read_text(encoding="utf-8").strip()]
    (EVAL / "REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote eval/REPORT.md: {n_pass}/{len(rows)} pass")


def baseline_section(b: dict) -> list[str]:
    """Side-by-side table from eval/baseline.json (eval/baseline_oneshot.py)."""
    out = ["## Baseline: the same questions to raw Gemini, no tools", "", b.get("summary", ""), "",
           "| question | raw LLM said | checked against the DB / oracle | Recipe Box |", "|---|---|---|---|"]
    for r in b["rows"]:
        out.append(f"| {r['question'][:70]} | {r['llm'][:160]} | {r['verdict']} | {r['ours'][:160]} |")
    return out


if __name__ == "__main__":
    main()
