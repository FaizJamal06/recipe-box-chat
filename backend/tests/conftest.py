"""Shared fixture: the 30-recipe mini dataset written out like data/raw/ and built into a DB once."""
import json
from pathlib import Path

import pytest

from app.ingest import build

FIXTURE = Path(__file__).parent / "fixtures" / "mini.json"


def fixture_files(d: Path) -> dict:
    """Write mini.json as one JSON file per source (like data/raw/) and return {source: path}."""
    files = {}
    for source, recs in json.loads(FIXTURE.read_text(encoding="utf-8")).items():
        files[source] = d / f"{source}.json"
        files[source].write_text(json.dumps(recs), encoding="utf-8")
    return files


@pytest.fixture(scope="session")
def mini(tmp_path_factory) -> tuple[Path, dict]:
    """(db path, raw files) for the fixture, built with the real VOCAB_MIN."""
    d = tmp_path_factory.mktemp("mini_db")
    files = fixture_files(d)
    build(d / "t.db", files)
    return d / "t.db", files
