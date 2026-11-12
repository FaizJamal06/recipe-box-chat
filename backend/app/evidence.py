"""Dataset evidence for a substitution (PRD 6.4 steps 4-7): three tiers of related recipes, contrast counts,
explicit-variant titles, quoted instruction snippets, observed quantities and a strength grade.

Tiers: L1 = titles with the dish words ("banana bread"); L2 = Jaccard >= 0.35 with the target's canonical set and
the same dish context; L3 = every recipe in the same dish context. Each tier splits into WITH the removed item and
WITHOUT it. For a candidate: support = WITHOUT recipes using it, lift = P(cand | WITHOUT) / P(cand | WITH) with
add-one smoothing (never divides by zero). Every cited recipe ID is re-checked against the DB before it is shown.
Strength: Strong = an explicit-variant L1 recipe ("eggless", "vegan") or support >= 3 in L1; Moderate = support >= 3
in L2; Weak = only L3 or support < 3; None = no support anywhere. Support-based grades also need lift > 1 in that
tier, and an explicit variant counts only if the candidate is rarer WITH the item (raw rates): baking soda is in an
eggless banana bread, but also in 137 of 178 banana breads with eggs, so it is a staple of the dish, not a replacement.
"""
import math
import re
import sqlite3
import statistics
from dataclasses import dataclass, field

import yaml

from . import normalize as nz
from .match import TO_BASE

STRENGTHS = ("Strong", "Moderate", "Weak", "None")
STAPLES = {"salt", "water", "sugar", "flour", "oil", "baking powder", "baking soda", "black pepper"}
_DECEPTIVE = set(yaml.safe_load((nz.LEX / "synonyms.yaml").read_text(encoding="utf-8"))["deceptive_heads"])
_DESCRIBE = set("""a an the my our your best easy quick simple homemade perfect ultimate delicious rich healthy basic super
amazing classic moist old fashioned grandma grandmas mom moms mommy aunt aunts favorite famous vegan eggless free low
fat skinny creamy yummy tasty awesome great special simply really very world ever recipe i ii iii iv and or style
gluten dairy egg sugar no""".split())
_CACHE: dict = {}


@dataclass
class Spec:
    """What is being removed: a tag ('eggs' -> every egg-tagged line) or a term (canonical / family)."""
    text: str
    tag: str | None = None
    canonical: str | None = None
    family: str | None = None
    words: list = field(default_factory=list)  # for title markers and the leftover-mention regex

    @property
    def key(self) -> str:
        return f"tag:{self.tag}" if self.tag else f"term:{self.canonical}|{self.family}"

    def line_hits(self, canonical: str | None, family: str | None, tags: dict) -> bool:
        if self.tag:
            return tags.get(self.tag) == "contains"
        return family == self.family if self.canonical == self.family else canonical == self.canonical


@dataclass
class Tier:
    n_with: int = 0
    n_without: int = 0
    support: int = 0  # WITHOUT-recipes that use the candidate
    in_with: int = 0  # WITH-recipes that use it too
    lift: float = 1.0
    ids: list = field(default_factory=list)  # supporting recipe ids (re-checked before display)


def _db(con) -> str:
    return con.execute("PRAGMA database_list").fetchone()[2]


def _cached(con, key, fn):
    k = (_db(con), key)
    if k not in _CACHE:
        if len(_CACHE) > 400:  # ponytail: FIFO bound for a 0.5 GB box; an LRU if hit rates ever matter
            for old in [x for x in _CACHE if x[1] not in ("contexts", "vocab")][:100]:
                del _CACHE[old]
        _CACHE[k] = fn()
    return _CACHE[k]


