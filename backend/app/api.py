"""FastAPI app. M0: only GET /api/health (record counts per raw file) to prove the host can download the data.

Counts come straight from the raw JSON so the deploy check does not depend on the DB (built in M1).
"""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI

RAW = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
app = FastAPI(title="Recipe Box")


@lru_cache(maxsize=1)
def raw_counts() -> dict[str, int]:
    """Record count per raw JSON file; cached because parsing ~200 MB is slow."""
    return {p.name: len(json.loads(p.read_text(encoding="utf-8"))) for p in sorted(RAW.glob("*.json"))}


@app.get("/api/health")
def health() -> dict:
    """Return status plus per-file record counts; status is 'error' if the data is missing."""
    counts = raw_counts()
    return {"status": "ok" if counts else "error", "records": counts, "total": sum(counts.values())}
