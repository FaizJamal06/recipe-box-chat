"""Safety regressions: unknown is not safe (unverified table, lenient warnings, strict exclusion, "or" options must
be verified themselves), the new soy / sesame / honey / gelatin / alcohol / root_veg tags, and every diet preset."""
import dataclasses
import json

import pytest

from app import normalize as nz
from app import safety
from app.db import connect, load_dataset
from app.ingest import build
from app.rules import DIETS, rule_plan
from app.search import search
from app.session import Session

# vocab_min=2: a canonical is "known" when two valid recipes use it; 'zorble...' names appear once (unknown)
RECIPES = {
    "a1": ("Mystery Cake", ["2 cups flour", "1 cup sugar", "1 cup zorbleberry jam"]),
    "a2": ("Plain Cake", ["2 cups flour", "1 cup sugar"]),
    "a3": ("Pasta Choice", ["8 ounces penne or zorblenoodles", "1 cup sugar"]),
    "a4": ("Free Cream", ["1 cup dairy-free zorblecream", "1 cup sugar"]),
    "a5": ("Penne Bowl", ["8 ounces penne", "1 cup sugar"]),
    "a6": ("Rice Noodles", ["8 ounces brand x rice noodles", "1 cup sugar"]),
}


@pytest.fixture(scope="module")
def eng(tmp_path_factory):
    d = tmp_path_factory.mktemp("safety")
    raw = {k: {"title": t, "ingredients": ing, "instructions": "Mix.\nBake."} for k, (t, ing) in RECIPES.items()}
    (d / "x.json").write_text(json.dumps(raw), encoding="utf-8")
    build(d / "x.db", {"ar": d / "x.json"}, vocab_min=2)
    con = connect(d / "x.db")
    yield con, load_dataset(con)
    con.close()


def unv(con, rid: str) -> set[str]:
    return {t for t, in con.execute("SELECT tag FROM unverified WHERE recipe_id = ?", (f"ar:{rid}",))}


def kept(con, tag: str, strict: bool) -> set[str]:
    return {h.id[3:] for h in search(con, "", exclude_tags=[tag], strict_may_contain=strict, limit=50).hits}


def test_unknown_ingredient_is_unverified_for_every_tag_it_could_hide(eng):
    con, _ = eng
    assert unv(con, "a2") == set()  # flour + sugar both known
    assert {"dairy", "egg", "soy", "peanut"} <= unv(con, "a1")  # 'zorbleberry jam' could be anything
    assert "dairy" not in unv(con, "a4") and "soy" in unv(con, "a4")  # 'dairy-free' clears dairy only
    assert "gluten" not in unv(con, "a6")  # 'rice noodles' (an except phrase of gluten) clears gluten


def test_or_alternative_must_itself_be_verified(eng):
    con, _ = eng
    # penne contains gluten, the alternative is unknown: no verified gluten-free option -> unverified, not 'alt'
    assert "gluten" in unv(con, "a3") and "dairy" not in unv(con, "a3")  # penne is a known dairy-free option
    assert "a3" in kept(con, "gluten", strict=False) and "a3" not in kept(con, "gluten", strict=True)


def test_lenient_warns_strict_excludes(eng):
    con, _ = eng
    lenient, strict = kept(con, "dairy", False), kept(con, "dairy", True)
    assert {"a1", "a2"} <= lenient and "a1" not in strict and "a2" in strict and "a4" in strict
    hit = next(h for h in search(con, "", exclude_tags=["dairy"], limit=50).hits if h.id == "ar:a1")
    assert any("1 ingredient couldn't be verified: '1 cup zorbleberry jam'" in e for e in hit.evidence)
    assert safety.warnings(con, "ar:a1", ["dairy"]) == ["no dairy: 1 ingredient couldn't be verified: "
                                                        "'1 cup zorbleberry jam'"]


def test_strict_tag_stats_count_unverified_as_not_free(eng):
    from app import stats
    con, ds = eng
    lenient, strict = stats.tag_count(con, ds, ["dairy"], "free")
    # no recipe contains dairy; a1 ('zorbleberry jam') and a6 ('brand x rice noodles') can't be verified for it
    assert (lenient.value, strict.value) == (6, 4) and "unverified" in strict.normalization_note


