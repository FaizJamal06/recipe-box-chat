"""Paths and tunables (DB path, raw data dir, LLM model, weights) read from env/.env in one place."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB = Path(os.environ.get("RECIPES_DB", ROOT / "data" / "recipes.db"))
VOCAB_MIN = 5  # a canonical "exists" for matching when >= this many valid recipes use it (PRD 4.5)


def load_env(path: Path = ROOT / ".env") -> None:
    """KEY=VALUE lines from .env into os.environ; real environment variables win (Railway sets them)."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.partition("=")
            if sep and not k.strip().startswith("#"):
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
LLM_CACHE = ROOT / "data" / "llm_cache.sqlite"
