"""Templated replies from executor output (no LLM, so no hallucinated facts); post-checks recipe IDs. M2-M4.

Every number in a reply comes from a stats/search Result, and every answer states the dataset line
'N of {valid} valid recipes ({total} records; invalid: ...)' from the startup Dataset.
"""
import json
import sqlite3

from . import safety
from .db import Dataset
from .match import MatchResult, Row
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
    for i, (rid, title, v, nl, ns, para, other) in enumerate(r.rows, 1):
        extra = (f" (newline steps {nl}, sentences {ns}{', paragraph-format' if para else ''}; {other} ingredients)"
                 if fld == "n_steps" else f" ({other} steps)")
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
    n = res.n_unverified
    out = [f"{res.total - n:,} recipes match ({res.filters}){' and are fully verified' if n else ''}; showing "
           f"{len(res.hits)}.", f"Eligible: {ds.header(res.total)}"]
    for i, h in enumerate(res.hits + res.more, 1):  # fully verified first; the rest folded behind one line
        if i == len(res.hits) + 1:
            out.append(f"  ⚠ {safety.summary(n)}. Ranked last:")
        out.append(f"  {i}. {h.id}  {h.title} — {h.n_ingredients} ingredients, {h.n_steps} steps")
        out += [f"       · {e}" for e in h.evidence]
    if n and not res.more:
        out.append(f"  ⚠ {safety.summary(n)}.")
    if not res.total:
        out.append("  No recipe satisfies every restriction; none were relaxed.")
    return "\n".join(out + [f"SQL: {res.sql}"])


def _match_line(i: int, r: Row) -> str:
    return (f"    {i}. {r.id}  {r.title} — matched: {', '.join(r.matched)} · extra ({len(r.extra)}): "
            f"{', '.join(r.extra[:8])}{' ...' if len(r.extra) > 8 else ''} · {r.n_steps} steps")


def match_reply(res: MatchResult, ds: Dataset) -> str:
    """Ranked matches with score breakdown and a 'why' sentence; or the exact no-match text plus a separately
    flagged list of one-constraint relaxations (never mixed with real matches)."""
    w = res.weights
    qty = lambda h: f" ({h.qty:g} {h.unit or ''})".replace(" )", ")") if h.qty is not None else ""
    out = [f"Your ingredients (U): {', '.join(h.term.text + qty(h) for h in res.have) or 'none'}"]
    if res.staples:
        out.append(f"Pantry staples assumed available (P): {', '.join(res.staples)} — say 'no staples' to turn off.")
    if res.unknown:
        out.append(f"Not found in the dataset vocabulary (ignored): {', '.join(res.unknown)}")
    out += [f"Removed from your ingredients because '{why}' excludes it: {h.term.text}" for h, why in res.dropped]
    out.append(f"Hard constraints: {'; '.join(res.constraints)}")
    if not res.total:
        out.append("No recipe satisfies all hard constraints")
        if res.alternatives:
            out.append("!! CLOSEST ALTERNATIVES — these are NOT matches; each one violates the named constraint:")
            for label, rows in res.alternatives:
                out.append(f"  Violates '{label}':")
                out += [_match_line(i, r) for i, r in enumerate(rows, 1)] or ["    (none even with this relaxed)"]
        return "\n".join(out)
    out.append(f"Eligible: {ds.header(res.total)}; showing the top {len(res.rows)} fully verified.")
    out.append(f"Score = {w['m']:g}·matched − {w['e']:g}·extra − {w['s']:g}·steps − {w['q']:g}·short-quantity items; "
               "ties: more matched, fewer extra, fewer steps, then id. matched = U∩R, unused = U−R, extra = R−U "
               "(R = recipe's required ingredients minus P).")
    prev = None
    for i, r in enumerate(res.rows + res.more, 1):  # fully verified first; the rest folded behind one line
        if i == len(res.rows) + 1:
            out.append(f"  ⚠ {safety.summary(res.n_unverified)}. Ranked last:")
        bar = " | ".join(f"{k} {v:+.1f}" for k, v in r.parts.items())
        out.append(f"  {i}. {r.id}  {r.title} — score {r.score:.2f} [{bar}]")
        out.append(f"       matched ({len(r.matched)}): {', '.join(r.matched)} · unused: {', '.join(r.unused) or '-'}"
                   f" · extra ({len(r.extra)}): {', '.join(r.extra) or '-'}"
                   + (f" · staples used: {', '.join(r.staples)}" if r.staples else ""))
        why = (f"uses {len(r.matched)} of your {len(res.have)} ingredients, needs {len(r.extra)} more, "
               f"{r.n_steps} step{'s' if r.n_steps != 1 else ''}")
        if prev is not None and abs(prev - r.score) < 1e-9:
            why += f"; same score as #{i - 1}, ordered by the tie-break"
        out.append(f"       why here: {why}.")
        out += [f"       qty: {q}" for q in r.qty]
        out += [f"       ⚠ {w}" for w in r.warnings]
        prev = r.score
    if res.n_unverified and not res.more:
        out.append(f"  ⚠ {safety.summary(res.n_unverified)}.")
    unq = [h.term.text for h in res.have if h.qty is None]
    if any(h.qty is not None for h in res.have) and unq:
        out.append(f"Quantities not given for {', '.join(unq)}: name-level match only.")
    return "\n".join(out + [f"SQL: {res.sql}"])


def detail_reply(con: sqlite3.Connection, rid: str, evidence: list[str]) -> str:
    """One recipe: original ingredient lines and instructions, plus a check of the active restrictions."""
    title, ing, instr, n_ing, n_steps, para = con.execute(
        "SELECT title, ingredients_raw, instructions_raw, n_ingredients, n_steps, is_paragraph_format FROM recipes "
        "WHERE id = ?", (rid,)).fetchone()
    lines = [s for x in json.loads(ing) if isinstance(x, str) and (s := x.replace("ADVERTISEMENT", "").strip())]
    out = [f"{rid}  {title} — {n_ing} ingredients, {n_steps} steps", "Ingredients (original lines):"]
    out += [f"  - {x}" for x in lines] + ["Steps:"]
    if para:
        out += [f"  (one paragraph; counted as {n_steps} sentences)", f"  {instr.strip()}"]
    else:
        out += [f"  {i}. {s.strip()}" for i, s in enumerate((s for s in instr.split("\n") if s.strip()), 1)]
    if evidence:
        out += ["Restrictions check:"] + [f"  · {e}" for e in evidence]
    return "\n".join(out)
