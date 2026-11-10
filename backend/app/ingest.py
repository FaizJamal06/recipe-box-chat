"""Raw JSON -> data/recipes.db (PRD 4.2-4.6). Memory-lean by design: one source file at a time,
batched executemany (BATCH rows), each file freed before the next, peak RSS printed at the end.

Pass 1 (per recipe): validity, step/sentence counts, every ingredient line parsed by normalize.py into
rows, recipe_tags. Rows sharing (recipe_id, line_no, alt_group) are alternatives ("butter or margarine");
different alt_group values on one line are separate items ("salt and pepper"); is_alt=0 marks the
primary. Originals are stored verbatim (ingredients_raw keeps ADVERTISEMENT); derived columns are separate.
Recipe tags = parsed items' tags + a keyword scan of each whole line (normalize.line_tags) as a safety net.
Pass 2 (SQL): comma lists of known canonicals are split (resplit), canonicals seen in < VOCAB_MIN valid
recipes fall back to their longest safe in-vocab word suffix (normalize.suffix_match), then
vocab(canonical, family, recipe_count) and the family column are filled.
Run: python -m backend.app.ingest   (from the repo root)
"""
import gc
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

from . import normalize as nz
from .config import VOCAB_MIN  # PRD 4.5 coverage target: canonical with recipe frequency >= 5

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "recipes.db"
BATCH = 5000
SOURCES = {"ar": "recipes_raw_nosource_ar.json", "epi": "recipes_raw_nosource_epi.json",
           "fn": "recipes_raw_nosource_fn.json"}

SCHEMA = """
CREATE TABLE recipes(id TEXT PRIMARY KEY, source TEXT, title TEXT, ingredients_raw TEXT,
    instructions_raw TEXT, n_ingredients INT, n_steps INT, n_sentences INT, valid INT, invalid_reason TEXT,
    n_steps_newline INT, is_paragraph_format INT);
CREATE TABLE ingredient_lines(recipe_id TEXT, line_no INT, raw TEXT, name_clean TEXT, canonical TEXT,
    family TEXT, qty REAL, unit TEXT, unit_family TEXT, alt_group INT, is_header INT, is_alt INT, is_not_food INT);
CREATE TABLE recipe_tags(recipe_id TEXT, tag TEXT, level TEXT, evidence_line_no INT);
CREATE TABLE vocab(canonical TEXT PRIMARY KEY, family TEXT, recipe_count INT);
CREATE TABLE meta(key TEXT PRIMARY KEY, value INT);
CREATE VIRTUAL TABLE recipes_fts USING fts5(id UNINDEXED, title, ingredients, tokenize='porter');
"""
INDEXES = """
CREATE INDEX ix_lines_canonical ON ingredient_lines(canonical);
CREATE INDEX ix_lines_recipe ON ingredient_lines(recipe_id);
CREATE INDEX ix_lines_family ON ingredient_lines(family);
CREATE INDEX ix_tags_tag ON recipe_tags(tag);
"""
TAG_RANK = {"alt": 1, "may_contain": 2, "contains": 3}


