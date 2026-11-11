"""T1 stats: typed ops over the full filtered set in SQL; never LLM-computed (PRD 6.2).

Every op returns a Result carrying the value plus everything an answer must state: filters, N analyzed,
denominator (valid recipes), a one-sentence method, the exact SQL that ran, and a normalization note.
Ingredient words are canonicalized by normalize() (the same path ingest used), never by the LLM.
"""
import sqlite3
import statistics
from dataclasses import dataclass, field

from . import normalize as nz
from .db import Dataset

STEP_RULE = ("Steps = effective n_steps: non-empty newline-separated steps, except when the instructions are "
             "one paragraph of 2+ sentences, where sentences are counted instead (PRD 4.4).")
PRESENCE_RULE = ("A recipe contains X when one of its required ingredient items is X (an 'or' alternative "
                 "alone does not count).")
FIELDS = {"n_steps", "n_ingredients"}


class UnknownIngredient(ValueError):
    """The text names no ingredient normalize() can recognise."""


@dataclass(frozen=True)
class Term:
    """One ingredient as the user said it, plus how strict/broad presence is decided for it.
    strict: the family when the word names one (garlic -> garlic, minced garlic, garlic clove...), else the
    exact canonical (penne). broad: the family plus its `broad` list in lexicon/families.yaml."""
    text: str
    canonical: str
    family: str

    @property
    def broad_names(self) -> list[str]:
        return [self.family, *nz.BROAD.get(self.family, [])]

    def cond(self, mode: str) -> tuple[str, list]:
        """SQL condition on ingredient_lines columns for 'strict' or 'broad'."""
        if mode == "strict":
            return ("family = ?", [self.family]) if self.canonical == self.family else ("canonical = ?", [self.canonical])
        names = self.broad_names
        ph = ",".join("?" * len(names))
        return f"(family IN ({ph}) OR canonical IN ({ph}))", names + names

    def definition(self, con: sqlite3.Connection) -> str:
        """Human-readable strict/broad definition, with the most common strict members from the DB."""
        members = [c for c, in con.execute("SELECT canonical FROM vocab WHERE family = ? ORDER BY recipe_count "
                                           "DESC, canonical LIMIT 6", (self.family,))]
        if self.canonical == self.family:
            strict = f"strict {self.text} = the '{self.family}' family ({', '.join(members) or self.family}, ...)"
        else:
            strict = f"strict {self.text} = exactly '{self.canonical}'; broad starts from its '{self.family}' family"
        extra = nz.BROAD.get(self.family, [])
        return f"{strict}; broad adds {', '.join(extra)}" if extra else f"{strict}; broad = strict (no broad list)"


def term(text: str, ds: Dataset) -> Term:
    """Plain words -> Term via normalize() (same canonicalization as ingest)."""
    cans = nz.normalize(text, ds.vocab)
    if not cans:
        raise UnknownIngredient(text)
    return Term(text.strip(), cans[0], nz.family_for(cans[0]))


@dataclass
class Filters:
    """Recipe filters; ingredient filters are Terms, title_contains are plain substrings."""
    all_of: list = field(default_factory=list)
    any_of: list = field(default_factory=list)
    none_of: list = field(default_factory=list)
    title_contains: list = field(default_factory=list)
    title_any: list = field(default_factory=list)  # whole-word title keywords, any of (category proxy, PRD 5.3)

    def where(self, mode: str, none_mode: str | None = None) -> tuple[str, list, str]:
        """(SQL where clause over recipes r, params, human-readable filters). none_mode: definition used for
        exclusions (search excludes broadly: 'no garlic' also drops garlic powder)."""
        sql, params, human = ["r.valid = 1"], [], []
        sub = "r.id {}IN (SELECT recipe_id FROM ingredient_lines WHERE is_alt = 0 AND {})"
        for neg, terms in (("", self.all_of), ("NOT ", self.none_of)):
            for t in terms:
                c, p = t.cond(none_mode or mode if neg else mode)
                sql.append(sub.format(neg, c))
                params += p
                human.append(f"{'no ' if neg else 'contains '}{t.text}")
        if self.any_of:
            parts = [(sub.format("", c), p) for c, p in (t.cond(mode) for t in self.any_of)]
            sql.append("(" + " OR ".join(c for c, _ in parts) + ")")
            params += [x for _, p in parts for x in p]
            human.append("contains any of " + ", ".join(t.text for t in self.any_of))
        for w in self.title_contains:
            sql.append("r.title LIKE ?")
            params.append(f"%{w}%")
            human.append(f"title contains '{w}'")
        if self.title_any:  # FTS5 title column, porter-stemmed whole words: 'cookie' also matches 'cookies'
            sql.append("r.id IN (SELECT id FROM recipes_fts WHERE recipes_fts MATCH ?)")
            params.append("title : (" + " OR ".join(f'"{w}"' for w in self.title_any) + ")")
            human.append("title has any of: " + ", ".join(self.title_any))
        return " AND ".join(sql), params, " AND ".join(human) or "all valid recipes"

    @property
    def terms(self) -> list:
        return [*self.all_of, *self.any_of, *self.none_of]


