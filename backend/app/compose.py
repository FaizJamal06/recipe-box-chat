"""Templated replies from executor output (no LLM, so no hallucinated facts); post-checks recipe IDs. M2-M4.

Every number in a reply comes from a stats/search Result, and every answer states the dataset line
'N of {valid} valid recipes ({total} records; invalid: ...)' from the startup Dataset.
"""
from .db import Dataset
from .search import SearchResult
from .stats import Result

FIELD_NAME = {"n_steps": "steps", "n_ingredients": "ingredients"}


def _tail(r: Result) -> list[str]:
    """Normalization, notes, method; shared by all stats replies."""
    out = [f"Normalization: {r.normalization_note}"] if r.normalization_note else []
    return out + [f"Note: {n}" for n in r.notes] + [f"Method: {r.method}"]


def count_reply(results: list[Result], ds: Dataset) -> str:
    """Count/percentage: one line per normalization mode, then definitions, method and SQL."""
    r0 = results[0]
    out = [f"Recipes where: {r0.filters}"]
    for r in results:
        out.append(f"  {r.mode:<6} {ds.header(r.value)} = {100 * r.value / r.denominator:.2f}% of valid recipes")
    out.append(f"Denominator: all {r0.denominator:,} valid recipes.")
    out += _tail(r0)
    return "\n".join(out + [f"SQL ({r.mode}): {r.sql}" for r in results])


def rank_reply(r: Result, fld: str, order: str) -> list[str]:
    word = {("n_steps", "asc"): "fewest steps", ("n_steps", "desc"): "most steps",
            ("n_ingredients", "asc"): "fewest ingredients", ("n_ingredients", "desc"): "most ingredients"}[fld, order]
    out = [f"{len(r.rows)} recipes with the {word} ({r.filters}):"]
    for i, (rid, title, v, nl, ns, para) in enumerate(r.rows, 1):
        extra = f" (newline steps {nl}, sentences {ns}{', paragraph-format' if para else ''})" if fld == "n_steps" else ""
        out.append(f"  {i}. {rid}  {title} — {v} {FIELD_NAME[fld][:-1] if v == 1 else FIELD_NAME[fld]}{extra}")
    return out


def stats_reply(res, ds: Dataset, plan: dict) -> str:
    """Any stats op -> text. `res` is a list for count/percentage, else one Result."""
    if isinstance(res, list):
        return count_reply(res, ds)
    s = plan["stats"]
    if res.op == "rank":
        out = rank_reply(res, s["field"], s["order"])
    elif res.op == "top_ingredients":
        out = [f"Top {len(res.rows)} ingredients by recipe count ({res.filters}):"] + \
              [f"  {i}. {c} — {n:,} recipes" for i, (c, n) in enumerate(res.rows, 1)]
    else:
        out = [f"{res.op.capitalize()} number of {FIELD_NAME[s['field']]} ({res.filters}): {res.value}"]
    out.append(f"Analyzed: {ds.header(res.n_analyzed)}")
    return "\n".join(out + _tail(res) + [f"SQL: {res.sql}"])


def search_reply(res: SearchResult, ds: Dataset) -> str:
    """Search hits with evidence lines and the full eligible count."""
    out = [f"{res.total:,} recipes match ({res.filters}); showing {len(res.hits)}.",
           f"Eligible: {ds.header(res.total)}"]
    for i, h in enumerate(res.hits, 1):
        out.append(f"  {i}. {h.id}  {h.title} — {h.n_ingredients} ingredients, {h.n_steps} steps")
        out += [f"       · {e}" for e in h.evidence]
    if not res.hits:
        out.append("  No recipe satisfies every restriction; none were relaxed.")
    return "\n".join(out + [f"SQL: {res.sql}"])
