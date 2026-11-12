"""T3 substitution (PRD 6.4): remove an ingredient from one recipe and propose replacements graded by dataset evidence.

Pipeline per removed item: affected lines (canonical, family or tag match) -> role from lexicon/roles.yaml for the
dish context -> candidates: curated (lexicon/candidates.yaml), "use more" of something already in the recipe, the
user's own pick, and data-discovered co-occurrences (lift >= 2, support >= 3 in L1/L2) -> safety: every candidate
must be verified (safety.verify_canonical) against all active restrictions and the removed item, otherwise it is
rejected with the reason -> evidence and strength (evidence.py) -> ranking: user pick, curated, then discovered
(labelled "co-occurs; role not established"). Choice (rank): the user's pick, then never a conflicting candidate
before a non-conflicting one, then strength, support and lift. An adaptation is built (adapt.py) only when the chosen
candidate has any support; a Weak one is labelled "Weak evidence: based on n recipes". L1 widens to less
specific title phrases ("cream sauce" -> "pasta") until every removed item has a Strong or Moderate candidate. A
defining ingredient (chicken in "Chicken Curry", egg whites in a meringue) makes the bot warn and ask first.
"""
import re
import sqlite3
from dataclasses import dataclass, field

import yaml

from . import adapt, amounts, evidence, safety, stats
from . import normalize as nz
from .db import Dataset
from .evidence import STAPLES, STRENGTHS, Spec
from .rules import TAG_WORDS

_ROLES = yaml.safe_load((nz.LEX / "roles.yaml").read_text(encoding="utf-8"))
CANDS = yaml.safe_load((nz.LEX / "candidates.yaml").read_text(encoding="utf-8"))
ESTIMATE, PREP, DECLARED = CANDS.pop("estimate"), CANDS.pop("prep"), CANDS.pop("declared")
ADAPT_MS = 12_000  # the step rewrite is a deliberate action: a longer cap than the 6 s planner, then a deterministic swap


@dataclass
class Cand:
    name: str
    kind: str  # user | curated | increase | discovered | staple
    roles: list = field(default_factory=list)
    tiers: dict = field(default_factory=dict)
    strength: str = "None"
    explicit: list = field(default_factory=list)  # explicit-variant L1 recipes using it ('eggless banana bread')
    ids: list = field(default_factory=list)  # supporting recipe ids that passed the re-check
    snippets: list = field(default_factory=list)  # [(recipe id, instruction sentence)]
    observed: tuple | None = None  # (amount text, n, value, unit) from evidence.observed; None -> yaml estimate
    conflicting: bool = False

    @property
    def quantity(self) -> str:
        return f"median {self.observed[0]} (n={self.observed[1]})" if self.observed else ""

    @property
    def label(self) -> str:
        return {"user": "your pick", "increase": f"use more {self.name} (already in the recipe)",
                "discovered": "co-occurs; role not established", "staple": "co-occurs; role not established (staple)",
                }.get(self.kind, f"curated: {', '.join(self.roles)}")


@dataclass
class Part:
    item: str
    spec: Spec
    affected: list  # [(line_no, raw)]
    roles: list = field(default_factory=list)
    candidates: list = field(default_factory=list)  # allowed, ranked
    rejected: list = field(default_factory=list)  # [(name, reason)]
    chosen: Cand | None = None
    conflicting: bool = False
    target_qty: str = ""  # median amount of the removed item in the WITH recipes

    @property
    def strength(self) -> str:
        return self.chosen.strength if self.chosen else "None"


@dataclass
class Result:
    rid: str
    title: str
    context: str = ""
    dish: list = field(default_factory=list)
    tiers: dict = field(default_factory=dict)  # tier -> size
    l1_without: int = 0  # L1 recipes without the (first) removed item
    parts: list = field(default_factory=list)
    restrictions: list = field(default_factory=list)
    question: str = ""
    adaptation: object = None
    notes: list = field(default_factory=list)
    picked: str = ""  # how the session chose the recipe ('I picked ...'), shown first
    widened: str = ""  # why L1 isn't the most specific phrase, or that wider phrases didn't help