@dataclass
class Result:
    """What every stats answer reports (PRD 6.2)."""
    op: str
    value: object
    filters: str
    n_analyzed: int
    denominator: int
    method: str
    sql: str
    mode: str = "strict"
    normalization_note: str = ""
    rows: list = field(default_factory=list)  # rank/top: (id or canonical, title, value, ...)
    notes: list = field(default_factory=list)  # caveats, ties, alternative rankings


def render(sql: str, params: list) -> str:
    """The exact query with parameters inlined as SQL literals, so it can be pasted into sqlite3."""
    for p in params:
        lit = str(p) if isinstance(p, (int, float)) else "'" + str(p).replace("'", "''") + "'"
        sql = sql.replace("?", lit, 1)
    return sql


def _note(con: sqlite3.Connection, f: Filters) -> str:
    return " | ".join(t.definition(con) for t in f.terms)


def _broad_note(con: sqlite3.Connection, f: Filters) -> list[str]:
    """Ops that filter on the strict definition also report the broad count (PRD 6.2: presence = both)."""
    if not f.terms:
        return []
    w, p, _ = f.where("broad")
    n = con.execute(f"SELECT COUNT(*) FROM recipes r WHERE {w}", p).fetchone()[0]
    return [f"Ingredient filters use the strict definition; the broad definition would match {n:,} recipes."]


def count(con: sqlite3.Connection, ds: Dataset, f: Filters, op: str = "count") -> list[Result]:
    """Recipes matching the filters, once strict and once broad (identical when there is no ingredient)."""
    out = []
    for mode in ("strict", "broad") if f.terms else ("strict",):
        w, p, human = f.where(mode)
        sql = f"SELECT COUNT(*) FROM recipes r WHERE {w}"
        n = con.execute(sql, p).fetchone()[0]
        out.append(Result(op, n, human, n, ds.valid, f"Counted valid recipes matching all filters ({mode}); "
                          f"percentage = count / valid recipes. {PRESENCE_RULE}", render(sql, p), mode, _note(con, f)))
    return out


def rank(con: sqlite3.Connection, ds: Dataset, f: Filters, fld: str = "n_steps", order: str = "asc",
         limit: int = 5) -> Result:
    """Top `limit` valid recipes by a field. Tie-break: the other field ascending (n_steps -> n_ingredients,
    n_ingredients -> n_steps), then recipe id ascending. Ingredient filters are strict."""
    assert fld in FIELDS and order in ("asc", "desc")
    other = "n_ingredients" if fld == "n_steps" else "n_steps"
    w, p, human = f.where("strict")
    sql = (f"SELECT r.id, r.title, r.{fld}, r.n_steps_newline, r.n_sentences, r.is_paragraph_format, r.{other} "
           f"FROM recipes r WHERE {w} ORDER BY r.{fld} {order.upper()}, r.{other} ASC, r.id ASC LIMIT ?")
    rows = con.execute(sql, p + [limit]).fetchall()
    n = con.execute(f"SELECT COUNT(*) FROM recipes r WHERE {w}", p).fetchone()[0]
    res = Result("rank", [r[0] for r in rows], human, n, ds.valid,
                 f"Sorted all {n:,} matching valid recipes by {fld} {order}, ties broken by {other} ascending, "
                 f"then recipe id ascending." + (f" {STEP_RULE}" if fld == "n_steps" else ""),
                 render(sql, p + [limit]), normalization_note=_note(con, f), rows=rows, notes=_broad_note(con, f))
    if rows:
        edge = rows[-1][2]
        ties = con.execute(f"SELECT COUNT(*) FROM recipes r WHERE {w} AND r.{fld} = ?", p + [edge]).fetchone()[0]
        if ties > 1:
            res.notes.append(f"{ties:,} recipes have {fld} = {edge}; the ones shown are the first by {other}, "
                             "then recipe id.")
    if fld == "n_steps" and rows:
        para = sum(r[5] for r in rows)
        if para * 2 >= len(rows):
            res.notes.append(f"Caveat: {para} of {len(rows)} are paragraph-format (one block of text), so their "
                             "step count is a sentence count.")
        nl = con.execute(f"SELECT r.id, r.title, r.n_steps_newline, r.is_paragraph_format FROM recipes r WHERE {w} "
                         f"ORDER BY r.n_steps_newline {order.upper()}, r.n_ingredients ASC, r.id ASC LIMIT ?",
                         p + [limit]).fetchall()
        np_ = sum(r[3] for r in nl)
        res.notes.append("Newline-only rule for comparison: " + ", ".join(f"{r[0]} ({r[2]})" for r in nl)
                         + (f" — {np_} of {len(nl)} paragraph-format" if np_ else ""))
    return res