def contexts(con: sqlite3.Connection) -> dict[str, str]:
    """{recipe_id: dish context} for every valid recipe (SQL heuristics, computed once per DB and cached):
    pasta = a pasta/noodle line; baked = oven/bake words + a flour, sugar, baking powder/soda or cake-mix line; dessert_cold = sugar + chill/freeze
    words without baking; savory = everything else."""
    def build():
        ids = lambda sql: {r for r, in con.execute(sql)}
        sweet = ("SELECT recipe_id FROM ingredient_lines WHERE family IN ('sugar', 'flour') OR canonical LIKE '%sugar%' "
                 "OR canonical LIKE 'baking %' OR canonical LIKE '%cake mix%'")
        pasta = ids("SELECT recipe_id FROM ingredient_lines WHERE family = 'pasta' OR canonical LIKE '%noodle%' "
                    "OR canonical LIKE '%pasta%'")
        baked = ids(f"SELECT id FROM recipes WHERE valid = 1 AND (instructions_raw LIKE '%bake%' OR instructions_raw "
                    f"LIKE '%oven%') AND id IN ({sweet})")
        cold = ids(f"SELECT id FROM recipes WHERE valid = 1 AND (instructions_raw LIKE '%chill%' OR instructions_raw "
                   f"LIKE '%refrigerat%' OR instructions_raw LIKE '%freez%') AND id IN ({sweet})")
        return {r: "pasta" if r in pasta else "baked" if r in baked else "dessert_cold" if r in cold else "savory"
                for r, in con.execute("SELECT id FROM recipes WHERE valid = 1")}
    return _cached(con, "contexts", build)


def lift(n_with: int, in_with: int, n_without: int, support: int) -> float:
    """Add-one smoothed P(cand | WITHOUT) / P(cand | WITH); 1.0 (neutral) when nothing was observed: no WITHOUT
    recipes, or the candidate in none of them nor in any WITH recipe (smoothing alone would show a fake 13x)."""
    if not n_without or not (support or in_with):
        return 1.0
    return ((support + 1) / (n_without + 2)) / ((in_with + 1) / (n_with + 2))


def with_item(con: sqlite3.Connection, spec: Spec) -> set:
    """Valid recipes containing the removed item (required lines)."""
    def build():
        if spec.tag:
            return {r for r, in con.execute("SELECT recipe_id FROM recipe_tags WHERE tag = ? AND level = 'contains'",
                                            (spec.tag,))}
        col, val = ("family", spec.family) if spec.canonical == spec.family else ("canonical", spec.canonical)
        return {r for r, in con.execute(f"SELECT DISTINCT recipe_id FROM ingredient_lines WHERE is_alt = 0 AND "
                                        f"{col} = ?", (val,))}
    return _cached(con, ("with", spec.key), build)


def names_for(con: sqlite3.Connection, cand: str) -> list[str]:
    """Canonicals that count as the candidate: itself plus word-suffix variants ('raw cashew' for cashew), except
    for deceptive heads ('peanut butter' is not butter)."""
    allv = _cached(con, "vocab", lambda: [c for c, in con.execute("SELECT canonical FROM vocab")])
    return _cached(con, ("names", cand), lambda: [cand] + (
        [] if cand in _DECEPTIVE else [v for v in allv if v.endswith(" " + cand)]))


def with_cand(con: sqlite3.Connection, cand: str) -> set:
    """Recipes with a required line that is the candidate (canonical, its family, or a word-suffix variant)."""
    def build():
        names = names_for(con, cand)
        return {r for r, in con.execute(
            f"SELECT DISTINCT recipe_id FROM ingredient_lines WHERE is_alt = 0 AND (family = ? OR canonical IN "
            f"({','.join('?' * len(names))}))", (cand, *names))}
    return _cached(con, ("cand", cand), build)


def head(title: str) -> str:
    """The title before ' with / in / on ...' ('Pasta with Tomato Cream Sauce' -> 'pasta')."""
    return re.split(r"\s+(?:with|in|on|over|served|topped)\s+", title.lower().strip())[0]