def spec_for(item: str, ds: Dataset) -> Spec:
    """'eggs' -> the egg tag (every egg line); 'egg whites' / 'cream' -> a term (canonical or family)."""
    w = " ".join(item.lower().split())
    tags = TAG_WORDS.get(w) or TAG_WORDS.get(nz.singular(w))
    if tags and len(tags) == 1 and tags[0] in ("egg", "honey", "gelatin"):
        return Spec(item, tag=tags[0], words=[tags[0]])
    t = stats.term(w, ds)
    words = [t.canonical] + ([t.family] if t.family != t.canonical and t.family in TAG_WORDS else [])
    return Spec(item, canonical=t.canonical, family=t.family, words=words)


def affected(con: sqlite3.Connection, rid: str, spec: Spec) -> list[tuple[int, str]]:
    """[(line_no, raw)] of the recipe's ingredient lines that contain the removed item."""
    out: dict[int, str] = {}
    for n, raw, can, fam in con.execute("SELECT line_no, raw, canonical, family FROM ingredient_lines WHERE "
                                        "recipe_id = ? AND is_header = 0 AND is_not_food = 0 ORDER BY line_no", (rid,)):
        tags = dict(nz.tags_for(can)) if can else {}
        if spec.line_hits(can, fam, tags) or (spec.tag and dict(nz.line_tags(raw)).get(spec.tag) == "contains"):
            out[n] = raw
    return sorted(out.items())


def _key(spec: Spec, table: dict) -> str | None:
    return next((k for k in (spec.canonical, spec.family, *spec.words) if k and k in table), None)


def roles_for(spec: Spec, ctx: str) -> list[str]:
    r = _ROLES["roles"].get(_key(spec, _ROLES["roles"]) or "", {})
    return r.get(ctx) or r.get("*") or []


def defining(title: str, spec: Spec) -> str | None:
    """The dish word that makes this item defining ('meringue' for egg whites), or the item itself if the title names
    it in the dish head ('chicken' in 'Chicken Curry', not 'cream' in 'Pasta with Tomato Cream Sauce')."""
    t = title.lower()
    for dish, items in _ROLES["defining"].items():
        if dish in t and ({spec.canonical, spec.family, *spec.words} & set(items)):
            return dish
    return next((w for w in spec.words if re.search(rf"\b{re.escape(w)}(?:e?s)?\b", evidence.head(t))), None)


def _discovered(con, fam: dict, withs: set, skip) -> list[str]:
    """Canonicals over-represented in WITHOUT recipes of L1/L2 (lift >= 2, support >= 3), most supported first."""
    out: dict[str, int] = {}
    for tier in ("L1", "L2"):
        ids, w = list(fam[tier]), fam[tier] & withs
        wo = fam[tier] - w
        canon: dict[str, set] = {}
        for i in range(0, len(ids), 900):
            part = ids[i:i + 900]
            for rid, c in con.execute(f"SELECT DISTINCT recipe_id, canonical FROM ingredient_lines WHERE is_alt = 0 AND "
                                      f"canonical IS NOT NULL AND recipe_id IN ({','.join('?' * len(part))})", part):
                canon.setdefault(c, set()).add(rid)
        for c, rs in canon.items():
            sup = len(rs & wo)
            if (lf := evidence.lift(len(w), len(rs & w), len(wo), sup)) is not None and lf >= 2 and not skip(c):
                out[c] = max(out.get(c, 0), sup)
    return sorted(out, key=lambda c: (-out[c], c))[:6]


def _evaluate(con, c: Cand, fam: dict, withs: set, spec: Spec, marker) -> Cand:
    """Tier counts, explicit variants, re-checked ids, snippets, observed quantity and strength for one candidate."""
    ids = evidence.with_cand(con, c.name)
    c.tiers = {t: evidence.tier(fam[t], withs, ids) for t in fam}
    names = evidence.names_for(con, c.name)
    l1_titles = evidence.titles(con, c.tiers["L1"].ids)
    c.explicit = evidence.cited(con, [r for r, ti in l1_titles.items() if marker.search(ti)], spec, c.name)
    support = c.tiers["L1"].ids + [r for r in c.tiers["L2"].ids if r not in c.tiers["L1"].ids]
    c.ids = evidence.cited(con, list(dict.fromkeys(c.explicit + support))[:12], spec, c.name)
    c.snippets = evidence.snippets(con, c.ids, c.name)
    c.observed = amounts.observed(con, support, names, c.name)
    increase = None
    if c.kind == "increase":  # graded on whether recipes without the item used more of it
        def more(t):
            fam_t, w = fam[t], fam[t] & withs
            a, b = amounts.observed(con, fam_t - w, names, c.name), amounts.observed(con, w, names, c.name)
            return bool(a and b and a[3] == b[3] and a[2] > 1.2 * b[2])  # same unit, >= 20% more
        increase = (more("L1"), more("L2"))
    staple = c.name in STAPLES or nz.family_for(c.name) in STAPLES
    c.strength = evidence.strength(c.tiers, c.explicit, increase, staple)
    if c.kind in ("discovered", "staple") and c.strength in ("Strong", "Moderate"):
        c.strength = "Weak"  # co-occurrence without an established role is not evidence of a replacement
    # an explicit variant uses it, yet overall it isn't more common without the item: say so
    c.conflicting = evidence.disagree(c.tiers) or bool(c.explicit and not evidence.favours(c.tiers["L1"]))
    return c


