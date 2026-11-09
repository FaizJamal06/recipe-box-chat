"""FastAPI app. M0/M1: only GET /api/health (record counts per source, from data/recipes.db).

The runtime image ships recipes.db only (no raw JSON), so health reads the DB read-only.
"""
import sqlite3
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI

DB = Path(__file__).resolve().parent.parent.parent / "data" / "recipes.db"
app = FastAPI(title="Recipe Box")


@lru_cache(maxsize=1)
def counts() -> dict[str, dict[str, int]]:
    """{source: {records, valid}} computed once; empty dict if the DB is missing."""
    if not DB.exists():
        return {}
    con = sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT source, COUNT(*), SUM(valid) FROM recipes GROUP BY source").fetchall()
    finally:
        con.close()
    return {s: {"records": n, "valid": v} for s, n, v in rows}


@app.get("/api/health")
def health() -> dict:
    """Return status plus per-source counts; status is 'error' if the DB is missing."""
    c = counts()
    return {"status": "ok" if c else "error", "sources": c,
            "total": sum(x["records"] for x in c.values()), "valid": sum(x["valid"] for x in c.values())}
