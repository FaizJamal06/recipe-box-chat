"""T1 search: FTS5 BM25 candidates + SQL include/exclude filters, with per-restriction evidence (PRD 6.1).

Hard constraints are SQL filters on the complete set, never post-hoc checks on a top-k: included ingredients
use the strict definition (asked for penne -> penne), excluded ones the broad one (no garlic -> no garlic
powder either), excluded tags drop 'contains' (and 'may_contain' + unverified recipes in strict mode;
lenient mode keeps unverified recipes, ranked after every fully verified one and folded behind one summary
line; each keeps its warning naming the line, see safety.py).
"""
import re
import sqlite3
from dataclasses import dataclass, field
from difflib import get_close_matches
from functools import lru_cache

import yaml

from . import normalize as nz
from . import safety
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
    total: int  # all eligible recipes, not just the ones shown (verified + unverified)
    filters: str
    sql: str
    more: list = field(default_factory=list)  # lenient mode: top recipes with an unverified ingredient, ranked last
    n_unverified: int = 0  # eligible recipes with an unverified ingredient for an excluded tag


@lru_cache(maxsize=2)
def _vocab_words(vocab: frozenset) -> tuple:
    return tuple(sorted({w for c in vocab for w in c.split() if len(w) > 2}))


def correct(query: str, vocab: frozenset) -> str:
    """Spelling fix for a query that found nothing, from words in the dataset vocab ('chiken' -> 'chicken')."""
    words = _vocab_words(vocab)
    known = set(words)
    # 0.88: 'chiken' -> 'chicken' (0.92) but not 'weather' -> 'water' (0.83)
    fix = lambda w: w if w in known or len(w) < 4 else (get_close_matches(w, words, n=1, cutoff=0.88) or [w])[0]
    return " ".join(fix(w) for w in re.findall(r"[a-z]+", (query or "").lower()))


def _fts(text: str) -> str:
    """Plain words -> an FTS5 query that ANDs quoted tokens (no FTS syntax from user text)."""
    return " ".join(f'"{w}"' for w in re.findall(r"[a-z0-9]+", (text or "").lower()))


SAFE = yaml.safe_load((nz.LEX / "synonyms.yaml").read_text(encoding="utf-8")).get("mention_safe") or {}


def mention_words(t: Term) -> list[str]:
    """Words whose mention in an ingredient line counts as containing an excluded ingredient."""
    return list(dict.fromkeys(x.replace('"', "") for x in (t.text.lower(), t.canonical, *t.broad_names)))


def _mention_fts(t: Term) -> str:
    """FTS5 query for the mention net: '"cream" NOT ("cream of tartar" OR ...)' per word, ORed.
    ponytail: NOT is per recipe, so a recipe with cream of tartar AND a stray unparsed 'cream' slips through
    this net (the canonical/family filter still catches parsed cream lines)."""
    q = lambda w: f'("{w}" NOT ({" OR ".join(chr(34) + s + chr(34) for s in SAFE[w])}))' if SAFE.get(w) else f'"{w}"'
    return "ingredients : (" + " OR ".join(q(w) for w in mention_words(t)) + ")"


def _mentions(t: Term, line: str) -> bool:
    """Does this ingredient line mention the excluded word (safe phrases masked first)?"""
    for w in mention_words(t):
        x = re.sub("|".join(re.escape(s) for s in SAFE[w]), " ", line, flags=re.I) if SAFE.get(w) else line
        if re.search(rf"\b{re.escape(w)}", x, re.I):
            return True
    return False


def hard_where(include: list[Term] = (), exclude: list[Term] = (), exclude_tags: list[str] = (),
               max_steps: int | None = None, strict_may_contain: bool = False) -> tuple[str, list, list[str]]:
    """Hard constraints as one SQL WHERE over `recipes r`, its params, and one label per constraint.
    Shared by search and match so both apply exactly the same rules."""
    w, params, _ = Filters(all_of=list(include), none_of=list(exclude)).where("strict", none_mode="broad")
    where = [w]
    for t in exclude:  # safety net: also any ingredient text naming it ('creamy roasted garlic ... sauce')
        where.append("r.id NOT IN (SELECT id FROM recipes_fts WHERE recipes_fts MATCH ?)")
        params.append(_mention_fts(t))
    human = [f"contains {t.text}" for t in include] + [f"no {t.text}" for t in exclude]
    levels = ("contains", "may_contain") if strict_may_contain else ("contains",)
    for tag in exclude_tags:
        where.append(f"r.id NOT IN (SELECT recipe_id FROM recipe_tags WHERE tag = ? AND level IN "
                     f"({','.join('?' * len(levels))}))")
        params += [tag, *levels]
        if strict_may_contain:  # unknown is not safe: strict mode also drops recipes it couldn't verify
            where.append("r.id NOT IN (SELECT recipe_id FROM unverified WHERE tag = ?)")
            params.append(tag)
        human.append(f"no {tag} ({' or '.join(levels + (('unverified',) if strict_may_contain else ()))})")
    if max_steps is not None:
        where.append("r.n_steps <= ?")
        params.append(max_steps)
        human.append(steps_label(max_steps))
    return " AND ".join(where), params, human


