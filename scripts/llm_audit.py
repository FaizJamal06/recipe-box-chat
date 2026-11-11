"""Offline LLM audit of the allergen/diet rules. The LLM never decides anything at runtime: it only flags rows
for a human to review, and every answer is cached so the audit is reproducible.

  python scripts/llm_audit.py canonicals [--top 3000]   # which tags apply to the most common canonicals?
  python scripts/llm_audit.py sample [--n 150]          # label 150 fixed-seed recipes from their raw lines
  python scripts/llm_audit.py report                    # write docs/tag_audit.md from the cached answers

canonicals: ~100 names per call; LLM tags vs normalize.tags_for (the current lexicon), disagreements sorted by
recipe count. sample: ~10 recipes per call; LLM 'contains' vs our recipe_tags + unverified table (the rules as
built into data/recipes.db). A silent miss = the LLM says the recipe contains T but we neither tag it nor warn
(it would pass even strict mode). Free-tier Gemini is flaky: calls retry on 429/503/timeouts with backoff, and a
run that stops early resumes from the cache next time. LLM answers are stored in eval/llm_audit/*.json.
"""
import argparse
import hashlib
import json
import os
import random
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app import llm, safety  # noqa: E402
from app import normalize as nz  # noqa: E402
from app.config import DB  # noqa: E402

TAGS = list(safety.TAGS)
OUT = ROOT / "eval" / "llm_audit"
DEFS = """Tags (an ingredient or recipe CONTAINS a tag when, as normally bought or made, it includes):
dairy: milk of cows/goats/sheep or products (butter, cream, cheese, yogurt, ghee, whey); NOT plant milks or eggs.
egg: eggs or egg products (mayonnaise, meringue, egg pasta). peanut: peanuts. tree_nut: almond, cashew, walnut,
pecan, pistachio, hazelnut, macadamia, pine nut... (NOT coconut, nutmeg, water chestnut).
gluten: wheat, barley, rye, spelt and products (flour, bread, pasta, couscous, beer, malt, regular soy sauce).
soy: soybeans and products (soy sauce, tofu, miso, edamame). sesame: sesame seeds/oil, tahini.
meat: any land-animal flesh incl. poultry, and broths/fats made from it (lard, chicken stock). pork: pig products
(bacon, ham, lard). poultry: chicken, turkey, duck. fish: finfish and fish products (anchovy, fish sauce).
shellfish: crustaceans and molluscs. gelatin: animal gelatin. honey: honey. alcohol: alcoholic drinks or
ingredients (wine, beer, spirits, liqueur, mirin); NOT vinegar. root_veg: onion, garlic, leek, shallot, scallion,
chives, and root/tuber vegetables (potato, carrot, beet, radish, turnip, ginger, sweet potato).
'may_contain' = commonly contains it depending on brand or recipe (e.g. margarine: dairy)."""
L = {"type": "array", "items": {"type": "string", "enum": TAGS}}
ITEM = lambda key: {"type": "object", "properties": {key: {"type": "string"}, "contains": L, "may_contain": L},
                    "required": [key, "contains", "may_contain"]}
SCHEMAS = {"canonicals": {"type": "object", "properties": {"items": {"type": "array", "items": ITEM("name")}},
                          "required": ["items"]},
           "sample": {"type": "object", "properties": {"recipes": {"type": "array", "items": ITEM("key")}},
                      "required": ["recipes"]}}
_client = None


def ask(system: str, prompt: str, schema: dict, validate, tries: int = 6):
    """Cached structured call with retries; returns validate(parsed) or raises after `tries` failures."""
    global _client
    from google import genai
    from google.genai import types
    model = llm.model()
    key = "audit:" + hashlib.sha256(json.dumps([model, system, prompt, schema], sort_keys=True).encode()).hexdigest()
    con = llm._db()
    row = con.execute("SELECT response FROM cache WHERE key = ?", (key,)).fetchone()
    if row:
        return validate(json.loads(row[0]))
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(timeout=180_000))
    for i in range(tries):
        try:
            r = _client.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(
                system_instruction=system, response_mime_type="application/json", response_json_schema=schema,
                temperature=0))
            out = validate(json.loads(r.text or ""))
            con.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, model, r.text))
            con.commit()
            return out
        except Exception as e:  # noqa: BLE001 - 429 / 503 / timeout / invalid: back off and retry
            code = getattr(e, "code", "")
            wait = 60 if code == 429 else min(5 * 2 ** i, 60)
            print(f"   retry {i + 1}/{tries} after {type(e).__name__} {code}: {str(e)[:90]} (sleep {wait}s)")
            if code == 429 and "PerDay" in str(e):
                raise SystemExit("daily quota reached: re-run later, finished batches are cached")
            time.sleep(wait)
    raise RuntimeError("gave up on this batch")