def dish_words(title: str, removed: list[str], named: str | None = None) -> list[str]:
    """Head words of the dish: the named dish, else the title before ' with / in / on ', minus descriptors and the
    removed item's words, last two ('Classic Banana Bread with Flax' -> banana bread)."""
    t = (named or head(title)).lower()
    drop = _DESCRIBE | {w for r in removed for w in re.findall(r"[a-z]+", r.lower())}
    words = [w for w in re.findall(r"[a-z]+", t) if w not in drop and len(w) > 2]
    return words[-2:]


def tiers(con: sqlite3.Connection, rid: str, words: list[str]) -> tuple[dict, list[str]]:
    """({'L1': ids, 'L2': ids, 'L3': ids}, dish words actually used for L1). Cached per (recipe, words), so a
    re-grade ('I'm also allergic to tree nuts') doesn't redo the L2 search; L3 is one shared set per context."""
    return _cached(con, ("tiers", rid, tuple(words)), lambda: _tiers(con, rid, words))


def _tiers(con: sqlite3.Connection, rid: str, words: list[str]) -> tuple[dict, list[str]]:
    ctx = contexts(con)
    title_ids = lambda ws: {r for r, in con.execute(
        "SELECT r.id FROM recipes_fts f JOIN recipes r ON r.id = f.id WHERE recipes_fts MATCH ? AND r.valid = 1",
        ("title : (" + " AND ".join(f'"{w}"' for w in ws) + ")",))} if ws else set()
    l1, used = title_ids(words), words
    if len(l1) < 3 and len(words) == 2:  # 'meringue cookies' -> the single word with more recipes
        alt = max(([w] for w in (words[-1], words[0])), key=lambda ws: len(title_ids(ws)))
        l1, used = title_ids(alt), alt
    target = {c for c, in con.execute("SELECT DISTINCT canonical FROM ingredient_lines WHERE recipe_id = ? AND "
                                      "is_alt = 0 AND canonical IS NOT NULL", (rid,))}
    l2 = set()
    if target:
        ph = ",".join("?" * len(target))
        shared = dict(con.execute(f"SELECT recipe_id, COUNT(DISTINCT canonical) FROM ingredient_lines WHERE is_alt = 0 "
                                  f"AND canonical IN ({ph}) GROUP BY recipe_id HAVING COUNT(DISTINCT canonical) >= ?",
                                  (*target, max(2, math.ceil(0.35 * len(target))))))
        pool = [r for r in shared if r != rid and ctx.get(r) == ctx.get(rid)]
        for i in range(0, len(pool), 900):  # SQLite variable limit
            part = pool[i:i + 900]
            for r, n in con.execute(f"SELECT recipe_id, COUNT(DISTINCT canonical) FROM ingredient_lines WHERE is_alt = 0 "
                                    f"AND canonical IS NOT NULL AND recipe_id IN ({','.join('?' * len(part))}) "
                                    f"GROUP BY recipe_id", part):
                if shared[r] / (len(target) + n - shared[r]) >= 0.35:
                    l2.add(r)
    l3 = _cached(con, ("L3", ctx.get(rid)), lambda: {r for r, c in ctx.items() if c == ctx.get(rid)})
    return {"L1": l1, "L2": l2, "L3": l3}, used


def tier(family: set, withs: set, cand_ids: set) -> Tier:
    """Contrast counts for one candidate in one tier."""
    w, wo = family & withs, family - withs
    sup, inw = wo & cand_ids, w & cand_ids
    return Tier(len(w), len(wo), len(sup), len(inw), lift(len(w), len(inw), len(wo), len(sup)), sorted(sup))


def markers(spec: Spec) -> re.Pattern:
    """Explicit-variant title words for this removal ('eggless', 'egg-free', 'vegan', 'dairy-free', ...)."""
    ws = [re.escape(w) for w in spec.words]
    pats = [rf"{w}less" for w in ws] + [rf"{w}s?[- ]free" for w in ws] + [rf"no[- ]{w}s?" for w in ws] + \
           [rf"without {w}s?" for w in ws]
    dairy = spec.tag == "dairy" or any(t == "dairy" for w in spec.words for t, _ in nz.tags_for(w))
    pats += ["dairy[- ]free", "non[- ]?dairy", "lactose[- ]free"] if dairy else []
    if spec.tag in ("egg", "dairy", "meat", "honey", "gelatin") or dairy or "egg" in spec.words:
        pats += ["vegan", "plant[- ]based"]
    return re.compile(r"\b(?:" + "|".join(pats) + r")\b", re.I)


