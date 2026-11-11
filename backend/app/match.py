"""T2 matching (PRD 6.3): rank recipes for the ingredients a user has.

U = the user's have-set (canonical, via normalize); P = pantry staples assumed available (salt, black pepper,
water; can be switched off); R = a recipe's required canonical set - P (required = primary option, not an
'or' alternative). matched = U & R, unused = U - R, extra = R - U (an unparsed line counts as extra).
A have item matches like stats' strict presence: its family when it names one ('rice' -> white/brown rice...),
else the exact canonical.
Eligibility (hard, SQL, via search.hard_where like T1): no exclude / exclude_tags violation, n_steps <=
max_steps, |matched| >= 1 (candidate prefilter: recipes using any item of U).
score = w_m*|matched| - w_e*|extra| - w_s*n_steps - w_q*(#matched items with insufficient quantity);
tie-break |matched| desc, |extra| asc, n_steps asc, id asc. Counts come from one GROUP BY over the candidates.
Quantities are compared only within one unit family (volume / mass via units.yaml to_base, count only for
the same unit or none); never volume<->mass. Otherwise: name-level match, quantity not verified.
No eligible recipe -> MatchResult.rows is empty and .alternatives relaxes one named constraint at a time.
"""
import re
import sqlite3
from dataclasses import dataclass, field

import yaml

from . import normalize as nz
from . import safety
from .db import Dataset
from .search import hard_where, steps_label
from .stats import Term, render

STAPLES = ("salt", "black pepper", "water")
WEIGHTS = {"m": 2.0, "e": 1.0, "s": 0.1, "q": 0.5}
PREF_WEIGHTS = {"use_most": ("m", 3.0), "fewest_extra": ("e", 1.5), "fewest_steps": ("s", 0.5)}
TO_BASE = {u: d.get("to_base") for u, d in
           yaml.safe_load((nz.LEX / "units.yaml").read_text(encoding="utf-8")).items()}
LINES = "is_alt = 0 AND is_header = 0 AND is_not_food = 0"  # required, real ingredient rows


@dataclass
class Have:
    """One user item: what they typed, its Term, and the quantity if given."""
    text: str
    term: Term
    qty: float | None = None
    unit: str | None = None


@dataclass
class Row:
    """One ranked recipe with its score components and the sets behind them."""
    id: str
    title: str
    n_steps: int
    score: float
    parts: dict  # component -> signed points
    matched: list = field(default_factory=list)
    unused: list = field(default_factory=list)
    extra: list = field(default_factory=list)
    staples: list = field(default_factory=list)  # staples the recipe uses (assumed available)
    qty: list = field(default_factory=list)  # one note per matched item with a user quantity
    warnings: list = field(default_factory=list)  # may_contain / unverified lines for excluded tags


@dataclass
class MatchResult:
    rows: list
    total: int  # all eligible recipes
    constraints: list  # hard constraints, one label each
    have: list
    unknown: list  # items normalize() could not place in the dataset vocab
    dropped: list  # have items removed because a restriction excludes them
    weights: dict
    staples: tuple
    sql: str = ""
    alternatives: list = field(default_factory=list)  # (violated constraint, [Row]) when nothing is eligible
    more: list = field(default_factory=list)  # lenient mode: top eligible rows with an unverified ingredient
    n_unverified: int = 0  # eligible recipes with an unverified ingredient for an excluded tag (ranked last)


def _hits(t: Term, canonical: str | None, family: str | None) -> bool:
    """Python mirror of Term.cond('strict')."""
    return family == t.family if t.canonical == t.family else canonical == t.canonical


def _segment(s: str, vocab) -> list[str] | None:
    """'eggs spinach' (no comma) -> ['eggs', 'spinach'] when the words split, longest first, into known
    canonicals that keep all their words ('goat cheese' is one canonical, so it is never split)."""
    words, out, i = s.split(), [], 0
    while i < len(words):
        for j in range(len(words), i, -1):
            c = nz.normalize(" ".join(words[i:j]), vocab)
            if c and c[0] in vocab and len(c[0].split()) >= j - i:
                out.append(" ".join(words[i:j]))
                i = j
                break
        else:
            return None
    return out if len(out) > 1 else None


