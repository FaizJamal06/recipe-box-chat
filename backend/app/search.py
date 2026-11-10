"""T1 search: FTS5 BM25 candidates + SQL include/exclude filters, with per-restriction evidence (PRD 6.1).

Hard constraints are SQL filters on the complete set, never post-hoc checks on a top-k: included ingredients
use the strict definition (asked for penne -> penne), excluded ones the broad one (no garlic -> no garlic
powder either), excluded tags drop 'contains' (and 'may_contain' in strict mode).
"""
import re
import sqlite3
from dataclasses import dataclass, field

from .stats import Filters, Term, render


@dataclass
class Hit:
    """One displayed recipe and the lines proving each restriction holds."""
    id: str
    title: str
    source: str
    n_ingredients: int
    n_steps: int
    evidence: list = field(default_factory=list)


@dataclass
class SearchResult:
    hits: list
    total: int  # all eligible recipes, not just the ones shown
    filters: str
    sql: str


def _fts(text: str) -> str:
    """Plain words -> an FTS5 query that ANDs quoted tokens (no FTS syntax from user text)."""
    return " ".join(f'"{w}"' for w in re.findall(r"[a-z0-9]+", (text or "").lower()))


def mention_words(t: Term) -> list[str]:
    """Words whose mention in an ingredient line counts as containing an excluded ingredient."""
    return list(dict.fromkeys(x.replace('"', "") for x in (t.text.lower(), t.canonical, *t.broad_names)))


def hard_where(include: list[Term] = (), exclude: list[Term] = (), exclude_tags: list[str] = (),
               max_steps: int | None = None, strict_may_contain: bool = False) -> tuple[str, list, list[str]]:
    """Hard constraints as one SQL WHERE over `recipes r`, its params, and one label per constraint.
    Shared by search and match so both apply exactly the same rules."""
    w, params, _ = Filters(all_of=list(include), none_of=list(exclude)).where("strict", none_mode="broad")
    where = [w]
    for t in exclude:  # safety net: also any ingredient text naming it ('creamy roasted garlic ... sauce')
        where.append("r.id NOT IN (SELECT id FROM recipes_fts WHERE recipes_fts MATCH ?)")
        params.append("ingredients : (" + " OR ".join(f'"{x}"' for x in mention_words(t)) + ")")
    human = [f"contains {t.text}" for t in include] + [f"no {t.text}" for t in exclude]
    levels = ("contains", "may_contain") if strict_may_contain else ("contains",)
    for tag in exclude_tags:
        where.append(f"r.id NOT IN (SELECT recipe_id FROM recipe_tags WHERE tag = ? AND level IN "
                     f"({','.join('?' * len(levels))}))")
        params += [tag, *levels]
        human.append(f"no {tag} ({' or '.join(levels)})")
    if max_steps is not None:
        where.append("r.n_steps <= ?")
        params.append(max_steps)
        human.append(steps_label(max_steps))
    return " AND ".join(where), params, human


def steps_label(n: int) -> str:
    return f"at most {n} step{'' if n == 1 else 's'}"


def search(con: sqlite3.Connection, query_text: str = "", include: list[Term] = (),
           exclude: list[Term] = (), exclude_tags: list[str] = (), max_steps: int | None = None,
           strict_may_contain: bool = False, limit: int = 10) -> SearchResult:
    """Top `limit` valid recipes by BM25 (title weighted 3x) among those passing every hard filter."""
    w, params, human = hard_where(include, exclude, exclude_tags, max_steps, strict_may_contain)
    q = _fts(query_text)
    if q:
        frm, order = "recipes_fts JOIN recipes r ON r.id = recipes_fts.id", \
            "(r.title LIKE ?) DESC, bm25(recipes_fts, 3.0, 1.0), r.id"  # exact phrase in the title first
        params = [q] + params
        w = "recipes_fts MATCH ? AND " + w
        human.insert(0, f"matches '{query_text}'")
    else:
        frm, order = "recipes r", "r.id"
    sql = f"SELECT r.id, r.title, r.source, r.n_ingredients, r.n_steps FROM {frm} WHERE {w} ORDER BY {order}"
    tail = [f"%{' '.join(query_text.split())}%"] if q else []
    rows = con.execute(sql, params + tail).fetchall()  # every eligible row once: the total is len(rows)
    total = len(rows)  # ponytail: one pass instead of a 2nd COUNT query; LIMIT + COUNT if result sets get huge
    hits = [Hit(*r) for r in rows[:limit]]
    for h in hits:
        h.evidence = _evidence(con, h, include, exclude, exclude_tags, max_steps)
    return SearchResult(hits, total, "; ".join(human) or "all valid recipes", render(sql, params + tail) +
                        f" -- first {limit} shown")


def evidence(con: sqlite3.Connection, rid: str, include=(), exclude=(), exclude_tags=(), max_steps=None) -> list[str]:
    """Restriction evidence for one recipe by id (the recipe-detail view)."""
    h = Hit(*con.execute("SELECT id, title, source, n_ingredients, n_steps FROM recipes WHERE id = ?", (rid,)).fetchone())
    return _evidence(con, h, include, exclude, exclude_tags, max_steps)


def _evidence(con: sqlite3.Connection, h: Hit, include, exclude, exclude_tags, max_steps) -> list[str]:
    """Lines that prove each restriction for one recipe (or the count of lines checked); a recipe opened
    before a restriction was added can violate it, which is reported, never hidden."""
    one = lambda sql, *a: con.execute(sql, (h.id, *a)).fetchone()
    out = []
    for t in include:
        c, p = t.cond("strict")
        row = one(f"SELECT raw FROM ingredient_lines WHERE recipe_id = ? AND is_alt = 0 AND {c} LIMIT 1", *p)
        out.append(f"has {t.text}: {row[0]!r}" if row else f"VIOLATES has {t.text}: no matching line")
    lines = [r for r, in con.execute("SELECT DISTINCT raw FROM ingredient_lines WHERE recipe_id = ? AND is_header = 0 "
                                     "AND is_not_food = 0", (h.id,))]
    for t in exclude:
        c, p = t.cond("broad")
        row = one(f"SELECT raw FROM ingredient_lines WHERE recipe_id = ? AND is_alt = 0 AND {c} LIMIT 1", *p)
        rx = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in mention_words(t)) + r")", re.I)
        bad = row[0] if row else next((x for x in lines if rx.search(x)), None)
        out.append(f"VIOLATES no {t.text}: {bad!r}" if bad else
                   f"no {t.text}: 0 lines name or mention it; checked {h.n_ingredients} lines")
    for tag in exclude_tags:
        row = one("SELECT t.level, l.raw FROM recipe_tags t JOIN ingredient_lines l ON l.recipe_id = t.recipe_id "
                  "AND l.line_no = t.evidence_line_no WHERE t.recipe_id = ? AND t.tag = ? LIMIT 1", tag)
        if not row:
            out.append(f"no {tag}: 0 {tag}-tagged lines; checked {h.n_ingredients} lines")
        elif row[0] == "contains":
            out.append(f"VIOLATES no {tag}: {row[1]!r}")
        elif row[0] == "alt":
            out.append(f"no {tag}: only as an alternative, use the {tag}-free option in {row[1]!r}")
        else:
            out.append(f"no {tag}: {row[1]!r} may contain {tag} (check the label)")
    if max_steps is not None:
        out.append(f"{'VIOLATES ' if h.n_steps > max_steps else ''}{h.n_steps} steps (limit {max_steps})")
    return out