def peak_rss_mb() -> float:
    """Peak resident memory of this process in MB (Windows: peak working set; Linux/mac: ru_maxrss)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        return pmc.PeakWorkingSetSize / 2**20
    import resource
    kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # KB on Linux, bytes on macOS
    return kb / 1024 if sys.platform != "darwin" else kb / 2**20


_ABBREV = {"tsp", "tbsp", "tbs", "tbl", "oz", "approx", "f", "c", "lb", "lbs", "pkg", "fl", "qt", "pt", "no",
           "vs", "st", "dr", "mr", "mrs", "e.g", "i.e", "deg", "min", "mins", "hr", "hrs", "in", "ca", "pkgs"}
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def count_sentences(text: str) -> int:
    """Sentences in instructions. Splits on . ! ? + whitespace and newlines, but not after abbreviations
    (tsp., oz., approx., 350 F.) or a bare number ('1. Preheat'); decimals never split (no space after '.')."""
    n = 0
    for seg in (text or "").split("\n"):
        chunks = [c for c in _SENT_SPLIT.split(seg.strip()) if c]
        for i, c in enumerate(chunks):
            last = re.sub(r"[^a-z0-9.]", "", c.rsplit(None, 1)[-1].lower()).rstrip(".")
            if i == len(chunks) - 1 or not (last in _ABBREV or last.replace(".", "").isdigit()):
                n += 1
    return n


def steps(instr: str) -> tuple[int, int, int, int]:
    """(n_steps, n_sentences, n_steps_newline, is_paragraph_format) per PRD 4.4.
    A recipe written as one block of several sentences is paragraph-format; its effective
    n_steps is then its sentence count, otherwise the newline-segment count."""
    newline = sum(1 for seg in instr.split("\n") if seg.strip())
    sent = count_sentences(instr)
    para = int(newline == 1 and sent >= 2)
    return (sent if para else newline), sent, newline, para


def recipe_tags(rid: str, parsed: list[tuple[int, list, tuple]]) -> list[tuple]:
    """One (recipe_id, tag, level, evidence_line_no) per tag. Per item, the best option decides:
    'contains' if every option contains the tag, 'may_contain' if the best option may contain it,
    'alt' if the tag is only in options that have a tag-free alternative (eligible, with a note)."""
    best: dict[str, tuple[int, int]] = {}  # tag -> (rank, line_no)

    def bump(tag: str, rank: int, line_no: int) -> None:
        if rank > best.get(tag, (0, 0))[0]:
            best[tag] = (rank, line_no)

    for line_no, items, scan in parsed:
        seen = set()
        for it in items:
            opts = [dict(o.tags) for o in it.options]
            for tag in {t for o in opts for t in o}:
                seen.add(tag)
                lv = min(nz.LEVELS[o.get(tag)] for o in opts)
                bump(tag, TAG_RANK["contains"] if lv == 2 else TAG_RANK["may_contain"] if lv == 1
                     else TAG_RANK["alt"], line_no)
        # safety net: a tag word on the line that no parsed item explains ('salt, pepper and butter')
        for tag, lv in scan:
            if tag not in seen:
                bump(tag, TAG_RANK[lv], line_no)
    names = {v: k for k, v in TAG_RANK.items()}
    return [(rid, tag, names[r], ln) for tag, (r, ln) in sorted(best.items())]


def line_rows(rid: str, n: int, s: str, items: list) -> list[tuple]:
    """ingredient_lines rows for one real line: one per option; a line naming nothing keeps canonical NULL."""
    if not items:
        return [(rid, n, s, None, None, None, None, None, None, None, 0, 0, 0)]
    return [(rid, n, s, o.clean, o.canonical, None, it.qty, it.unit, it.unit_family, g, 0, int(k > 0), 0)
            for g, it in enumerate(items) for k, o in enumerate(it.options)]


def convert(source: str, key: str, rec: dict) -> tuple:
    """One raw record -> (recipe_row, line_rows, fts_row, tag_rows). Applies the single validity rule (4.3)."""
    rid = f"{source}:{key}"
    title = rec.get("title") if isinstance(rec.get("title"), str) else ""
    instr = rec.get("instructions") if isinstance(rec.get("instructions"), str) else ""
    ing = rec.get("ingredients") if isinstance(rec.get("ingredients"), list) else []
    rows, parsed, real = [], [], []
    for n, x in enumerate(ing):
        s = x.replace("ADVERTISEMENT", "").strip() if isinstance(x, str) else ""
        if not s:
            continue
        items = nz.parse_line(s)
        if items and (items[0].is_header or items[0].not_food):  # kept, but not an ingredient
            rows.append((rid, n, s, None, None, None, None, None, None, None, int(items[0].is_header), 0,
                         int(items[0].not_food)))
            if items[0].is_header and (lt := nz.line_tags(s)):  # 'Pie Crust, recipe follows': still tags it
                parsed.append((n, [], lt))
            continue
        real.append(s)
        parsed.append((n, items, nz.line_tags(s)))
        rows.extend(line_rows(rid, n, s, items))
    n_steps, n_sent, n_newline, para = steps(instr)
    reason = ("empty_record" if not rec else "no_title" if not title.strip()
              else "no_ingredients" if not real else "no_instructions" if not instr.strip() else None)
    row = (rid, source, title, json.dumps(ing, ensure_ascii=False), instr, len(real), n_steps, n_sent,
           int(reason is None), reason, n_newline, para)
    return row, rows, (rid, title, "\n".join(real)), recipe_tags(rid, parsed)


def flush(con: sqlite3.Connection, recs: list, lines: list, fts: list, tags: list) -> None:
    """Write one batch with executemany and clear the buffers."""
    con.executemany("INSERT INTO recipes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", recs)
    con.executemany("INSERT INTO ingredient_lines VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", lines)
    con.executemany("INSERT INTO recipes_fts(id,title,ingredients) VALUES (?,?,?)", fts)
    con.executemany("INSERT INTO recipe_tags VALUES (?,?,?,?)", tags)
    recs.clear(), lines.clear(), fts.clear(), tags.clear()


COUNT_SQL = """SELECT l.canonical, COUNT(DISTINCT CASE WHEN r.valid = 1 THEN l.recipe_id END)
FROM ingredient_lines l JOIN recipes r ON r.id = l.recipe_id
WHERE l.canonical IS NOT NULL GROUP BY l.canonical"""


def resplit(con: sqlite3.Connection, vocab: set) -> int:
    """Comma lists whose every part is a known canonical ('salt, pepper and paprika') -> one row group per
    part. Needs the vocab, so it runs in pass 2. recipe_tags need no update: the pass-1 line scan already
    saw every word. shortcut: an alternative inside such a list can rank a tag one level stricter than needed."""
    todo = [(rid, n, s, sp) for rid, n, s in con.execute(
        "SELECT DISTINCT recipe_id, line_no, raw FROM ingredient_lines WHERE is_header = 0 AND raw LIKE '%,%'"
    ).fetchall() if (sp := nz.comma_split(s, vocab))]
    con.executemany("DELETE FROM ingredient_lines WHERE recipe_id = ? AND line_no = ?", [t[:2] for t in todo])
    con.executemany("INSERT INTO ingredient_lines VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [row for rid, n, s, sp in todo for row in line_rows(rid, n, s, sp)])
    return len(todo)


def finalize(con: sqlite3.Connection, vocab_min: int) -> None:
    """Pass 2: rare canonicals -> longest in-vocab suffix, then fill vocab and ingredient_lines.family.
    recipe_count counts valid recipes only (that is what stats and matching see)."""
    counts = dict(con.execute(COUNT_SQL).fetchall())
    vocab = {c for c, n in counts.items() if n >= vocab_min}
    splits = resplit(con, vocab)
    print(f"comma lists split: {splits:,}")
    remap = [(c, m) for c, n in counts.items() if n < vocab_min and (m := nz.suffix_match(c, vocab))]
    con.executemany("INSERT INTO meta VALUES (?,?)", [("comma_splits", splits), ("rare_remapped", len(remap))])
    del counts
    con.execute("CREATE TEMP TABLE remap(old TEXT PRIMARY KEY, new TEXT)")
    con.executemany("INSERT INTO remap VALUES (?,?)", remap)
    con.execute("UPDATE ingredient_lines SET canonical = (SELECT new FROM remap WHERE old = canonical) "
                "WHERE canonical IN (SELECT old FROM remap)")
    con.executemany("INSERT INTO vocab VALUES (?,?,?)",
                    ((c, nz.family_for(c), n) for c, n in con.execute(COUNT_SQL).fetchall()))
    con.execute("UPDATE ingredient_lines SET family = (SELECT family FROM vocab v WHERE v.canonical = "
                "ingredient_lines.canonical) WHERE canonical IS NOT NULL")
    print(f"vocab: {len(vocab):,} canonicals with >= {vocab_min} recipes; {len(remap):,} rare names remapped")


def build(db: Path, files: dict[str, Path], vocab_min: int = VOCAB_MIN) -> None:
    """Build `db` from scratch from {source: json_path}, one file in memory at a time.

    Writes to `<db>.tmp` and swaps it in only at the end, so an interrupted run (journaling is off)
    never leaves a half-written file under the real name."""
    t0 = time.time()
    final, db = db, db.with_name(db.name + ".tmp")
    final.parent.mkdir(exist_ok=True)
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;" + SCHEMA)
    for source, path in files.items():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        recs, lines, fts, tags = [], [], [], []
        for key, rec in data.items():
            r, l, fx, tg = convert(source, key, rec if isinstance(rec, dict) else {})
            recs.append(r), lines.extend(l), tags.extend(tg)
            if r[8]:  # only valid recipes are searchable
                fts.append(fx)
            if len(recs) >= BATCH:
                flush(con, recs, lines, fts, tags)
        flush(con, recs, lines, fts, tags)
        con.commit()
        del data
        gc.collect()
        print(f"{source}: done, {time.time() - t0:.0f}s, peak RSS so far {peak_rss_mb():.0f} MB", flush=True)
    con.executescript(INDEXES)
    finalize(con, vocab_min)
    n, v = con.execute("SELECT COUNT(*), SUM(valid) FROM recipes").fetchone()
    con.commit()
    con.close()
    db = db.replace(final)
    print(f"recipes={n:,} valid={v:,} db={db.stat().st_size / 2**20:.0f} MB "
          f"time={time.time() - t0:.0f}s PEAK RSS={peak_rss_mb():.0f} MB")


if __name__ == "__main__":
    build(DB, {s: RAW / f for s, f in SOURCES.items()})
