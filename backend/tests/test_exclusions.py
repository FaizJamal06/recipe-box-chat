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
}


@pytest.fixture(scope="module")
def eng(tmp_path_factory):
    """(connection, Dataset with every canonical in vocab) for RECIPES."""
    d = tmp_path_factory.mktemp("excl")
    raw = {k: {"title": t, "ingredients": ing, "instructions": "Mix.\nBake."} for k, (t, ing) in RECIPES.items()}
    (d / "x.json").write_text(json.dumps(raw), encoding="utf-8")
    build(d / "x.db", {"ar": d / "x.json"})
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


@pytest.mark.xfail(strict=True, reason="known over-exclusion: the ingredient-text safety net (FTS word 'cream') "
                                       "also matches 'cream of tartar'; see docs/lexicon_todo.md")
def test_no_cream_keeps_cream_of_tartar(eng):
    assert "x5" in kept(eng, word="cream")