def test_new_tags():
    has = lambda w, t: dict(nz.tags_for(w)).get(t)
    assert has("tofu", "soy") == has("tamari", "soy") == "contains"
    assert has("tahini", "sesame") == has("toasted sesame oil", "sesame") == "contains"
    assert has("honey", "honey") == "contains" and has("honeydew melon", "honey") is None
    assert has("unflavored gelatin", "gelatin") == "contains" and has("agar agar", "gelatin") is None
    assert has("gelatin", "meat") is None and has("gelatin", "pork") == "may_contain"  # halal: often porcine
    assert has("dry white wine", "alcohol") == has("mirin", "alcohol") == "contains"
    for w in ("red wine vinegar", "apple cider", "ginger ale", "non-alcoholic beer"):
        assert has(w, "alcohol") is None, w
    assert has("vanilla extract", "alcohol") == "may_contain"
    assert has("yellow onion", "root_veg") == has("fresh ginger", "root_veg") == has("sweet potato", "root_veg")
    assert has("ginger ale", "root_veg") is None


EXPECT = {"vegetarian": {"meat", "fish", "shellfish", "gelatin"},
          "vegan": {"meat", "fish", "shellfish", "gelatin", "dairy", "egg", "honey"},
          "pescatarian": {"meat", "gelatin"}, "halal": {"pork", "alcohol"},
          "jain": {"meat", "fish", "shellfish", "egg", "gelatin", "root_veg"}, "kosher": set(),
          "lactose intolerant": {"dairy"}, "celiac / wheat": {"gluten"}, "nut allergy": {"peanut", "tree_nut"}}
SAY = {"vegetarian": "I'm vegetarian", "vegan": "I am vegan", "pescatarian": "pescatarian please",
       "halal": "halal only", "jain": "I eat jain food", "kosher": "kosher please",
       "lactose intolerant": "I'm lactose intolerant", "celiac / wheat": "I'm allergic to wheat",
       "nut allergy": "I have a nut allergy"}


@pytest.mark.parametrize("name", list(EXPECT))
def test_every_preset_expands_to_its_tags(name):
    assert set(DIETS[name]["tags"]) == EXPECT[name]
    sp = rule_plan(SAY[name])["state_patch"]
    assert sp["diets_add"] == [name] and set(sp["exclude_tags_add"]) == EXPECT[name]


def test_single_allergens_and_kosher_salt():
    for text, tags in (("no shellfish", ["shellfish"]), ("no fish", ["fish"]), ("celiac", ["gluten"]),
                       ("no soy please", ["soy"]), ("no sesame", ["sesame"]), ("allergic to nuts", ["peanut", "tree_nut"])):
        assert rule_plan(text)["state_patch"]["exclude_tags_add"] == tags, text
    assert rule_plan("1 tsp kosher salt").get("state_patch", {}).get("diets_add", []) == []


def test_session_shows_expansion_chip_and_notes(eng):
    con, ds = eng
    ds = dataclasses.replace(ds, vocab=frozenset(c for c, in con.execute("SELECT canonical FROM vocab")))
    s = Session(con, ds, use_llm=False)
    t = s.respond("find a cake recipe, I am vegan")
    assert s.state.diets == ["vegan"] and set(EXPECT["vegan"]) <= set(s.state.exclude_tags)
    assert "Vegan → no meat, fish, shellfish, gelatin, dairy, eggs, honey." in t.reply
    t = s.respond("halal too")
    assert "slaughter method" in t.reply and {"pork", "alcohol"} <= set(s.state.exclude_tags)
    t = s.respond("dairy is fine now")
    assert s.state.diets == ["halal"] and "dairy" not in s.state.exclude_tags  # the vegan chip ends with it
    t = s.respond("kosher please")
    assert "can't be verified from recipe text" in t.reply and "kosher" not in s.state.diets
    t = s.respond("I eat jain food")
    assert "jain" in s.state.diets and "Many Jains also avoid honey" in t.reply and "root_veg" in s.state.exclude_tags


def test_api_diet_chip_removal(eng, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app import api
    con, _ = eng
    db = con.execute("PRAGMA database_list").fetchone()[2]
    monkeypatch.setattr(api, "DB", type(api.DB)(db))
    monkeypatch.setattr(api, "SESSIONS", {})
    with TestClient(api.app) as c:
        r = c.post("/api/chat", json={"message": "find a cake recipe, I am vegan and halal"}).json()
        assert [d["name"] for d in r["state"]["diets"]] == ["vegan", "halal"]
        r = c.patch(f"/api/session/{r['session_id']}/state", json={"op": "remove", "field": "diets", "value": "vegan"})
        st = r.json()["state"]
        assert [d["name"] for d in st["diets"]] == ["halal"] and set(st["exclude_tags"]) == {"pork", "alcohol"}