def titles(con: sqlite3.Connection, ids) -> dict[str, str]:
    ids = list(ids)
    return dict(con.execute(f"SELECT id, title FROM recipes WHERE id IN ({','.join('?' * len(ids))})", ids)) \
        if ids else {}


def cited(con: sqlite3.Connection, ids, spec: Spec, cand: str) -> list[str]:
    """Fresh DB re-check of cited recipes, batched: valid, lacks the removed item, contains the candidate. Anything
    that fails is dropped, never shown. (recipe_tags has no recipe_id index, so one query per id would scan.)"""
    ids = list(dict.fromkeys(ids))
    if not ids:
        return []
    q, names = ",".join("?" * len(ids)), names_for(con, cand)
    got = lambda sql, args: {r for r, in con.execute(sql, args)}
    valid = got(f"SELECT id FROM recipes WHERE valid = 1 AND id IN ({q})", ids)
    if spec.tag:
        has = got(f"SELECT recipe_id FROM recipe_tags WHERE tag = ? AND level = 'contains' AND recipe_id IN ({q})",
                  (spec.tag, *ids))
    else:
        col, val = ("family", spec.family) if spec.canonical == spec.family else ("canonical", spec.canonical)
        has = got(f"SELECT recipe_id FROM ingredient_lines WHERE is_alt = 0 AND +{col} = ? AND recipe_id IN ({q})",
                  (val, *ids))
    uses = got(f"SELECT recipe_id FROM ingredient_lines WHERE is_alt = 0 AND (+family = ? OR +canonical IN "
               f"({','.join('?' * len(names))})) AND recipe_id IN ({q})", (cand, *names, *ids))
    return [r for r in ids if r in valid and r not in has and r in uses]


def snippets(con: sqlite3.Connection, ids: list[str], cand: str, k: int = 2) -> list[tuple[str, str]]:
    """Up to k instruction sentences (from different recipes) that mention the candidate, with the recipe id."""
    head = re.compile(rf"\b{re.escape(cand.split()[-1])}(?:e?s)?\b", re.I)
    out = []
    for rid in ids[:40]:
        text = con.execute("SELECT instructions_raw FROM recipes WHERE id = ?", (rid,)).fetchone()[0] or ""
        hit = next((s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if head.search(s)), None)
        if hit:
            out.append((rid, hit[:200]))
        if len(out) == k:
            break
    return out


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


def strength(t: dict, explicit: list, increase: tuple | None = None) -> str:
    """The grade from tier counts (see module doc). `increase`: (L1 more?, L2 more?) for 'use more X' candidates,
    which are graded on whether WITHOUT recipes used more of it, not on presence."""
    if increase is not None:
        return "Strong" if increase[0] else "Moderate" if increase[1] else "Weak"
    a = t["L1"]
    staple = a.support / max(a.n_without, 1) <= a.in_with / max(a.n_with, 1)  # baking soda in eggless banana bread
    if (explicit and not staple) or (a.support >= 3 and a.lift > 1):
        return "Strong"
    if t["L2"].support >= 3 and t["L2"].lift > 1:
        return "Moderate"
    return "Weak" if any(x.support for x in t.values()) else "None"


def disagree(t: dict) -> bool:
    """Tiers point in opposite directions (lift > 1.5 in one, < 0.67 in another, each with >= 3 WITHOUT recipes)."""
    ls = [x.lift for x in t.values() if x.n_without >= 3 and (x.support or x.in_with)]
    return bool(ls) and max(ls) > 1.5 and min(ls) < 0.67