def parse_have(items: list[str], ds: Dataset) -> tuple[list[Have], list[str]]:
    """'2 eggs' -> Have(egg, qty 2); names the dataset doesn't know go to `unknown`."""
    have, unknown, seen = [], [], set()
    for s in [x for item in items for x in (_segment(item, ds.vocab) if not re.search(r"\d", item) else None) or [item]]:
        p = nz.parse_line(s, ds.vocab)
        p = p[0] if p and p[0].name else None
        if not p or p.name.canonical not in ds.vocab:
            unknown.append(s)
        elif p.name.canonical not in seen:
            seen.add(c := p.name.canonical)
            have.append(Have(s, Term(c, c, nz.family_for(c)), p.qty, p.unit))
    return have, unknown


def _conflicts(have: list[Have], exclude: list[Term], exclude_tags: list[str]) -> list[tuple[Have, str]]:
    """Have items a restriction forbids ('eggs' + 'exclude eggs'): they can't count as matched."""
    out = []
    for h in have:
        tags = {t for t, lv in nz.tags_for(h.term.canonical) if lv == "contains"} & set(exclude_tags)
        ex = [t.text for t in exclude if h.term.family in t.broad_names or h.term.canonical in t.broad_names]
        if tags or ex:
            out.append((h, f"no {(sorted(tags) or ex)[0]}"))
    return out


def _in_unit(qty: float | None, unit: str | None, ref: str | None) -> float | None:
    """qty expressed in the user's unit `ref`, or None when not comparable (never volume <-> mass)."""
    if qty is None or unit == ref:
        return qty
    a, b = TO_BASE.get(unit), TO_BASE.get(ref)
    return qty * a / b if a and b and nz.UNIT_FAMILY[unit] == nz.UNIT_FAMILY[ref] else None


def _quantities(con: sqlite3.Connection, h: Have) -> dict[str, tuple[bool, str]]:
    """{recipe_id: (short?, note)} for one have item with a quantity, over every recipe that uses it."""
    c, p = h.term.cond("strict")
    need: dict[str, list] = {}
    for rid, qty, unit in con.execute(f"SELECT recipe_id, qty, unit FROM ingredient_lines WHERE is_alt = 0 AND {c}", p):
        need.setdefault(rid, []).append(_in_unit(qty, unit, h.unit))
    u = f" {h.unit}" if h.unit else ""
    out = {}
    for rid, vals in need.items():
        if any(v is None for v in vals):
            out[rid] = (False, f"{h.term.text}: name-level match; quantity not verified (different or missing unit)")
        elif (n := sum(vals)) <= h.qty:
            out[rid] = (False, f"{h.term.text}: sufficient (recipe needs {n:g}{u}, you have {h.qty:g}{u})")
        else:
            out[rid] = (True, f"{h.term.text}: short by {n - h.qty:g}{u} (recipe needs {n:g}{u}, you have {h.qty:g}{u})")
    return out


def _ranked(con, have, where, params, staples, w, flag=("0", [])) -> tuple[list[tuple], str, dict, set]:
    """Every eligible recipe as (score, -matched, extra, n_steps, id, title, parts), best first, fully verified
    recipes before those with an unverified ingredient (`flag`, see safety.flag_sql); plus the unverified ids."""
    conds = [h.term.cond("strict") for h in have]
    anyc, anyp = " OR ".join(f"({c})" for c, _ in conds), [x for _, p in conds for x in p]
    cols = ", ".join(f"MAX(CASE WHEN {c} THEN 1 ELSE 0 END)" for c, _ in conds)
    st = f"canonical IN ({','.join('?' * len(staples))})" if staples else "0"
    # candidates first (eligible + uses any item of U), then only their lines via ix_lines_recipe (~3x faster)
    sql = (f"WITH cand AS (SELECT r.id, r.title, r.n_steps FROM recipes r WHERE {where} AND r.id IN (SELECT recipe_id "
           f"FROM ingredient_lines WHERE is_alt = 0 AND ({anyc}))) SELECT c.id, c.title, c.n_steps, COUNT(DISTINCT "
           f"CASE WHEN NOT COALESCE(({anyc}), 0) AND NOT COALESCE({st}, 0) THEN COALESCE(l.canonical, l.raw) END), "
           f"{cols}, {flag[0]} FROM cand c JOIN ingredient_lines l ON l.recipe_id = c.id "
           f"WHERE l.{LINES.replace(' AND ', ' AND l.')} GROUP BY c.id")
    p = params + anyp + anyp + list(staples) + anyp + list(flag[1])
    qty = {i: _quantities(con, h) for i, h in enumerate(have) if h.qty is not None}
    out, unverified = [], set()
    for rid, title, n_steps, extra, *m, unv in con.execute(sql, p):
        if unv:
            unverified.add(rid)
        short = sum(qty[i].get(rid, (False,))[0] for i in qty if m[i])
        parts = {"matched": w["m"] * sum(m), "extra": -w["e"] * extra, "steps": -w["s"] * n_steps,
                 "short": -w["q"] * short}
        out.append((-round(sum(parts.values()), 6), -sum(m), extra, n_steps, rid, title, parts))
    out.sort(key=lambda x: (x[4] in unverified, x[:5]))
    return out, render(sql, p), qty, unverified


