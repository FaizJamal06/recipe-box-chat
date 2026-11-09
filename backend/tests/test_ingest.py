"""ingest.py end to end on tests/fixtures/mini.json (30 records across ar/epi/fn)."""
import json
import sqlite3
from pathlib import Path

import pytest

from app.ingest import build

FIXTURE = Path(__file__).parent / "fixtures" / "mini.json"


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    """Build a DB from the fixture (one JSON file per source, like data/raw/)."""
    d = tmp_path_factory.mktemp("mini")
    files = {}
    for source, recs in json.loads(FIXTURE.read_text(encoding="utf-8")).items():
        files[source] = d / f"{source}.json"
        files[source].write_text(json.dumps(recs), encoding="utf-8")
    build(d / "t.db", files)
    c = sqlite3.connect(d / "t.db")
    yield c
    c.close()


def one(con, sql, *args):
    """First row of a query."""
    return con.execute(sql, args).fetchone()


def test_validity(con):
    assert one(con, "SELECT COUNT(*), SUM(valid) FROM recipes") == (30, 23)
    bad = dict(con.execute("SELECT id, invalid_reason FROM recipes WHERE valid = 0").fetchall())
    assert bad == {"ar:a02": "empty_record", "ar:a03": "no_ingredients", "ar:a09": "no_title",
                   "epi:e04": "no_ingredients", "epi:e05": "no_instructions", "fn:f02": "no_title",
                   "fn:f03": "no_instructions"}
    assert one(con, "SELECT COUNT(*) FROM recipes_fts")[0] == 23  # only valid recipes are searchable


def test_originals_kept_and_advertisement_stripped(con):
    raw, n = one(con, "SELECT ingredients_raw, n_ingredients FROM recipes WHERE id = 'ar:a01'")
    assert "ADVERTISEMENT" in raw and n == 5
    assert one(con, "SELECT COUNT(*) FROM ingredient_lines WHERE raw LIKE '%ADVERTISEMENT%'")[0] == 0
    assert one(con, "SELECT canonical FROM ingredient_lines WHERE recipe_id = 'ar:a01' AND line_no = 0") == ("sugar",)


def test_steps_and_paragraph_format(con):
    q = "SELECT n_steps, n_steps_newline, n_sentences, is_paragraph_format FROM recipes WHERE id = ?"
    assert one(con, q, "ar:a04") == (4, 1, 4, 1)
    assert one(con, q, "fn:f04") == (4, 1, 4, 1)  # '212 F. and' does not split
    assert one(con, q, "ar:a01") == (3, 3, 4, 0)  # '350 degrees F. Cream' stays one sentence (by design)


def test_headers_compounds_alternatives(con):
    assert one(con, "SELECT SUM(is_header), COUNT(DISTINCT line_no) FROM ingredient_lines "
                    "WHERE recipe_id = 'epi:e03'") == (2, 8)
    assert one(con, "SELECT n_ingredients FROM recipes WHERE id = 'epi:e03'") == (6,)
    rows = con.execute("SELECT alt_group, is_alt, canonical FROM ingredient_lines WHERE recipe_id = 'fn:f01' "
                       "AND line_no = 0 ORDER BY alt_group").fetchall()
    assert rows == [(0, 0, "salt"), (1, 0, "black pepper")]
    rows = con.execute("SELECT alt_group, is_alt, canonical FROM ingredient_lines WHERE recipe_id = 'ar:a01' "
                       "AND line_no = 2 ORDER BY is_alt").fetchall()
    assert rows == [(0, 0, "butter"), (0, 1, "margarine")]
    assert one(con, "SELECT COUNT(*) FROM ingredient_lines WHERE recipe_id = 'ar:a05'") == (4,)  # kept whole


def tags(con, rid: str) -> dict:
    """{tag: level} for one recipe."""
    return dict(con.execute("SELECT tag, level FROM recipe_tags WHERE recipe_id = ?", (rid,)).fetchall())


def test_recipe_tags(con):
    assert "dairy" not in tags(con, "ar:a08")  # coconut/almond milk, butternut, vegan butter, dairy-free cheese
    assert tags(con, "ar:a01")["dairy"] == "may_contain"  # butter OR margarine: best option is margarine
    assert tags(con, "fn:f09")["dairy"] == "may_contain"
    assert tags(con, "ar:a06")["peanut"] == "contains" and tags(con, "ar:a06")["egg"] == "contains"
    assert tags(con, "fn:f10")["pork"] == "alt" and tags(con, "fn:f10")["meat"] == "contains"
    assert tags(con, "epi:e07") == {"dairy": "may_contain", "tree_nut": "contains"}  # cocoa butter is not dairy
    assert tags(con, "epi:e08")["egg"] == "contains"  # mayonnaise, not eggplant
    assert "gluten" not in tags(con, "fn:f08")
    t = tags(con, "epi:e09")
    assert t["pork"] == t["fish"] == t["meat"] == "contains"
    assert one(con, "SELECT evidence_line_no FROM recipe_tags WHERE recipe_id = 'ar:a01' AND tag = 'dairy'") == (2,)


def test_vocab_and_family_filled(con):
    assert one(con, "SELECT COUNT(*) FROM ingredient_lines WHERE canonical IS NOT NULL AND family IS NULL")[0] == 0
    assert one(con, "SELECT family FROM vocab WHERE canonical = 'red onion'") == ("onion",)
    assert one(con, "SELECT recipe_count FROM vocab WHERE canonical = 'salt'") == (5,)  # valid recipes only
