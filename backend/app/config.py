"""Paths and tunables (DB path, raw data dir, LLM model, weights) read from env/.env in one place."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB = Path(os.environ.get("RECIPES_DB", ROOT / "data" / "recipes.db"))
VOCAB_MIN = 5  # a canonical "exists" for matching when >= this many valid recipes use it (PRD 4.5)
