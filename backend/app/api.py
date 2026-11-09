"""FastAPI app. M0: only GET /api/health (record counts per raw file) to prove the host can download the data.

Counts come straight from the raw JSON so the deploy check does not depend on the DB (built in M1).
"""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI

DATA = Path(__file__).resolve().parent.parent.parent / "data"
app = FastAPI(title="Recipe Box")


@lru_cache(maxsize=1)
def raw_counts() -> dict[str, int]:
    """Record count per raw file. Reads data/counts.json written at build time (download.py);
    falls back to parsing the raw files, which can exceed 512 MB RAM on a small host."""
    cached = DATA / "counts.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    return {p.name: len(json.loads(p.read_text(encoding="utf-8"))) for p in sorted((DATA / "raw").glob("*.json"))}


@app.get("/api/health")
def health() -> dict:
    """Return status plus per-file record counts; status is 'error' if the data is missing."""
    counts = raw_counts()
    return {"status": "ok" if counts else "error", "records": counts, "total": sum(counts.values())}
