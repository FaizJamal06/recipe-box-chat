"""Dataset evidence for a substitution (PRD 6.4 steps 4-7): three tiers of related recipes, contrast counts,
explicit-variant titles, quoted instruction snippets, observed quantities and a strength grade.

Tiers: L1 = titles with the most specific dish phrase that has >= 10 recipes, >= 3 of them without the item
("tomato cream sauce" -> "cream sauce" -> "pasta": 14 tomato cream sauces all have cream, so nothing to learn); L2 = Jaccard >= 0.35 with the target's canonical set and the same dish context; L3 = every recipe in the
same dish context. Each tier splits into WITH the removed item and WITHOUT it. For a candidate: support = WITHOUT
recipes using it, in_with = WITH recipes using it, lift = (support / n_without) / (in_with / n_with) from raw rates,
only when support >= 3 and n_with >= 20 (else "too few to compute": the grade then uses the counts). Every cited
recipe ID is re-checked against the DB before it is shown.
Strength: "favours" = the raw rate WITHOUT the item beats the rate WITH it (lift > 1 whenever lift is computable).
Strong = favours in L1 and either >= 3 L1 supporting recipes, or an explicit-variant title ("eggless") plus >= 2 L1
supporting recipes or >= 3 favouring in L2; never for a staple (baking soda is in an eggless banana bread, but also in
137 of 178 banana breads with eggs). Moderate = >= 3 favouring in L2; Weak = any support; None = no support anywhere.
"""
import math
import re
import sqlite3
from dataclasses import dataclass, field

import yaml

from . import normalize as nz

STRENGTHS = ("Strong", "Moderate", "Weak", "None")
STAPLES = {"salt", "water", "sugar", "flour", "oil", "baking powder", "baking soda", "black pepper"}
MIN_L1, MIN_WITHOUT = 10, 3  # an L1 phrase needs 10 recipes, 3 of them without the item, else a less specific one
_DECEPTIVE = set(yaml.safe_load((nz.LEX / "synonyms.yaml").read_text(encoding="utf-8"))["deceptive_heads"])
_DESCRIBE = set("""a an the my our your best easy quick simple homemade perfect ultimate delicious rich healthy basic super
amazing classic moist old fashioned grandma grandmas mom moms mommy aunt aunts favorite famous vegan eggless free low
fat skinny creamy yummy tasty awesome great special simply really very world ever recipe i ii iii iv and or style
gluten dairy egg sugar no""".split())
_DISH_WORDS = {"sugar", "egg"}  # descriptors that also start dish names: sugar cookies, egg salad
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
    lift: float | None = None  # None = too few to compute
    ids: list = field(default_factory=list)  # supporting recipe ids (re-checked before display)


def _db(con) -> str:
    return con.execute("PRAGMA database_list").fetchone()[2]


def _cached(con, key, fn):
    k = (_db(con), key)
    if k not in _CACHE:
        if len(_CACHE) > 400:  # ponytail: FIFO bound for a 0.5 GB box; an LRU if hit rates ever matter
            for old in [x for x in list(_CACHE) if x[1] not in ("contexts", "sizes", "vocab")][:100]:
                _CACHE.pop(old, None)  # list(): the startup warm-up thread may insert at the same time
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


def sizes(con: sqlite3.Connection) -> dict[str, int]:
    """{recipe_id: distinct required canonicals} (L2's exact Jaccard set sizes, from ingest), loaded at startup."""
    return _cached(con, "sizes", lambda: dict(con.execute("SELECT recipe_id, n FROM recipe_size")))


def lift(n_with: int, in_with: int, n_without: int, support: int) -> float | None:
    """Raw P(cand | WITHOUT) / P(cand | WITH); None when support < 3 or n_with < 20 (too few to compute), inf when
    no WITH recipe uses it. No smoothing: add-one turned 3/1411 vs 0/181 into 'lift 0.5'."""
    if support < 3 or n_with < 20:
        return None
    return math.inf if not in_with else (support / n_without) / (in_with / n_with)


def fmt_lift(x: float | None) -> str:
    return "too few to compute" if x is None else "∞" if math.isinf(x) else f"{x:.1f}"


def favours(t: "Tier") -> bool:
    """The candidate's raw rate WITHOUT the item beats its rate WITH it."""
    return t.support / max(t.n_without, 1) > t.in_with / max(t.n_with, 1)


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