def steps_label(n: int) -> str:
    return f"at most {n} step{'' if n == 1 else 's'}"


def search(con: sqlite3.Connection, query_text: str = "", include: list[Term] = (),
           exclude: list[Term] = (), exclude_tags: list[str] = (), max_steps: int | None = None,
           strict_may_contain: bool = False, limit: int = 10, any_words: list[str] = ()) -> SearchResult:
    """Top `limit` valid recipes by BM25 (title weighted 3x) among those passing every hard filter.
    any_words: title must contain at least one of these words/phrases (the cuisine keyword proxy)."""
    w, params, human = hard_where(include, exclude, exclude_tags, max_steps, strict_may_contain)
    q = _fts(query_text)
    if any_words:
        words = [x for x in (re.sub(r"[^a-z' -]", "", x.lower()).strip() for x in any_words) if x]
        qa = "title : (" + " OR ".join(f'"{x}"' for x in words) + ")"
        q = f"{q} AND {qa}" if q else qa
        human.insert(0, "title has any of: " + ", ".join(words))
    if q:
        frm, order = "recipes_fts JOIN recipes r ON r.id = recipes_fts.id", \
            "(r.title LIKE ?) DESC, bm25(recipes_fts, 3.0, 1.0), r.id"  # exact phrase in the title first
        params = [q] + params
        w = "recipes_fts MATCH ? AND " + w
        if _fts(query_text):
            human.insert(0, f"matches '{query_text}'")
    else:
        frm, order = "recipes r", "r.id"
    flag, fp = safety.flag_sql(exclude_tags, strict_may_contain)  # fully verified recipes rank first
    sql = (f"SELECT r.id, r.title, r.source, r.n_ingredients, r.n_steps, {flag} AS unverified FROM {frm} WHERE {w} "
           f"ORDER BY unverified, {order}")
    tail = [f"%{' '.join((query_text or '').split())}%"] if q else []
    rows = con.execute(sql, fp + params + tail).fetchall()  # every eligible row once: the total is len(rows)
    total = len(rows)  # ponytail: one pass instead of a 2nd COUNT query; LIMIT + COUNT if result sets get huge
    hits = [Hit(*r[:5]) for r in rows if not r[5]][:limit]
    more = [Hit(*r[:5]) for r in rows if r[5]][:limit]
    for h in hits + more:
        h.evidence = _evidence(con, h, include, exclude, exclude_tags, max_steps)
    return SearchResult(hits, total, "; ".join(human) or "all valid recipes", render(sql, fp + params + tail) +
                        f" -- first {limit} shown", more, sum(r[5] for r in rows))


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
        bad = row[0] if row else next((x for x in lines if _mentions(t, x)), None)
        out.append(f"VIOLATES no {t.text}: {bad!r}" if bad else
                   f"no {t.text}: 0 lines name or mention it; checked {h.n_ingredients} lines")
    unv = safety.lines(con, h.id, exclude_tags)
    for tag in exclude_tags:
        row = one("SELECT t.level, l.raw FROM recipe_tags t JOIN ingredient_lines l ON l.recipe_id = t.recipe_id "
                  "AND l.line_no = t.evidence_line_no WHERE t.recipe_id = ? AND t.tag = ? LIMIT 1", tag)
        if row and row[0] == "contains":
            out.append(f"VIOLATES no {tag}: {row[1]!r}")
            continue
        if row and row[0] == "may_contain":
            out.append(f"no {tag}: {row[1]!r} may contain {tag} (check the label)")
        elif row and row[1] not in unv.get(tag, []):  # 'alt' with a verified tag-free option
            out.append(f"no {tag}: only as an alternative, use the {tag}-free option in {row[1]!r}")
        if unv.get(tag):  # unknown is not safe: name the lines we couldn't verify
            out.append(f"no {tag}: {safety.warning(unv[tag])}")
        elif not row:
            out.append(f"no {tag}: 0 {tag}-tagged lines, all {h.n_ingredients} lines verified")
    if max_steps is not None:
        out.append(f"{'VIOLATES ' if h.n_steps > max_steps else ''}{h.n_steps} steps (limit {max_steps})")
    return out
