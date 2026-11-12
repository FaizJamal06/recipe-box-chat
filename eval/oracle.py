"""Pure-Python (not SQL) recomputation of the dataset counts and demos 2 and 3, checked against the CLI.

Independent of the DB: it re-reads data/raw/*.json, applies the validity rule (PRD 4.3) itself, rebuilds
the vocab in Python (pass 1) and parses every line with normalize.parse_line(line, vocab) (pass 2: the same
comma split and safe suffix fallback that ingest applies in SQL). It shares only normalize.py and
ingest.steps() with the app, so it checks the DB build, the SQL and the answer plumbing, not the lexicon.
The CLI side is session.respond(), the exact function the CLI prints; both the structured values and the
formatted 'N of {valid} valid recipes (...)' lines in the reply text must match.

Run: python eval/oracle.py [--db data/recipes.db]   (about 2.5 minutes; exit 1 on any mismatch). The CLI side uses
the rule parser (no LLM quota or timeouts); the computed values are saved to eval/oracle_values.json for eval/run.py.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app import normalize as nz  # noqa: E402
from app.config import DB, VOCAB_MIN  # noqa: E402
from app.db import connect, load_dataset  # noqa: E402
from app.ingest import RAW, SOURCES, steps  # noqa: E402
from app.session import respond  # noqa: E402

VALUES = Path(__file__).with_name("oracle_values.json")

DEMO2 = "How many recipes contain both garlic and onion? What percentage of the dataset is that?"
DEMO3 = "Among recipes containing tomato, which five have the fewest instruction steps?"


def records(files: dict):
    """(recipe_id, record dict) for every raw record, one file in memory at a time."""
    for source, path in files.items():
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for key, rec in data.items():
            yield f"{source}:{key}", rec if isinstance(rec, dict) else {}
        del data


def real_lines(rec: dict) -> list[str]:
    """Ingredient lines that count (PRD 4.3): non-empty after removing ADVERTISEMENT, not a header, not equipment."""
    out = []
    for x in rec.get("ingredients") if isinstance(rec.get("ingredients"), list) else []:
        s = x.replace("ADVERTISEMENT", "").strip() if isinstance(x, str) else ""
        items = nz.parse_line(s) if s else None
        if s and not (items and (items[0].is_header or items[0].not_food)):
            out.append(s)
    return out


def invalid_reason(rec: dict, lines: list[str]) -> str | None:
    """The single validity rule, re-implemented here on purpose."""
    text = lambda k: rec.get(k) if isinstance(rec.get(k), str) else ""
    return ("empty_record" if not rec else "no_title" if not text("title").strip() else
            "no_ingredients" if not lines else "no_instructions" if not text("instructions").strip() else None)


def compute(files: dict, vocab_min: int = VOCAB_MIN) -> dict:
    """Expected numbers for the dataset line, demo 2 (garlic AND onion) and demo 3 (tomato, fewest steps)."""
    reasons, seen, valid = Counter(), Counter(), set()
    for rid, rec in records(files):  # pass 1: validity + canonical -> number of valid recipes (all options)
        lines = real_lines(rec)
        reasons[r := invalid_reason(rec, lines)] += 1
        if r is None:
            valid.add(rid)
            seen.update({o.canonical for s in lines for p in nz.parse_line(s) for o in p.options})
    vocab = {c for c, n in seen.items() if n >= vocab_min}
    fam = {w: nz.family_for(nz.normalize(w, vocab)[0]) for w in ("garlic", "onion", "tomato")}
    has = lambda f, cans, fams, broad: bool((fams | cans) & {f, *nz.BROAD.get(f, [])}) if broad else f in fams
    both, tomato, tomato_broad = Counter(), [], 0
    for rid, rec in records(files):  # pass 2: required items (primary options) with the vocab, like the DB
        if rid not in valid:
            continue
        lines = real_lines(rec)
        cans = {p.name.canonical for s in lines for p in nz.parse_line(s, vocab) if p.name}
        fams = {nz.family_for(c) for c in cans}
        for mode, broad in (("strict", False), ("broad", True)):
            both[mode] += has(fam["garlic"], cans, fams, broad) and has(fam["onion"], cans, fams, broad)
        if has(fam["tomato"], cans, fams, False):  # rank tie-break: n_steps, n_ingredients, id
            tomato.append((steps(rec["instructions"])[0], len(lines), rid))
        tomato_broad += has(fam["tomato"], cans, fams, True)
    tomato.sort()
    return {"total": sum(reasons.values()), "valid": reasons.pop(None, 0), "invalid": dict(reasons),
            "demo2": dict(both), "demo3_n": len(tomato), "demo3_ids": [rid for *_, rid in tomato[:5]],
            "demo3_broad": tomato_broad}


def check(files: dict, db: Path = DB, vocab_min: int = VOCAB_MIN) -> list[tuple]:
    """[(check, expected, got, ok)] comparing the oracle with what the CLI answers."""
    exp = compute(files, vocab_min)
    VALUES.write_text(json.dumps(exp, indent=1), encoding="utf-8")  # eval/run.py asserts stats against these
    con = connect(db)
    ds = load_dataset(con)
    text2, _, r2 = respond(con, ds, DEMO2, use_llm=False)  # rule parser: no quota, no timeouts, deterministic
    text3, _, r3 = respond(con, ds, DEMO3, use_llm=False)
    got2 = {r.mode: r.value for r in r2}
    rows = [("records", exp["total"], ds.total), ("valid", exp["valid"], ds.valid),
            ("invalid breakdown", exp["invalid"], dict(ds.invalid)),
            ("demo2 strict", exp["demo2"]["strict"], got2.get("strict")),
            ("demo2 broad", exp["demo2"]["broad"], got2.get("broad")),
            ("demo2 text", True, all(ds.header(exp["demo2"][m]) in text2 for m in ("strict", "broad"))),
            ("demo3 n analyzed", exp["demo3_n"], r3.n_analyzed), ("demo3 ids", exp["demo3_ids"], r3.value),
            ("demo3 text", True, ds.header(exp["demo3_n"]) in text3 and all(i in text3 for i in exp["demo3_ids"])
             and f"would match {exp['demo3_broad']:,} recipes" in text3)]
    con.close()
    return [(name, e, g, e == g) for name, e, g in rows]


def main() -> None:
    """Print each check and exit 1 on any mismatch."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DB)
    results = check({s: RAW / f for s, f in SOURCES.items()}, ap.parse_args().db)
    for name, e, g, ok in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: expected {e}" + ("" if ok else f", CLI said {g}"))
    sys.exit(0 if all(ok for *_, ok in results) else 1)


if __name__ == "__main__":
    main()