def phrases(title: str) -> list[list[str]]:
    """L1 phrases, most specific first: word-suffixes of each ' with / in / on ' segment that start on a content
    word (dish heads come last), longest first, head segment first. 'Pasta with Tomato Cream Sauce' -> tomato cream
    sauce, cream sauce, pasta, sauce. A ' with A and B' list is accompaniments, not the dish ('Paella with ... and
    Green Peas' is a paella), so only a single-item tail counts."""
    out = []
    for s, seg in enumerate(re.split(r"\s+(?:with|in|on|over|served|topped)\s+", title.lower().strip())):
        if s and re.search(r",|\band\b|&", seg):
            continue
        w = re.findall(r"[a-z]+", seg)
        while w and (w[-1] in _DESCRIBE or len(w[-1]) < 3):
            w.pop()  # 'Banana Bread II'
        starts = lambda i: len(w[i]) > 2 and (w[i] not in _DESCRIBE or (  # 'sugar cookies', not 'sugar free ...'
            w[i] in _DISH_WORDS and i + 1 < len(w) and w[i + 1] not in ("free", "less")))
        out += [(i - len(w), s, w[i:]) for i in range(len(w)) if starts(i)]
    return [p for *_, p in sorted(out)]


def l1_levels(con: sqlite3.Connection, title: str, spec: Spec | None) -> list[tuple[list[str], set]]:
    """[(phrase, ids)] for every title phrase with >= MIN_L1 recipes, >= MIN_WITHOUT of them without the item, most
    specific first (substitute.run widens through them); if none qualifies, just the largest phrase."""
    def build():
        withs, out, best = with_item(con, spec) if spec else set(), [], ((False, 0), [], set())
        for p in phrases(title):
            ids = {r for r, in con.execute("SELECT r.id FROM recipes_fts f JOIN recipes r ON r.id = f.id WHERE "
                                           "recipes_fts MATCH ? AND r.valid = 1", (f'title : "{" ".join(p)}"',))}
            key = (len(ids - withs) >= MIN_WITHOUT, len(ids))
            if key[0] and key[1] >= MIN_L1:
                out.append((p, ids))
            best = max(best, (key, p, ids), key=lambda b: b[0])
        return out or [best[1:]]
    return _cached(con, ("l1", title, spec and spec.key, MIN_L1), build)


def tiers(con: sqlite3.Connection, rid: str) -> dict:
    """{'L2': ids, 'L3': ids}. Cached per recipe, so a re-grade ('I'm also allergic to tree nuts') doesn't redo the
    L2 search; L3 is one shared set per context."""
    return _cached(con, ("tiers", rid), lambda: _tiers(con, rid))


def _tiers(con: sqlite3.Connection, rid: str) -> dict:
    ctx = contexts(con)
    target = {c for c, in con.execute("SELECT DISTINCT canonical FROM ingredient_lines WHERE recipe_id = ? AND "
                                      "is_alt = 0 AND canonical IS NOT NULL", (rid,))}
    l2 = set()
    if target:
        ph = ",".join("?" * len(target))
        rows = con.execute(f"SELECT recipe_id, COUNT(*) FROM recipe_canon WHERE canonical IN ({ph}) GROUP BY "
                           f"recipe_id HAVING COUNT(*) >= ?", (*target, max(2, math.ceil(0.35 * len(target)))))
        size = sizes(con)
        l2 = {r for r, a in rows if r != rid and ctx.get(r) == ctx.get(rid)
              and a / (len(target) + max(size.get(r, 0), a) - a) >= 0.35}
    l3 = _cached(con, ("L3", ctx.get(rid)), lambda: {r for r, c in ctx.items() if c == ctx.get(rid)})
    return {"L2": l2, "L3": l3}


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
    that fails is dropped, never shown. (recipe_tags has no recipe_id index: a tag check reuses with_item's set.)"""
    ids = list(dict.fromkeys(ids))
    if not ids:
        return []
    q, names = ",".join("?" * len(ids)), names_for(con, cand)
    got = lambda sql, args: {r for r, in con.execute(sql, args)}
    valid = got(f"SELECT id FROM recipes WHERE valid = 1 AND id IN ({q})", ids)
    if spec.tag:
        has = with_item(con, spec)
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


def strength(t: dict, explicit: list, increase: tuple | None = None, staple: bool = False) -> str:
    """The grade from tier counts (see module doc). `increase`: (L1 more?, L2 more?) for 'use more X' candidates,
    which are graded on whether WITHOUT recipes used more of it, not on presence."""
    if increase is not None:
        return "Strong" if increase[0] else "Moderate" if increase[1] else "Weak"
    a, b = t["L1"], t["L2"]
    l2 = b.support >= 3 and favours(b)
    if not staple and favours(a) and (a.support >= 3 or (explicit and (a.support >= 2 or l2))):
        return "Strong"
    if l2:
        return "Moderate"
    return "Weak" if any(x.support for x in t.values()) else "None"


def disagree(t: dict) -> bool:
    """Tiers point in opposite directions (computable lift > 1.5 in one tier, < 0.67 in another)."""
    ls = [x.lift for x in t.values() if x.lift is not None]
    return bool(ls) and max(ls) > 1.5 and min(ls) < 0.67