def summary(con: sqlite3.Connection, ds: Dataset, f: Filters, op: str, fld: str) -> Result:
    """mean or median of a field over the filtered set (values fetched by SQL, statistic in Python)."""
    assert op in ("mean", "median") and fld in FIELDS
    w, p, human = f.where("strict")
    sql = f"SELECT r.{fld} FROM recipes r WHERE {w}"
    vals = [v for v, in con.execute(sql, p)]
    value = round(getattr(statistics, op)(vals), 2) if vals else None
    return Result(op, value, human, len(vals), ds.valid, f"{op} of {fld} over {len(vals):,} matching valid recipes."
                  + (f" {STEP_RULE}" if fld == "n_steps" else ""), render(sql, p), normalization_note=_note(con, f),
                  notes=_broad_note(con, f))


def top_ingredients(con: sqlite3.Connection, ds: Dataset, f: Filters, k: int = 10) -> Result:
    """Most common canonicals by recipe frequency (not line count) over the filtered set."""
    w, p, human = f.where("strict")
    sql = (f"SELECT l.canonical, COUNT(DISTINCT l.recipe_id) AS n FROM ingredient_lines l JOIN recipes r ON "
           f"r.id = l.recipe_id WHERE {w} AND l.is_alt = 0 AND l.canonical IS NOT NULL "
           f"GROUP BY l.canonical ORDER BY n DESC, l.canonical LIMIT ?")
    rows = con.execute(sql, p + [k]).fetchall()
    n = con.execute(f"SELECT COUNT(*) FROM recipes r WHERE {w}", p).fetchone()[0]
    return Result("top_ingredients", rows, human, n, ds.valid, "Canonical ingredients ranked by the number of "
                  "matching valid recipes that use them (required items only).", render(sql, p + [k]),
                  normalization_note=_note(con, f), rows=rows, notes=_broad_note(con, f))


TAG_LEVELS = ("Tag levels (recipe_tags): contains = a required item has it; may_contain = label-dependent "
              "(e.g. margarine, chocolate chips); alt = only in an 'or' option that has a tag-free alternative, so "
              "the recipe can be made without it (counted as free); unverified = an ingredient no tag could be "
              "verified for (unknown is not safe: strict counts it as not free).")


def tag_count(con: sqlite3.Connection, ds: Dataset, tags: list[str], want: str = "free",
              op: str = "count") -> list[Result]:
    """'How many recipes are dairy-free / contain dairy' over recipe_tags, reported at two strictness levels:
    lenient reads only 'contains'; strict also treats 'may_contain' and unverified recipes as not free."""
    assert want in ("free", "contains")
    out, tph = [], ",".join("?" * len(tags))
    for mode, levels in (("lenient", ("contains",)), ("strict", ("contains", "may_contain"))):
        sub = (f"r.id IN (SELECT recipe_id FROM recipe_tags WHERE tag IN ({tph}) AND level IN "
               f"({','.join('?' * len(levels))}))")
        if mode == "strict":
            sub = f"({sub} OR r.id IN (SELECT recipe_id FROM unverified WHERE tag IN ({tph})))"
        sql = f"SELECT COUNT(*) FROM recipes r WHERE r.valid = 1 AND {'NOT ' if want == 'free' else ''}{sub}"
        p = [*tags, *levels] + (list(tags) if mode == "strict" else [])
        n = con.execute(sql, p).fetchone()[0]
        name = "/".join(tags)
        method = (f"lenient = valid recipes with no {name} line at level 'contains' (may_contain and alt count as "
                  f"free); strict = no {name} line at 'contains' or 'may_contain' and every line verified" if want == "free" else
                  f"lenient = valid recipes with a {name} line at level 'contains'; strict = at 'contains' or "
                  "'may_contain', or with a line that couldn't be verified")
        out.append(Result(op, n, f"{name}-{want} recipes", n, ds.valid,
                          method + "; percentage = count / valid recipes.", render(sql, p), mode, TAG_LEVELS))
    return out


def execute(con: sqlite3.Connection, ds: Dataset, plan: dict):
    """Run a stats plan; returns Result(s). Raises UnknownIngredient."""
    s = plan["stats"]
    if s.get("tags"):
        return tag_count(con, ds, s["tags"], s["tag_mode"], "percentage" if s["op"] == "percentage" else "count")
    terms = lambda k: [term(w, ds) for w in s.get(k) or []]
    f = Filters(terms("all_of"), terms("any_of"), terms("none_of"), list(s.get("title_contains") or []))
    if s["op"] in ("count", "percentage"):
        return count(con, ds, f, s["op"])
    if s["op"] == "rank":
        return rank(con, ds, f, s["field"], s["order"], s["limit"])
    if s["op"] in ("mean", "median"):
        return summary(con, ds, f, s["op"], s["field"])
    return top_ingredients(con, ds, f, s["limit"])
