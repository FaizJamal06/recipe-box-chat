"""Raw-LLM baseline (PRD 13): the same questions to Gemini with no tools, its answers checked against the DB and the
oracle, side by side with Recipe Box. Writes eval/baseline.json; eval/run.py renders it into REPORT.md.

The model gets a fair description of the dataset (sources, size, ID format) and must answer in JSON
{answer, numbers, recipe_ids}. Checks: every recipe id must exist in data/recipes.db (and satisfy the question's
constraint where there is one); every number is compared with eval/oracle_values.json. Answers go through the
app's LLM cache, so a second run (or --replay) costs no quota.
Run: python eval/baseline_oneshot.py [--replay]
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
EVAL = ROOT / "eval"

SYSTEM = ("You answer questions about a recipe dataset: 125,164 recipe records scraped from AllRecipes, Epicurious and "
          "Food Network (title, ingredient lines, instructions). Recipe ids look like 'ar:<32 chars>', "
          "'epi:<32 chars>' or 'fn:<32 chars>'. Answer as precisely as you can. Return JSON: answer (short text), "
          "numbers (every number you state), recipe_ids (every recipe id you cite).")
SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}, "numbers": {"type": "array", "items": {"type": "number"}},
          "recipe_ids": {"type": "array", "items": {"type": "string"}}}, "required": ["answer", "numbers", "recipe_ids"]}
QUESTIONS = [  # (key, question, constraint on cited ids)
    ("size", "How many recipes are in the dataset, and how many of them are valid (have a title, ingredients and "
             "instructions)?", None),
    ("demo2", "How many recipes contain both garlic and onion? What percentage of the dataset is that?", None),
    ("demo3", "Among recipes containing tomato, which five have the fewest instruction steps? Give their recipe ids.",
     None),
    ("penne", "Find a penne pasta recipe without dairy. Give its recipe id.", ("lacks", "dairy")),
    ("banana", "Which recipes in the dataset are egg-free banana breads that use applesauce instead of eggs? Give "
               "recipe ids.", ("lacks", "egg")),
    ("match", "I have eggs, onions, tomatoes, and rice. Suggest five recipes using as many as possible, no peanuts, "
              "at most six steps. Give recipe ids.", ("lacks", "peanut")),
]


def ours(con, ds, key: str, q: str) -> str:
    """Recipe Box's answer to the same question (the full system, LLM planner through the cache): numbers or ids."""
    from app.session import Session
    s = Session(con, ds, use_llm=True)
    t = s.respond(q)
    r = t.result
    if key == "size":
        return f"{ds.total:,} records, {ds.valid:,} valid"
    if key == "demo2":
        return "; ".join(f"{x.mode} {x.value:,} = {100 * x.value / x.denominator:.2f}%" for x in r)
    ids = (r.value if key == "demo3" else [h.id for h in getattr(r, "hits", [])] or [x.id for x in getattr(r, "rows", [])])
    return f"{len(ids)} ids, all in the DB: " + ", ".join(f"`{i}`" for i in ids[:3]) + (" …" if len(ids) > 3 else "")


def verdict(con, key: str, a: dict, oracle: dict, constraint) -> str:
    """Checks against the DB and the oracle, in words."""
    ids, nums = a.get("recipe_ids") or [], a.get("numbers") or []
    out = []
    if ids:
        real = {r for r, in con.execute(f"SELECT id FROM recipes WHERE id IN ({','.join('?' * len(ids))})", ids)}
        out.append(f"{len(ids) - len(real)} of {len(ids)} ids don't exist in the dataset")
        if constraint and real:
            bad = {r for r, in con.execute(f"SELECT recipe_id FROM recipe_tags WHERE tag = ? AND level = 'contains' "
                                           f"AND recipe_id IN ({','.join('?' * len(real))})", (constraint[1], *real))}
            out.append(f"{len(bad)} of the real ones contain {constraint[1]}")
    elif key in ("demo3", "penne", "banana", "match"):
        out.append("no recipe id given")
    if key == "size":
        out.append(f"oracle: {oracle['total']:,} records, {oracle['valid']:,} valid; "
                   f"{'matches' if oracle['valid'] in nums else 'no number matches the valid count'}")
    if key == "demo2":
        exp = [oracle["demo2"]["strict"], oracle["demo2"]["broad"]]
        out.append(f"oracle: strict {exp[0]:,}, broad {exp[1]:,}; "
                   f"{'a number matches' if set(exp) & set(nums) else 'no number matches'}")
    if key == "demo3":
        out.append(f"{len(set(ids) & set(oracle['demo3_ids']))} of 5 match the oracle's ids")
    return "; ".join(out)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    if ap.parse_args().replay:
        os.environ["LLM_REPLAY"] = "1"
    from app import config, llm  # noqa: E402
    from app.db import connect, load_dataset  # noqa: E402
    if hasattr(config, "load_env"):
        config.load_env()
    con = connect()
    ds = load_dataset(con)
    oracle = json.loads((EVAL / "oracle_values.json").read_text(encoding="utf-8"))
    rows, fabricated, wrong = [], 0, 0
    for key, q, constraint in QUESTIONS:
        try:
            a, _ = llm.generate_json(SYSTEM, q, SCHEMA, lambda d: d, timeout_ms=30_000, attempts=1, label="baseline")
        except llm.LLMError as e:
            a = {"answer": f"(no answer: {e})", "numbers": [], "recipe_ids": []}
        v = verdict(con, key, a, oracle, constraint)
        fabricated += v.startswith(tuple(f"{n} of" for n in range(1, 100)))
        wrong += "no number matches" in v or "0 of 5 match" in v
        llm_text = a["answer"] + (f" ids: {', '.join(a['recipe_ids'][:3])}" if a.get("recipe_ids") else "")
        rows.append({"question": q, "llm": llm_text.replace("|", "/").replace("\n", " "), "verdict": v,
                     "ours": ours(con, ds, key, q)})
        print(f"{key}: {v}")
    summary = (f"{fabricated} of {len(QUESTIONS)} answers cite recipe ids that don't exist in the dataset; "
               f"{wrong} answers state counts or rankings that don't match the oracle. Recipe Box answers every one "
               "from the DB (ids re-checked, counts equal to the oracle).")
    (EVAL / "baseline.json").write_text(json.dumps({"model": llm.model(), "summary": summary, "rows": rows}, indent=1),
                                        encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