def rank(c: Cand) -> tuple:
    """Sort key: your pick; non-conflicting before conflicting; strength; role coverage (roles all come from the
    same part, so more roles = a larger share of them); an established role before a bare co-occurrence (garlic is no
    egg substitute); L1 evidence for it before against; support (L1, L2, L3); lift."""
    t = c.tiers
    return (c.kind != "user", c.conflicting, STRENGTHS.index(c.strength), -len(c.roles),
            c.kind in ("discovered", "staple"),
            not evidence.favours(t["L1"]),
            -t["L1"].support, -t["L2"].support, -t["L3"].support, -(t["L1"].lift or 0), c.name)


def run(con: sqlite3.Connection, ds: Dataset, rid: str, removes: list[str], restrictions=(), exclude=(),
        replace_with: str | None = None, option: int = 1, dataset_only: bool = True, force: bool = False,
        use_llm: bool = True, remove_tags=()) -> Result:
    """Grade replacements for each removed item in recipe `rid` and, when supportable, adapt the recipe."""
    title = con.execute("SELECT title FROM recipes WHERE id = ?", (rid,)).fetchone()[0].strip()
    res = Result(rid, title, restrictions=list(dict.fromkeys(restrictions)))
    res.context = evidence.contexts(con).get(rid, "savory")
    specs = []
    for item in removes:
        try:
            specs.append(spec_for(item, ds))
        except stats.UnknownIngredient:
            res.notes.append(f"I don't recognise '{item}' as an ingredient.")
    for tag in remove_tags:  # 'make it vegan': every line with the tag, one part per ingredient family
        fams = dict.fromkeys(f for _, can, f in con.execute(
            "SELECT line_no, canonical, family FROM ingredient_lines WHERE recipe_id = ? AND is_alt = 0 AND "
            "canonical IS NOT NULL", (rid,)) if dict(nz.tags_for(can)).get(tag) == "contains")
        specs += [Spec(f, canonical=f, family=f, words=[f]) for f in fams if f not in {s.family for s in specs}]
    target_names = {c for c, in con.execute("SELECT DISTINCT canonical FROM ingredient_lines WHERE recipe_id = ? AND "
                                            "canonical IS NOT NULL", (rid,))}
    target_fams = {nz.family_for(c) for c in target_names}
    excl = [stats.term(w, ds) for w in exclude]

    def grade(fam: dict, dish: list[str]) -> tuple[list, list]:
        """(parts, notes) with this L1."""
        notes = []
        return [p for s in specs if (p := _part(s, fam, dish, notes))], notes

    def _part(spec, fam, dish, notes):
        lines = affected(con, rid, spec)
        if not lines:
            notes.append(f"'{spec.text}' isn't in this recipe (checked every ingredient line of `{rid}`).")
            return None
        part = Part(spec.text, spec, lines, roles_for(spec, res.context))
        withs, marker = evidence.with_item(con, spec), evidence.markers(spec)
        tags = list(dict.fromkeys([*res.restrictions, *([spec.tag] if spec.tag else [])]))
        removed = lambda c: spec.line_hits(c, nz.family_for(c), dict(nz.tags_for(c)))
        pool: dict[str, Cand] = {}
        if replace_with:
            pool[replace_with.lower()] = Cand(replace_with.lower(), "user")
        cur = CANDS.get(_key(spec, CANDS) or "", {})
        for role in part.roles:
            for n in cur.get(role, []):
                kind = "increase" if n in target_names or n in target_fams else "curated"
                pool.setdefault(n, Cand(n, kind)).roles.append(role)
        known_names = set(pool)
        skip = lambda c: (c in target_names or removed(c) or nz.family_for(c) == spec.family  # 'egg' for egg whites
                          or bool(set(c.split()) & set(dish))  # 'meringue cookie' in a meringue: the dish itself
                          or any(re.search(rf"\b{re.escape(w)}\b", c) for w in spec.words)  # 'saffron thread'
                          or any(c == k or c.endswith(" " + k) for k in known_names))
        for c in _discovered(con, fam, withs, skip):
            pool[c] = Cand(c, "staple" if nz.family_for(c) in STAPLES or c in STAPLES else "discovered")
        allowed = []  # declared tags (candidates.yaml) verify a curated item too rare for the vocab, if a recipe uses it
        declared = {n: DECLARED[n] for n in pool if n in DECLARED and evidence.with_cand(con, n)}
        for c in pool.values():
            ok, why = safety.verify_canonical(c.name, tags, ds.vocab, declared)
            if ok and removed((nz.normalize(c.name, ds.vocab) or [c.name])[0]):
                ok, why = False, f"is the ingredient being removed ({spec.text})"
            if ok and any(c.name in t.broad_names or c.name == t.canonical for t in excl):
                ok, why = False, "excluded by your restrictions"
            if ok and dataset_only and c.name not in ds.vocab and c.name not in declared and c.kind != "user":
                ok, why = False, "not a dataset ingredient (dataset only)"
            _evaluate(con, c, fam, withs, spec, marker)
            (allowed.append(c) if ok else part.rejected.append((c.name, why)))
        part.candidates = sorted(allowed, key=rank)
        if part.candidates:
            part.chosen = part.candidates[min(max(option, 1), len(part.candidates)) - 1]
            if option > len(part.candidates):
                notes.append(f"There are only {len(part.candidates)} usable options for {spec.text}.")
        best = min(list(pool.values()), key=lambda c: (STRENGTHS.index(c.strength), -c.tiers["L1"].support), default=None)
        part.conflicting = bool(part.chosen and (part.chosen.conflicting or (best and best not in allowed and
                                STRENGTHS.index(best.strength) < STRENGTHS.index(part.chosen.strength))))
        q = amounts.observed(con, fam["L1"] & withs or fam["L2"] & withs, [spec.canonical or spec.tag], spec.family)
        part.target_qty = f"median {q[0]} (n={q[1]})" if q else ""
        return part

    good = lambda ps: sum(bool(p.chosen and p.chosen.strength in ("Strong", "Moderate")) for p in ps)
    levels, l23, best = evidence.l1_levels(con, title, specs[0] if specs else None), evidence.tiers(con, rid), None
    for i, (phrase, l1) in enumerate(levels):  # widen until every part has a Strong or Moderate candidate
        fam = {"L1": l1, **l23}
        parts, notes = grade(fam, phrase)
        if best is None or good(parts) > good(best[1]):
            best = (i, parts, notes, fam, phrase)
        if good(parts) == len(parts):
            break
    i, res.parts, notes, fam, res.dish = best
    res.notes += notes
    tried = [" ".join(p) for p, _ in levels[:i]]
    if tried:
        res.widened = f"widened from '{tried[-1]}': no Strong or Moderate candidate there"
    elif len(levels) > 1 and not good(res.parts):
        res.widened = f"wider phrases ({', '.join(chr(39) + ' '.join(p) + chr(39) for p, _ in levels[1:])}) had none either"
    res.tiers = {t: len(v) for t, v in fam.items()}
    res.l1_without = len(fam["L1"] - evidence.with_item(con, specs[0])) if specs else 0
    dw = next((d for p in res.parts if (d := defining(title, p.spec))), None)
    if dw and not force and res.parts:
        be, it = ("are", "them") if res.parts[0].item.endswith("s") else ("is", "it")
        what = f"{be} what makes this a {dw}" if dw not in res.parts[0].spec.words else f"{be} in the dish name ('{title}')"
        res.question = (f"{res.parts[0].item.capitalize()} {what}: without {it}, it becomes a different dish. I've shown "
                        "the evidence below; say 'adapt it anyway' if you still want an adaptation.")
        return res
    supported = lambda p: p.chosen and p.chosen.strength != "None"
    if res.parts and all(supported(p) for p in res.parts):
        res.adaptation = adapt.build(con, ds, res, use_llm, caveat=adapt.weak_label(res), timeout_ms=ADAPT_MS)
    elif res.parts:
        res.notes.append("No adaptation: no recipe in the data supports a replacement for " + ", ".join(
            p.item for p in res.parts if not supported(p)) + ".")
    return res
