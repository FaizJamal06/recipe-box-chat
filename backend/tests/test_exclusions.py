"""Hard exclusions respect word boundaries: an excluded word must not drop recipes that merely contain it
inside another word or a different product (eggplant, unsalted butter, cream of tartar). Built on a tiny
purpose-made DB so each case has exactly one recipe that should survive and one that should go."""
import dataclasses
import json

import pytest

from app import stats
from app.db import connect, load_dataset
from app.ingest import build
from app.search import search

RECIPES = {
    "x1": ("Eggplant Stew", ["1 large eggplant, cubed", "2 tomatoes", "1 tablespoon olive oil"]),
    "x2": ("Omelet", ["2 eggs", "1 tablespoon butter"]),
    "x3": ("Butter Cookies", ["1 cup unsalted butter", "2 cups flour", "1/2 cup sugar"]),
    "x4": ("Salted Almonds", ["2 cups almonds", "1 teaspoon salt"]),
    "x5": ("Snickerdoodles", ["1 cup shortening", "2 cups flour", "2 teaspoons cream of tartar", "1 cup sugar"]),
    "x6": ("Cream Sauce", ["1 cup heavy cream", "1 tablespoon flour"]),
    # wheat-allergy safety: every pasta option must be tagged, rice noodles are fine, soba is may_contain
    "x7": ("Cacio e Pepe", ["6 ounces penne or bucatini", "1/2 cup grated pecorino"]),
    "x8": ("Rice Noodle Bowl", ["8 ounces rice noodles", "1 cup tofu"]),
    "x9": ("Soba Salad", ["8 ounces soba noodles", "1 cucumber"]),
    "x10": ("Cavatapi Ragu", ["8 ounces cavatapi or penne pasta, uncooked", "1 cup tomato sauce"]),
    "x11": ("Tart", ["Pie Crust, recipe follows", "1 cup sugar"]),
}


@pytest.fixture(scope="module")
def eng(tmp_path_factory):
    """(connection, Dataset with every canonical in vocab) for RECIPES."""
    d = tmp_path_factory.mktemp("excl")
    raw = {k: {"title": t, "ingredients": ing, "instructions": "Mix.\nBake."} for k, (t, ing) in RECIPES.items()}
    (d / "x.json").write_text(json.dumps(raw), encoding="utf-8")
    build(d / "x.db", {"ar": d / "x.json"}, vocab_min=1)  # every name known: these tests are about tags
    con = connect(d / "x.db")
    ds = load_dataset(con)
    yield con, dataclasses.replace(ds, vocab=frozenset(c for c, in con.execute("SELECT canonical FROM vocab")))
    con.close()


def kept(eng, word: str = None, tag: str = None) -> set[str]:
    """Recipe keys that survive excluding an ingredient word or a tag."""
    con, ds = eng
    res = search(con, "", exclude=[stats.term(word, ds)] if word else [], exclude_tags=[tag] if tag else [], limit=50)
    return {h.id.split(":")[1] for h in res.hits}


def test_no_egg_keeps_eggplant(eng):
    assert "x1" in kept(eng, word="egg") and "x2" not in kept(eng, word="egg")
    assert "x1" in kept(eng, tag="egg") and "x2" not in kept(eng, tag="egg")


def test_no_salt_keeps_unsalted_butter(eng):
    assert "x3" in kept(eng, word="salt") and "x4" not in kept(eng, word="salt")


def test_no_cream_drops_cream(eng):
    assert "x6" not in kept(eng, word="cream")


def test_no_cream_keeps_cream_of_tartar(eng):  # was a known over-exclusion; fixed via mention_safe
    assert "x5" in kept(eng, word="cream")


def test_no_gluten_drops_every_wheat_pasta_option(eng):
    """'penne or bucatini' / 'cavatapi or penne' used to be only 'alt' (the other shape had no tag) and leaked."""
    con, _ = eng
    lenient = kept(eng, tag="gluten")
    assert not {"x7", "x10", "x11"} & lenient and {"x8", "x9"} <= lenient  # rice noodles fine, soba may_contain
    strict = {h.id.split(":")[1] for h in search(con, "", exclude_tags=["gluten"], strict_may_contain=True, limit=50).hits}
    assert "x9" not in strict and "x8" in strict
    level = dict(con.execute("SELECT recipe_id, level FROM recipe_tags WHERE tag = 'gluten'").fetchall())
    assert level["ar:x7"] == level["ar:x10"] == level["ar:x11"] == "contains" and level["ar:x9"] == "may_contain"
    assert con.execute("SELECT is_header FROM ingredient_lines WHERE recipe_id = 'ar:x11' AND line_no = 0").fetchone() == (1,)