def run_canonicals(con: sqlite3.Connection, top: int, size: int = 100) -> None:
    """LLM tags for the `top` canonicals by recipe count -> eval/llm_audit/canonicals.json."""
    names = [c for c, in con.execute("SELECT canonical FROM vocab ORDER BY recipe_count DESC, canonical LIMIT ?",
                                     (top,))]
    path, done = OUT / "canonicals.json", {}
    if path.exists():
        done = json.loads(path.read_text(encoding="utf-8"))
    system = "You label recipe ingredient names with allergen/diet tags. " + DEFS
    for b in range(0, len(names), size):
        batch = [n for n in names[b:b + size] if n not in done]
        if not batch:
            continue

        def ok(d, batch=batch):
            got = {x["name"].strip().lower(): x for x in d["items"] if x["name"].strip().lower() in batch}
            if len(got) < 0.9 * len(batch):
                raise ValueError(f"only {len(got)}/{len(batch)} names answered")
            return got
        prompt = "Label each ingredient name (as written):\n" + "\n".join(batch)
        try:
            got = ask(system, prompt, SCHEMAS["canonicals"], ok)
        except RuntimeError as e:
            print(f"batch {b // size}: {e}")
            continue
        done |= {n: {"contains": sorted(set(x["contains"])), "may_contain": sorted(set(x["may_contain"]))}
                 for n, x in got.items()}
        path.write_text(json.dumps(done, indent=0, sort_keys=True), encoding="utf-8")
        print(f"batch {b // size + 1}/{-(-len(names) // size)}: {len(done)} names labelled")


def sample_ids(con: sqlite3.Connection, n: int) -> list[str]:
    """Fixed-seed sample of valid recipe ids."""
    return sorted(random.Random(42).sample([r for r, in con.execute("SELECT id FROM recipes WHERE valid = 1 "
                                                                    "ORDER BY id")], n))


def raw_lines(con: sqlite3.Connection, rid: str) -> list[str]:
    ing = json.loads(con.execute("SELECT ingredients_raw FROM recipes WHERE id = ?", (rid,)).fetchone()[0])
    return [s for x in ing if isinstance(x, str) and (s := x.replace("ADVERTISEMENT", "").strip())]


def run_sample(con: sqlite3.Connection, n: int, size: int = 10) -> None:
    """LLM labels for a fixed-seed sample of recipes -> eval/llm_audit/sample.json."""
    path, done = OUT / "sample.json", {}
    if path.exists():
        done = json.loads(path.read_text(encoding="utf-8"))
    ids = sample_ids(con, n)
    system = ("You label recipes with allergen/diet tags from their ingredient lines only. A recipe CONTAINS a tag "
              "when a required ingredient has it (an 'or' alternative that avoids it does not count). " + DEFS)
    for b in range(0, len(ids), size):
        batch = [r for r in ids[b:b + size] if r not in done]
        if not batch:
            continue
        keys = {f"r{i + 1}": rid for i, rid in enumerate(batch)}

        def ok(d, keys=keys):
            got = {keys[x["key"]]: x for x in d["recipes"] if x["key"] in keys}
            if len(got) < len(keys):
                raise ValueError(f"only {len(got)}/{len(keys)} recipes answered")
            return got
        prompt = "\n\n".join(f"{k}:\n" + "\n".join(f"- {s}" for s in raw_lines(con, rid)) for k, rid in keys.items())
        try:
            got = ask(system, prompt, SCHEMAS["sample"], ok)
        except RuntimeError as e:
            print(f"batch {b // size}: {e}")
            continue
        done |= {rid: {"contains": sorted(set(x["contains"])), "may_contain": sorted(set(x["may_contain"]))}
                 for rid, x in got.items()}
        path.write_text(json.dumps(done, indent=0, sort_keys=True), encoding="utf-8")
        print(f"batch {b // size + 1}/{-(-len(ids) // size)}: {len(done)} recipes labelled")


def canonical_diff(con: sqlite3.Connection) -> list[tuple]:
    """[(recipes, canonical, tag, llm, ours)] where the LLM and the lexicon disagree."""
    labels = json.loads((OUT / "canonicals.json").read_text(encoding="utf-8"))
    counts = dict(con.execute("SELECT canonical, recipe_count FROM vocab"))
    rows = []
    for c, lab in labels.items():
        ours = dict(nz.tags_for(c))
        for t in TAGS:
            llm_lv = "contains" if t in lab["contains"] else "may_contain" if t in lab["may_contain"] else "-"
            if (llm_lv == "contains") != (ours.get(t) == "contains") and not (
                    llm_lv == "-" and ours.get(t) == "may_contain"):
                rows.append((counts.get(c, 0), c, t, llm_lv, ours.get(t, "-")))
    return sorted(rows, key=lambda r: (-r[0], r[1], r[2]))


def our_levels(con: sqlite3.Connection, rid: str) -> dict[str, str]:
    """{tag: contains | may_contain | unverified | alt} from data/recipes.db (no key = verified free)."""
    lv = dict(con.execute("SELECT tag, level FROM recipe_tags WHERE recipe_id = ?", (rid,)))
    for t, in con.execute("SELECT DISTINCT tag FROM unverified WHERE recipe_id = ?", (rid,)):
        if lv.get(t) not in ("contains", "may_contain"):
            lv[t] = "unverified"
    return lv


