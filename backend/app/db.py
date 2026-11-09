"""SQLite connection helper (stdlib sqlite3, FTS5). One file DB keeps counts reproducible and deploys trivial.

Dataset facts every answer states (total, valid, invalid breakdown) are queried once at startup, never
hardcoded, so they always match the DB that is actually being served.
"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import DB, VOCAB_MIN


def connect(path: Path = DB) -> sqlite3.Connection:
    """Read-only connection; the runtime never writes to the recipe DB."""
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found; build it with: python -m backend.app.ingest")
    return sqlite3.connect(f"{Path(path).as_uri()}?mode=ro", uri=True, check_same_thread=False)


@dataclass(frozen=True)
class Dataset:
    """Startup snapshot of the DB: record counts and the known-canonical vocabulary."""
    total: int
    valid: int
    invalid: tuple  # ((reason, count), ...) largest first
    vocab: frozenset

    def header(self, n: int) -> str:
        """'N of {valid} valid recipes ({total} records; invalid: {breakdown})'."""
        bd = ", ".join(f"{reason} {k:,}" for reason, k in self.invalid) or "none"
        return f"{n:,} of {self.valid:,} valid recipes ({self.total:,} records; invalid: {bd})"


def load_dataset(con: sqlite3.Connection) -> Dataset:
    """Query the counts and vocab once (call at startup)."""
    (total, valid), = con.execute("SELECT COUNT(*), COALESCE(SUM(valid), 0) FROM recipes").fetchall()
    invalid = tuple(con.execute("SELECT invalid_reason, COUNT(*) FROM recipes WHERE valid = 0 "
                                "GROUP BY 1 ORDER BY 2 DESC, 1").fetchall())
    vocab = frozenset(c for c, in con.execute("SELECT canonical FROM vocab WHERE recipe_count >= ?", (VOCAB_MIN,)))
    return Dataset(total, valid, invalid, vocab)
