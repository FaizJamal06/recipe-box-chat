"""FastAPI app. So far only GET /api/health: per-source counts plus the build fingerprint (vocab size, line
and tag counts, comma splits, garlic/onion family counts, vocab hash) to compare a local build with the live one.

The runtime image ships recipes.db only (no raw JSON), so health reads the DB read-only.
"""
from functools import lru_cache

from fastapi import FastAPI

from .config import DB
from .db import connect, fingerprint

app = FastAPI(title="Recipe Box")


@lru_cache(maxsize=1)
def counts() -> dict:
    """{'sources': {source: {records, valid}}, 'fingerprint': {...}} computed once; {} if the DB is missing."""
    if not DB.exists():
        return {}
    con = connect(DB)
    try:
        rows = con.execute("SELECT source, COUNT(*), SUM(valid) FROM recipes GROUP BY source ORDER BY source").fetchall()
        return {"sources": {s: {"records": n, "valid": v} for s, n, v in rows}, "fingerprint": fingerprint(con)}
    finally:
        con.close()


@app.get("/api/health")
def health() -> dict:
    """Return status, per-source counts and the build fingerprint; status is 'error' if the DB is missing."""
    c = counts()
    src = c.get("sources", {})
    return {"status": "ok" if c else "error", "sources": src, "total": sum(x["records"] for x in src.values()),
            "valid": sum(x["valid"] for x in src.values()), "fingerprint": c.get("fingerprint", {})}