def accuracy(con: sqlite3.Connection) -> tuple[dict, list]:
    """Per tag: LLM positives, caught (contains), warned (may_contain/unverified), silent misses, false alarms."""
    labels = json.loads((OUT / "sample.json").read_text(encoding="utf-8"))
    stats = {t: {"positives": 0, "caught": 0, "warned": 0, "silent": [], "false_alarm": []} for t in TAGS}
    for rid, lab in labels.items():
        ours = our_levels(con, rid)
        for t in TAGS:
            o, s = ours.get(t), stats[t]
            if t in lab["contains"]:
                s["positives"] += 1
                if o == "contains":
                    s["caught"] += 1
                elif o in ("may_contain", "unverified"):
                    s["warned"] += 1
                else:
                    s["silent"].append(rid)
            elif o == "contains" and t not in lab["may_contain"]:
                s["false_alarm"].append(rid)
    return stats, list(labels)


def report(con: sqlite3.Connection) -> None:
    """docs/tag_audit.md: review notes (eval/llm_audit/review.md) + canonical disagreements + sample accuracy."""
    out = ["# Allergen / diet tag audit", "",
           "Generated by `python scripts/llm_audit.py report` from cached Gemini answers (`eval/llm_audit/*.json`). "
           f"Model: `{llm.model()}`. The LLM is an auditor here, never a runtime decision maker: rules in "
           "`backend/app/lexicon/tags.yaml` decide; the LLM only flags rows to review.", ""]
    review = OUT / "review.md"
    if review.exists():
        out += [review.read_text(encoding="utf-8").strip(), ""]
    if (OUT / "sample.json").exists():
        stats, ids = accuracy(con)
        reviewed = json.loads((OUT / "reviewed.json").read_text(encoding="utf-8")) if (OUT / "reviewed.json").exists() else {}
        out += ["## Measured accuracy on a fixed sample", "",
                f"{len(ids)} valid recipes (`random.Random(42)`), labelled by the LLM from their raw ingredient lines "
                "and compared with `recipe_tags` + `unverified` in `data/recipes.db`. **Silent miss** = the LLM says "
                "the recipe contains the tag, and we neither tag it nor warn, so it would pass even strict mode. "
                "**Warned** = shown with ⚠ (may contain / couldn't be verified), excluded in strict mode. "
                "LLM labels are not ground truth: every silent miss below was checked by hand (see review notes).", "",
                "| tag | LLM says contains | we tag contains | warned ⚠ | silent (raw) | silent after hand review | "
                "miss rate after review | false alarms |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for t, s in stats.items():
            real = [r for r in s["silent"] if f"{t}:{r}" not in reviewed]
            rate = f"{100 * len(real) / s['positives']:.1f}%" if s["positives"] else "–"
            out.append(f"| {t} | {s['positives']} | {s['caught']} | {s['warned']} | {len(s['silent'])} | {len(real)} | "
                       f"{rate} | {len(s['false_alarm'])} |")
        out += ["", "Raw silent misses judged LLM errors on hand review (`eval/llm_audit/reviewed.json`):", ""]
        out += [f"- {k.split(':', 1)[0]} `{k.split(':', 1)[1]}`: {v}" for k, v in reviewed.items()]
        out += ["", "Silent misses and false alarms by recipe id:", ""]
        for t, s in stats.items():
            if s["silent"] or s["false_alarm"]:
                out.append(f"- **{t}**: silent {', '.join(f'`{r}`' for r in s['silent']) or '–'}; false alarm "
                           f"{', '.join(f'`{r}`' for r in s['false_alarm']) or '–'}")
        out.append("")
    if (OUT / "canonicals.json").exists():
        rows = canonical_diff(con)
        n = len(json.loads((OUT / "canonicals.json").read_text(encoding="utf-8")))
        out += ["## Canonical audit: LLM vs lexicon disagreements", "",
                f"{n} most common canonicals labelled; {len(rows)} (canonical, tag) disagreements remain after the "
                "fixes, sorted by recipe count. `llm` / `ours` = contains, may_contain or – . Rows where the LLM says "
                "contains and we say – are possible misses; the reverse are possible over-tags. Reviewed: the top "
                "rows were fixed in the lexicon or kept on purpose (review notes); the tail is logged for review.", "",
                "| recipes | canonical | tag | llm | ours |", "|---:|---|---|---|---|"]
        out += [f"| {n_:,} | {c} | {t} | {a} | {b} |" for n_, c, t, a, b in rows]
    (ROOT / "docs" / "tag_audit.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote docs/tag_audit.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["canonicals", "sample", "report"])
    ap.add_argument("--top", type=int, default=3000)
    ap.add_argument("--n", type=int, default=150)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True)
    {"canonicals": lambda: run_canonicals(con, a.top), "sample": lambda: run_sample(con, a.n),
     "report": lambda: report(con)}[a.cmd]()


if __name__ == "__main__":
    main()
