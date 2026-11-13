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


def pct(xs, q):
    return round(statistics.quantiles(xs, n=10)[q // 10 - 1]) if len(xs) >= 2 else (xs[0] if xs else 0)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true", help="LLM cache only (no network, no quota)")
    args = ap.parse_args()
    TestClient, api, stats, substitute = setup(args.replay)
    from app.config import VOCAB_MIN
    from checks import Checker
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
