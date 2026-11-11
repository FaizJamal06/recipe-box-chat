"""Unknown is not safe: allergen / diet filters only pass an ingredient they could verify.

For a restriction "no T", an ingredient option is VERIFIED SAFE when
- its canonical is known (a native vocab canonical: >= VOCAB_MIN valid recipes before the suffix fallback, so the
  lexicon has seen it) and none of its tags is T, or
- the line scanner explicitly cleared T for that line (a free_if or except phrase of T: 'dairy-free',
  'coconut milk', 'rice noodles').
An item ("butter or margarine") is verified when at least one of its options is: an "or" alternative only makes
the recipe compliant if that option is itself verified. An item with no verified option, at least one unknown
option, and no T keyword anywhere on the line is UNVERIFIED for T. (Lines with a T keyword are already in
recipe_tags as contains / may_contain.) Unverified items are stored in unverified(recipe_id, tag, line_no):
lenient filters show the recipe with a warning that names the line, strict mode excludes it.
"""
import sqlite3
from itertools import groupby

from . import normalize as nz

TAGS = tuple(nz.TAG_RE)


def cleared(raw: str) -> frozenset:
    """Tags the line scanner explicitly rules out on this line (a free_if or except phrase of the tag)."""
    s = nz.clean_text(raw)
    return frozenset(t for t, (free, exc, *_) in nz.TAG_RE.items()
                     if (free and free.search(s)) or (exc and exc.search(s)))


def item_unverified(options: list, raw: str, known) -> set[str]:
    """Tags for which this item has no verified-safe option. options: canonicals of the item (None = the line
    named nothing we could parse); known: native vocab canonicals."""
    if all(c is not None and c in known for c in options):
        return set()  # every option known: each tag is either verified absent or recorded in recipe_tags
    tags = [dict(nz.tags_for(c)) if c else {} for c in options]
    # a T keyword on the line that no option explains ('salt, pepper and butter') is recorded in recipe_tags; one
    # an option explains ('penne or bucatini') says nothing about the other options, which must be verified
    skip = {t for t, _ in nz.line_tags(raw) if not any(t in tg for tg in tags)} | cleared(raw)
    out = set()
    for t in TAGS:
        if t in skip:
            continue
        free = [c for c, tg in zip(options, tags) if t not in tg]  # options without a T keyword
        if free and all(c is None or c not in known for c in free):
            out.add(t)
    return out


UNKNOWN_LINES = """SELECT l.recipe_id, l.line_no, l.alt_group, l.canonical, l.raw FROM ingredient_lines l
JOIN recipes r ON r.id = l.recipe_id WHERE r.valid = 1 AND l.is_header = 0 AND l.is_not_food = 0
AND (l.recipe_id, l.line_no) IN (SELECT recipe_id, line_no FROM ingredient_lines WHERE is_header = 0
     AND is_not_food = 0 AND (canonical IS NULL OR canonical NOT IN (SELECT c FROM known)))
ORDER BY l.recipe_id, l.line_no, l.alt_group"""


def build_table(con: sqlite3.Connection, known: set) -> dict[str, int]:
    """Ingest pass 2 (before the suffix remap, so canonicals are as parsed): fill `unverified`.
    Only lines with an unknown option can be unverified, so only those are read. Returns {tag: recipes}."""
    con.execute("CREATE TEMP TABLE known(c TEXT PRIMARY KEY)")
    con.executemany("INSERT INTO known VALUES (?)", ((c,) for c in known))
    rows = set()
    for (rid, n, _), grp in groupby(con.execute(UNKNOWN_LINES).fetchall(), key=lambda r: r[:3]):
        grp = list(grp)
        rows |= {(rid, t, n) for t in item_unverified([r[3] for r in grp], grp[0][4], known)}
    con.executemany("INSERT INTO unverified VALUES (?,?,?)", sorted(rows))
    con.execute("CREATE INDEX ix_unverified ON unverified(tag, recipe_id)")
    return dict(con.execute("SELECT tag, COUNT(DISTINCT recipe_id) FROM unverified GROUP BY tag ORDER BY tag"))


def recipe_unverified(lines: list[tuple[int, str]], known) -> dict[str, list[int]]:
    """The same rule for one recipe straight from raw lines (evaluation scripts): {tag: [line_no, ...]}."""
    out: dict[str, list[int]] = {}
    for n, raw in lines:
        items = nz.parse_line(raw)
        if items and (items[0].is_header or items[0].not_food):
            continue
        for opts in ([[o.canonical for o in it.options] for it in items] or [[None]]):
            for t in item_unverified(opts, raw, known):
                out.setdefault(t, []).append(n)
    return out


def lines(con: sqlite3.Connection, rid: str, tags) -> dict[str, list[str]]:
    """{tag: [raw lines that couldn't be verified]} for one recipe and the given tags."""
    tags = list(tags)
    if not tags:
        return {}
    out: dict[str, list[str]] = {}
    for tag, raw in con.execute(
            f"SELECT u.tag, MIN(l.raw) FROM unverified u JOIN ingredient_lines l ON l.recipe_id = u.recipe_id AND "
            f"l.line_no = u.line_no WHERE u.recipe_id = ? AND u.tag IN ({','.join('?' * len(tags))}) "
            f"GROUP BY u.tag, u.line_no ORDER BY u.tag, u.line_no", (rid, *tags)):
        out.setdefault(tag, []).append(raw)
    return out


def warning(raws: list[str]) -> str:
    """'⚠ 1 ingredient couldn't be verified: '<raw line>''."""
    n = len(raws)
    return f"{n} ingredient{'' if n == 1 else 's'} couldn't be verified: " + ", ".join(f"'{r}'" for r in raws[:3]) \
        + (" …" if n > 3 else "")


def warnings(con: sqlite3.Connection, rid: str, tags) -> list[str]:
    """Lenient-mode warnings for one recipe and the excluded tags: may_contain lines + lines not verified."""
    tags, out = list(tags), []
    for tag in tags:
        row = con.execute("SELECT l.raw FROM recipe_tags t JOIN ingredient_lines l ON l.recipe_id = t.recipe_id AND "
                          "l.line_no = t.evidence_line_no WHERE t.recipe_id = ? AND t.tag = ? AND t.level = "
                          "'may_contain' LIMIT 1", (rid, tag)).fetchone()
        if row:
            out.append(f"no {tag}: {row[0]!r} may contain {tag} (check the label)")
    return out + [f"no {tag}: {warning(raws)}" for tag, raws in lines(con, rid, tags).items()]


def flag_sql(tags, strict: bool, rid: str = "r.id") -> tuple[str, list]:
    """SQL expression: 1 when the recipe has an unverified ingredient for any of `tags` (lenient mode ranks those
    recipes last and folds them behind one summary line). Strict mode already excludes them: constant 0."""
    tags = list(tags)
    if strict or not tags:
        return "0", []
    return (f"EXISTS(SELECT 1 FROM unverified u WHERE u.recipe_id = {rid} AND u.tag IN "
            f"({','.join('?' * len(tags))}))", tags)


def summary(n: int) -> str:
    """The one line that replaces per-card noise: unverified recipes are ranked last and folded."""
    return (f"{n:,} more recipe{' matches' if n == 1 else 's match'} but {'has' if n == 1 else 'have'} an "
            "ingredient I couldn't verify; turn on strict to hide them")
