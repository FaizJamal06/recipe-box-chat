"""Amounts for a substitution: the observed median of an ingredient across recipes (evidence, >= 3 examples) and a
labelled estimate scaled to the removed quantity ('1/4 cup per egg' x 3 eggs -> '3/4 cup')."""
import re
import sqlite3
import statistics

from . import normalize as nz
from .match import TO_BASE


def _fmt(x: float) -> str:
    whole, frac = int(x), x - int(x)
    near = min(((abs(frac - v), s) for v, s in ((0, ""), (.25, "1/4"), (1 / 3, "1/3"), (.5, "1/2"), (2 / 3, "2/3"),
                                               (.75, "3/4"), (1, "+1"))))[1]
    if near == "+1":
        return str(whole + 1)
    return f"{whole} {near}".strip() if whole and near else (near or str(whole))


def observed(con: sqlite3.Connection, ids, names: list[str], family: str | None = None) -> tuple | None:
    """('1/2 cup', n, 0.5, 'cup'): the median amount of an ingredient across recipes, only from >= 3 parseable examples in one
    unit family (volume / mass converted within the family; counts need the same unit). None otherwise."""
    ids, names = sorted(ids)[:300], list(names)  # ponytail: fixed 300-recipe sample; plenty for a median
    if not ids:
        return None
    per: dict = {}
    for i in range(0, len(ids), 900):
        part = ids[i:i + 900]
        for rid, qty, unit in con.execute(
                f"SELECT recipe_id, qty, unit FROM ingredient_lines WHERE is_alt = 0 AND qty IS NOT NULL AND "
                f"recipe_id IN ({','.join('?' * len(part))}) AND (+canonical IN ({','.join('?' * len(names))})"
                + (" OR +family = ?" if family else "") + ")", (*part, *names) + ((family,) if family else ())):
            fam = nz.UNIT_FAMILY.get(unit) if unit else "count"
            base = qty * TO_BASE[unit] if unit and TO_BASE.get(unit) else qty
            key = (fam, None if TO_BASE.get(unit) else unit)
            per.setdefault(key, {}).setdefault(rid, [0.0, unit])[0] += base
    best = max(per.items(), key=lambda kv: len(kv[1]), default=None)
    if not best or len(best[1]) < 3:
        return None
    (fam, unit), vals = best
    units = [u for _, u in vals.values()]
    shown = max(set(units), key=units.count) if unit is None and fam in ("volume", "mass") else unit
    med = statistics.median(v for v, _ in vals.values()) / (TO_BASE.get(shown) or 1)
    return (f"{_fmt(med)} {shown}" if shown else _fmt(med)), len(vals), med, shown


def scale(est: str, lines: list[str]) -> str:
    """The estimate for the removed lines: '1/4 cup per egg' + ['3 eggs'] -> '3/4 cup' (counts for 'per egg', a volume
    for 'per cup of ...'); 'the same volume' / '3/4 of the amount' -> that share of the removed amount. '' if unknown."""
    items = [i for r in lines for i in nz.parse_line(r)[:1]]
    if not items or any(i.qty is None for i in items):
        return ""
    amounts, per, unit = est.partition(" per ")
    share = 1.0 if est.startswith("the same") else nz._num(m[1]) if (m := re.match(rf"({nz.NUM}) of the amount", est)) \
        else None
    if share is not None and len(items) == 1:
        amounts, n = f"{items[0].qty} {items[0].unit or ''}".strip(), share
    elif not per:
        return ""
    elif unit.startswith("cup"):
        if any(nz.UNIT_FAMILY.get(i.unit) != "volume" or not TO_BASE.get(i.unit) for i in items):
            return ""
        n = sum(i.qty * TO_BASE[i.unit] for i in items) / TO_BASE["cup"]
    elif any(i.unit for i in items):
        return ""
    else:
        n = sum(i.qty for i in items)
    out = re.sub(nz.NUM, lambda m: _fmt(nz._num(m[0]) * n), amounts)
    return re.sub(rf"({nz.NUM}) (cup|tablespoon|teaspoon)s?\b",
                  lambda m: f"{m[1]} {m[2]}" + ("s" if nz._num(m[1]) > 1 else ""), out)
