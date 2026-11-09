"""Raw JSON -> data/recipes.db (PRD 4.2, 4.3, 4.4, 4.6). Memory-lean by design: one source file at a time,
batched executemany (BATCH rows), each file freed before the next, peak RSS printed at the end.

Why: the Docker builder and a 512 MB Free runtime must both cope; originals are stored verbatim
(including ADVERTISEMENT) and derived columns are separate. Canonical/family/qty columns of
ingredient_lines stay NULL until normalize.py lands (M1).
Run: python backend/app/ingest.py
"""
import gc
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "recipes.db"
BATCH = 5000
SOURCES = {"ar": "recipes_raw_nosource_ar.json", "epi": "recipes_raw_nosource_epi.json",
           "fn": "recipes_raw_nosource_fn.json"}

SCHEMA = """
CREATE TABLE recipes(id TEXT PRIMARY KEY, source TEXT, title TEXT, ingredients_raw TEXT,
    instructions_raw TEXT, n_ingredients INT, n_steps INT, n_sentences INT, valid INT, invalid_reason TEXT);
CREATE TABLE ingredient_lines(recipe_id TEXT, line_no INT, raw TEXT, name_clean TEXT, canonical TEXT,
    family TEXT, qty REAL, unit TEXT, unit_family TEXT, alt_group INT, is_header INT);
CREATE TABLE recipe_tags(recipe_id TEXT, tag TEXT, level TEXT, evidence_line_no INT);
CREATE TABLE vocab(canonical TEXT PRIMARY KEY, family TEXT, recipe_count INT);
CREATE VIRTUAL TABLE recipes_fts USING fts5(id UNINDEXED, title, ingredients, tokenize='porter');
"""
INDEXES = """
CREATE INDEX ix_lines_canonical ON ingredient_lines(canonical);
CREATE INDEX ix_lines_recipe ON ingredient_lines(recipe_id);
CREATE INDEX ix_tags_tag ON recipe_tags(tag);
"""
SENTENCE_END = re.compile(r"[.!?]+(?:\s|$)")


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


def real_lines(ing) -> list[tuple[int, str, int]]:
    """(line_no, text, is_header) for ingredient entries that are non-empty after stripping ADVERTISEMENT.
    Header heuristic: ends with ':' ('For the sauce:'); refined in M1."""
    out = []
    for i, x in enumerate(ing if isinstance(ing, list) else []):
        s = x.replace("ADVERTISEMENT", "").strip() if isinstance(x, str) else ""
        if s:
            out.append((i, s, int(s.endswith(":"))))
    return out


def convert(source: str, key: str, rec: dict) -> tuple:
    """Turn one raw record into (recipe_row, line_rows, fts_row). Applies the single validity rule (4.3)."""
    rid = f"{source}:{key}"
    title = rec.get("title") if isinstance(rec.get("title"), str) else ""
    instr = rec.get("instructions") if isinstance(rec.get("instructions"), str) else ""
    ing = rec.get("ingredients")
    lines = real_lines(ing)
    real = [(n, s) for n, s, h in lines if not h]
    n_steps = sum(1 for seg in instr.split("\n") if seg.strip())
    n_sent = len(SENTENCE_END.findall(instr))
    reason = ("empty_record" if not rec else "no_title" if not title.strip()
              else "no_ingredients" if not real else "no_instructions" if not instr.strip() else None)
    row = (rid, source, title, json.dumps(ing if isinstance(ing, list) else [], ensure_ascii=False),
           instr, len(real), n_steps, n_sent, int(reason is None), reason)
    return row, [(rid, n, s, None, None, None, None, None, None, None, h) for n, s, h in lines], \
        (rid, title, "\n".join(s for _, s in real))


def flush(con: sqlite3.Connection, recs: list, lines: list, fts: list) -> None:
    """Write one batch with executemany and clear the buffers."""
    con.executemany("INSERT INTO recipes VALUES (?,?,?,?,?,?,?,?,?,?)", recs)
    con.executemany("INSERT INTO ingredient_lines VALUES (?,?,?,?,?,?,?,?,?,?,?)", lines)
    con.executemany("INSERT INTO recipes_fts(id,title,ingredients) VALUES (?,?,?)", [f for f in fts if f[0]])
    recs.clear(), lines.clear(), fts.clear()


def main() -> None:
    """Build data/recipes.db from scratch, one source file at a time."""
    t0 = time.time()
    DB.parent.mkdir(exist_ok=True)
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;" + SCHEMA)
    for source, fname in SOURCES.items():
        with open(RAW / fname, encoding="utf-8") as f:
            data = json.load(f)
        recs, lines, fts = [], [], []
        for key, rec in data.items():
            r, l, fx = convert(source, key, rec)
            recs.append(r), lines.extend(l)
            fts.append(fx if r[8] else (None,) * 3)  # only valid recipes are searchable
            if len(recs) >= BATCH:
                flush(con, recs, lines, fts)
        flush(con, recs, lines, fts)
        con.commit()
        del data
        gc.collect()
        print(f"{source}: done, peak RSS so far {peak_rss_mb():.0f} MB", flush=True)
    con.executescript(INDEXES)
    n, v = con.execute("SELECT COUNT(*), SUM(valid) FROM recipes").fetchone()
    con.commit()
    con.close()
    print(f"recipes={n:,} valid={v:,} db={DB.stat().st_size / 2**20:.0f} MB "
          f"time={time.time() - t0:.0f}s PEAK RSS={peak_rss_mb():.0f} MB")


if __name__ == "__main__":
    main()
