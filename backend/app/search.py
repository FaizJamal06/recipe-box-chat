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


def search(con: sqlite3.Connection, query_text: str = "", include: list[Term] = (),
           exclude: list[Term] = (), exclude_tags: list[str] = (), max_steps: int | None = None,
           strict_may_contain: bool = False, limit: int = 10) -> SearchResult:
    """Top `limit` valid recipes by BM25 (title weighted 3x) among those passing every hard filter."""
    w, params, h = Filters(all_of=list(include), none_of=list(exclude)).where("strict", none_mode="broad")
    where, human = [w], ([] if h == "all valid recipes" else [h])
    levels = ("contains", "may_contain") if strict_may_contain else ("contains",)
    for tag in exclude_tags:
        where.append(f"r.id NOT IN (SELECT recipe_id FROM recipe_tags WHERE tag = ? AND level IN "
                     f"({','.join('?' * len(levels))}))")
        params += [tag, *levels]
        human.append(f"no {tag} ({' or '.join(levels)})")
    if max_steps is not None:
        where.append("r.n_steps <= ?")
        params.append(max_steps)
        human.append(f"at most {max_steps} steps")
    q, w = _fts(query_text), " AND ".join(where)
    if q:
        frm, order, params = "recipes_fts JOIN recipes r ON r.id = recipes_fts.id", \
            "bm25(recipes_fts, 3.0, 1.0), r.id", [q] + params
        w = "recipes_fts MATCH ? AND " + w
        human.insert(0, f"matches '{query_text}'")
    else:
        frm, order = "recipes r", "r.id"
    sql = f"SELECT r.id, r.title, r.source, r.n_ingredients, r.n_steps FROM {frm} WHERE {w} ORDER BY {order} LIMIT ?"
    rows = con.execute(sql, params + [limit]).fetchall()
    total = con.execute(f"SELECT COUNT(*) FROM {frm} WHERE {w}", params).fetchone()[0]
    hits = [Hit(*r) for r in rows]
    for h in hits:
        h.evidence = _evidence(con, h, include, exclude, exclude_tags, max_steps)
    return SearchResult(hits, total, "; ".join(human) or "all valid recipes", render(sql, params + [limit]))


def _evidence(con: sqlite3.Connection, h: Hit, include, exclude, exclude_tags, max_steps) -> list[str]:
    """Lines that prove each restriction for one recipe (or the count of lines checked)."""
    one = lambda sql, *a: con.execute(sql, (h.id, *a)).fetchone()
    out = []
    for t in include:
        c, p = t.cond("strict")
        row = one(f"SELECT raw FROM ingredient_lines WHERE recipe_id = ? AND is_alt = 0 AND {c} LIMIT 1", *p)
        out.append(f"has {t.text}: {row[0]!r}" if row else f"has {t.text}")
    for t in exclude:
        out.append(f"no {t.text}: 0 matching lines; checked {h.n_ingredients} lines")
    for tag in exclude_tags:
        row = one("SELECT t.level, l.raw FROM recipe_tags t JOIN ingredient_lines l ON l.recipe_id = t.recipe_id "
                  "AND l.line_no = t.evidence_line_no WHERE t.recipe_id = ? AND t.tag = ? LIMIT 1", tag)
        if not row:
            out.append(f"no {tag}: 0 {tag}-tagged lines; checked {h.n_ingredients} lines")
        elif row[0] == "alt":
            out.append(f"no {tag}: only as an alternative, use the {tag}-free option in {row[1]!r}")
        else:
            out.append(f"no {tag}: {row[1]!r} may contain {tag} (check the label)")
    if max_steps is not None:
        out.append(f"{h.n_steps} steps (limit {max_steps})")
    return out