def _row(con, r: tuple, have: list[Have], staples, qty: dict) -> Row:
    """Matched / unused / extra names and quantity notes for one displayed recipe."""
    score, _, _, n_steps, rid, title, parts = r
    lines = con.execute(f"SELECT canonical, family, raw FROM ingredient_lines WHERE recipe_id = ? AND {LINES} "
                        "ORDER BY line_no, alt_group", (rid,)).fetchall()
    hit = [any(_hits(h.term, c, f) for c, f, _ in lines) for h in have]
    extra, used = [], []
    for c, f, raw in lines:
        name = c or f"(unparsed) {raw[:40]}"
        if c in staples:
            used.append(c)
        elif not any(_hits(h.term, c, f) for h in have) and name not in extra:
            extra.append(name)
    return Row(rid, title, n_steps, -score, parts, [h.term.text for h, k in zip(have, hit) if k],
               [h.term.text for h, k in zip(have, hit) if not k], extra, sorted(set(used)),
               [qty[i][rid][1] for i in qty if hit[i] and rid in qty[i]])


def match(con: sqlite3.Connection, ds: Dataset, items: list[str], exclude: list[Term] = (),
          exclude_tags: list[str] = (), max_steps: int | None = None, strict_may_contain: bool = False,
          prefs: list[str] = (), limit: int = 5, staples: tuple = STAPLES, relax: bool = True) -> MatchResult:
    """Top `limit` eligible recipes for the have-list, plus one-constraint relaxations when none qualify."""
    have, unknown = parse_have(items, ds)
    dropped = _conflicts(have, list(exclude), list(exclude_tags))
    have = [h for h in have if h not in [d for d, _ in dropped]]
    w = dict(WEIGHTS)
    w.update(PREF_WEIGHTS[p] for p in prefs if p in PREF_WEIGHTS)
    where, params, constraints = hard_where((), exclude, exclude_tags, max_steps, strict_may_contain)
    constraints = constraints + ["uses at least 1 of your ingredients"]
    res = MatchResult([], 0, constraints, have, unknown, dropped, w, tuple(staples))
    if not have:
        return res
    ranked, res.sql, qty, unv = _ranked(con, have, where, params, staples, w,
                                        safety.flag_sql(exclude_tags, strict_may_contain, "c.id"))
    res.total, res.n_unverified = len(ranked), len(unv)
    res.rows = [_row(con, r, have, staples, qty) for r in [r for r in ranked if r[4] not in unv][:limit]]
    res.more = [_row(con, r, have, staples, qty) for r in [r for r in ranked if r[4] in unv][:limit]]
    for r in res.rows + res.more:  # may_contain / unverified lines are shown on the card, never hidden
        r.warnings = safety.warnings(con, r.id, exclude_tags)
    if not ranked and relax:
        kw = dict(items=items, exclude=list(exclude), exclude_tags=list(exclude_tags), max_steps=max_steps,
                  strict_may_contain=strict_may_contain, prefs=prefs, limit=3, staples=staples, relax=False)
        options = [(f"no {t.text}", {"exclude": [x for x in exclude if x != t]}) for t in exclude] + \
                  [(c, {"exclude_tags": [x for x in exclude_tags if x != tag]}) for tag, c in
                   zip(exclude_tags, constraints[len(exclude):])] + \
                  ([(steps_label(max_steps), {"max_steps": None})] if max_steps is not None else [])
        res.alternatives = [(label, match(con, ds, **{**kw, **change}).rows) for label, change in options]
    return res
