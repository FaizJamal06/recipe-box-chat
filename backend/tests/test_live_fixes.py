"""M6 part 2: regression tests for the bugs found in live testing (A0.1-A0.5) and the step-limit chip."""
import pytest

from app import adapt, omit, search
from app.db import connect, load_dataset
from app.evidence import Spec
from app.rules import dish_filters, only, removed, rule_plan
from app.session import Session
from app.substitute import Cand


@pytest.fixture(scope="module")
def eng(mini):
    con = connect(mini[0])
    yield con, load_dataset(con)
    con.close()


def patch(text: str) -> dict:
    return rule_plan(text.lower()).get("state_patch", {})


def test_removal_phrasings_drop_presets_and_tags():
    assert removed("actually i'm not vegan anymore, just no peanuts") == ["vegan"]
    assert removed("i can eat dairy now") == ["dairy"] and removed("i'm no longer vegetarian") == ["vegetarian"]
    assert removed("drop vegan") == ["vegan"] and removed("remove the dairy restriction") == ["dairy"]
    p = patch("Actually I'm not vegan anymore, just no peanuts")
    assert p["diets_remove"] == ["vegan"] and p["exclude_tags_add"] == ["peanut"] and p["only"]
    assert not p["diets_add"] and not p.get("query_text")  # vegan is never re-added; no junk dish
    assert only("just no peanuts") and only("only no gluten") and not only("no peanuts")


def test_diet_words_in_a_dish_are_filters():
    assert dish_filters("vegetarian biryani") == ("biryani", ["vegetarian"], [])
    assert dish_filters("veg biryani") == ("biryani", ["vegetarian"], [])
    assert dish_filters("eggless banana bread") == ("banana bread", [], ["eggs"])
    assert dish_filters("dairy-free pasta") == ("pasta", [], ["dairy"])
    assert dish_filters("mixed veg curry")[0] == "mixed veg curry"  # 'veg' mid-dish is a word, not the preset
    assert dish_filters("veggie stock")[1] == []


def test_filter_words_are_not_substitutions_or_dishes():
    for text in ("remove the step limit", "drop vegan", "remove the dairy restriction"):
        assert rule_plan(text)["intent"] == "search", text
    assert patch("remove the step limit")["max_steps"] == -1 and not patch("remove the step limit").get("query_text")
    assert rule_plan("restore previous filters")["intent"] == "restore"
    assert rule_plan("remove the eggs")["intent"] == "substitute"


def test_not_vegan_anymore_keeps_the_dish(eng):
    s = Session(*eng, use_llm=False)
    s.respond("Find a vegan curry recipe")
    t = s.respond("Actually I'm not vegan anymore, just no peanuts")
    assert s.state.diets == [] and s.state.exclude_tags == ["peanut"] and s.state.query_text == "curry"
    assert any("now: no peanuts (replacing vegan)" in n for n in t.notes)


def test_non_food_leftovers_ask_instead_of_guessing(eng):
    s = Session(*eng, use_llm=False)
    s.respond("Find a rice recipe")
    t = s.respond("hmm, not sure, maybe later")
    assert t.plan["intent"] == "clarify" and s.state.query_text == "rice"
    assert not search.has_food(eng[0], eng[1], "actually not anymore") and search.has_food(eng[0], eng[1], "rice")


def test_task_switch_clears_request_filters_and_restore_brings_them_back(eng):
    s = Session(*eng, use_llm=False)
    s.respond("Find a rice recipe")
    s.respond("at most 5 steps")
    s.respond("I cannot have dairy")
    t = s.respond("Find a curry recipe")
    assert s.state.max_steps is None and s.state.exclude_tags == ["dairy"]
    assert any("cleared at most 5 steps" in n for n in t.notes) and any("no dairy" in n for n in t.notes)
    s.respond("restore previous filters")
    assert s.state.max_steps == 5 and s.state.query_text == "curry"
    s.respond("I have rice and onions")
    assert s.state.max_steps is None and s.state.have == ["rice", "onions"]


def test_kept_note_names_presets_not_tags(eng):
    s = Session(*eng, use_llm=False)
    s.respond("Find a vegan curry recipe")
    s.respond("I'm allergic to peanuts")
    t = s.respond("Find a rice recipe")
    note = next(n for n in t.notes if n.startswith("Kept"))
    assert "(vegan, no peanuts)" in note and "honey" not in note


def test_make_it_vegetarian_after_a_search_drops_the_meat_word(eng):
    s = Session(*eng, use_llm=False)
    s.respond("Find a chicken pot pie recipe")
    t = s.respond("make it vegetarian")
    assert s.state.query_text == "pot pie" and "meat" in s.state.exclude_tags
    assert any("Dropped 'chicken'" in n for n in t.notes)


def test_relaxations_keep_the_head_dish():
    assert list(search.relaxations("spicy coconut biryani")) == [
        ("coconut biryani", "dropped 'spicy'"), ("biryani", "dropped 'spicy', 'coconut'")]
    assert next(search.relaxations("aubergine curry"))[0] == "eggplant curry"


def test_omit_grade_and_step_strip():
    fam = {"L1": set(range(18)), "L2": set(range(47)), "L3": set(range(100))}
    c = omit.grade(Cand(omit.NAME, "omit"), fam, withs=set(range(8, 47)))
    assert c.strength == "Strong" and c.tiers["L1"].n_without == 8 and omit.summary(c, "salt", "broiled chicken") == \
        "8 of 18 'broiled chicken' recipes have no salt"
    assert omit.grade(Cand(omit.NAME, "omit"), fam, withs=set(range(1, 100))).strength == "Weak"
    rx = adapt.removed_rx(["salt"])
    assert omit.strip("Season chicken with salt and pepper.", rx, "salt") == "Season chicken with pepper."
    assert omit.strip("Spread onions. Season with salt. Bake.", rx, "salt") == "Spread onions. Bake."
    assert omit.strip("Sprinkle with salt.", rx, "salt") == "(Skip: this step only added salt.)"
    assert omit.optional(Spec("salt", canonical="salt", family="salt"), [(0, "salt as needed")])
    assert omit.optional(Spec("cheese", canonical="cheddar", family="cheese"), [(0, "cheddar, for garnish")])
    assert not omit.optional(Spec("eggs", tag="egg"), [(0, "2 eggs")])
