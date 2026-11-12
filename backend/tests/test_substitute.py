"""T3 substitution (PRD 6.4) on a purpose-built fixture: evidence tiers, curated + data-discovered candidates,
"unknown is not safe" for candidates, cited-ID re-checks, the instruction validator, the final safety gate, and the
session flows of demos 7, 8 and 9. No LLM: adaptations use the deterministic fallback."""
import dataclasses
import json

import pytest

from app import adapt, evidence, substitute, voice
from app.db import connect, load_dataset
from app.ingest import build
from app.session import Session

BAKE = "Preheat oven to 350 degrees F.\nMix the dry ingredients.\nStir in the wet ingredients.\nBake for 50 minutes."
R = {  # key: (title, ingredient lines, instructions)
    "bb1": ("Classic Banana Bread", ["2 cups all-purpose flour", "1 cup white sugar", "2 eggs", "3 ripe bananas, mashed",
                                     "1/2 cup butter, melted", "1 teaspoon baking soda"],
            "Preheat oven to 350 degrees F.\nMix the flour, sugar and baking soda.\nBeat in the eggs, bananas and "
            "butter.\nBake for 60 minutes."),
    "bb2": ("Moist Banana Bread", ["2 cups all-purpose flour", "1 cup white sugar", "2 large eggs", "3 bananas",
                                   "1/2 cup vegetable oil", "1 teaspoon baking soda"], BAKE),
    "bb3": ("Banana Bread", ["2 cups all-purpose flour", "1 cup white sugar", "1 egg", "2 bananas",
                             "1/2 cup butter", "1 teaspoon baking soda"], BAKE),
    "bb4": ("Eggless Banana Bread", ["2 cups all-purpose flour", "1 cup white sugar", "1/2 cup applesauce",
                                     "3 bananas", "1/2 cup vegetable oil", "1 teaspoon baking soda"],
            "Preheat oven to 350 degrees F.\nMix the applesauce with the mashed bananas.\nStir into the flour.\n"
            "Bake for 55 minutes."),
    "bb5": ("Vegan Banana Bread", ["2 cups all-purpose flour", "1 cup white sugar", "1/3 cup applesauce",
                                   "4 bananas", "1/3 cup vegetable oil", "1 teaspoon baking soda"], BAKE),
    "bb6": ("Egg-Free Banana Bread", ["2 cups all-purpose flour", "1 cup white sugar", "1/2 cup applesauce",
                                      "3 bananas", "1/2 cup butter", "1 teaspoon baking soda"], BAKE),
    "bb7": ("Banana Bread with Flax", ["2 cups all-purpose flour", "1 cup white sugar", "1 tablespoon flaxseed",
                                       "3 tablespoons water", "3 bananas", "1/2 cup vegetable oil",
                                       "1 teaspoon baking soda"], BAKE),
    "bb8": ("Banana Bread with Yogurt", ["2 cups all-purpose flour", "1 cup white sugar", "1/2 cup plain yogurt",
                                         "3 bananas", "1/2 cup butter", "1 teaspoon baking soda"], BAKE),
    "bm1": ("Blueberry Muffins", ["2 cups all-purpose flour", "1 cup white sugar", "1 egg", "1 cup milk",
                                  "1/2 cup vegetable oil", "1 cup blueberries", "2 teaspoons baking powder"], BAKE),
    "bm2": ("Vegan Blueberry Muffins", ["2 cups all-purpose flour", "1 cup white sugar", "1 tablespoon flaxseed",
                                        "1 cup soy milk", "1/2 cup vegetable oil", "1 cup blueberries",
                                        "2 teaspoons baking powder"], BAKE),
    "bm3": ("Applesauce Muffins", ["2 cups all-purpose flour", "1 cup white sugar", "1/2 cup applesauce",
                                   "1/2 cup soy milk", "2 teaspoons baking powder", "1 teaspoon cinnamon"], BAKE),
    "bm4": ("Yogurt Muffins", ["2 cups all-purpose flour", "1 cup white sugar", "1 cup plain yogurt", "1 egg",
                               "2 teaspoons baking powder", "1 teaspoon cinnamon"], BAKE),
    "p1": ("Creamy Penne", ["8 ounces penne pasta", "1 cup heavy cream", "1/2 cup grated parmesan cheese",
                            "2 cloves garlic, minced", "2 tablespoons butter"],
           "Cook the penne.\nMelt the butter and cook the garlic, then add the cream.\nToss with the pasta and "
           "parmesan."),
    "p2": ("Penne in Cream Sauce", ["8 ounces penne pasta", "1 cup heavy cream", "2 cloves garlic, minced",
                                    "2 tablespoons olive oil", "1 teaspoon salt"],
           "Cook the penne in salted water.\nCook the garlic in the olive oil, add the cream and simmer for 5 "
           "minutes.\nToss with the pasta."),
    "p3": ("Vegan Creamy Penne", ["8 ounces penne pasta", "1 cup raw cashews", "1/2 cup water",
                                  "2 cloves garlic, minced", "2 tablespoons olive oil"],
           "Cook the penne.\nBlend the cashews with the water until smooth.\nToss the pasta with the cashew sauce."),
    "p4": ("Dairy-Free Penne", ["8 ounces penne pasta", "1 cup cashews, soaked", "2 cloves garlic, minced",
                                "2 tablespoons olive oil", "1 tablespoon lemon juice"],
           "Cook the penne.\nBlend the cashews with the lemon juice.\nToss with the pasta."),
    "p5": ("Penne with Cashew Sauce", ["8 ounces penne pasta", "3/4 cup cashews", "2 cloves garlic, minced",
                                       "2 tablespoons olive oil", "1 teaspoon salt"],
           "Cook the penne.\nBlend the cashews.\nToss with the pasta."),
    "p6": ("Coconut Penne", ["8 ounces penne pasta", "1 cup coconut milk", "2 cloves garlic, minced",
                             "2 tablespoons olive oil", "1 teaspoon salt"],
           "Cook the penne.\nSimmer the garlic in the coconut milk.\nToss with the pasta."),
    "p7": ("Spicy Coconut Penne", ["8 ounces penne pasta", "1 cup coconut milk", "2 cloves garlic, minced",
                                   "1 tablespoon lemon juice"],
           "Cook the penne.\nSimmer the coconut milk with the garlic.\nToss with the pasta."),
    "m1": ("Meringue Cookies", ["4 egg whites", "1 cup white sugar", "1/4 teaspoon cream of tartar"],
           "Beat the egg whites with the cream of tartar until stiff.\nBeat in the sugar.\nBake at 200 degrees F "
           "for 2 hours."),
    "m2": ("Chocolate Meringues", ["3 egg whites", "1 cup white sugar", "2 tablespoons cocoa powder"],
           "Beat the egg whites until stiff.\nFold in the sugar and cocoa.\nBake at 200 degrees F for 2 hours."),
    "m3": ("Lemon Meringue Kisses", ["2 egg whites", "1 cup white sugar", "1/4 teaspoon cream of tartar"],
           "Beat the egg whites until stiff.\nBeat in the sugar.\nBake at 200 degrees F for 90 minutes."),
    "m4": ("Aquafaba Meringues", ["1/2 cup aquafaba", "1 cup white sugar", "1/4 teaspoon cream of tartar"],
           "Whip the aquafaba until stiff.\nBeat in the sugar.\nBake at 200 degrees F for 2 hours."),
}


@pytest.fixture(scope="module")
def eng(tmp_path_factory):
    d = tmp_path_factory.mktemp("subst")
    raw = {k: {"title": t, "ingredients": ing, "instructions": ins} for k, (t, ing, ins) in R.items()}
    (d / "s.json").write_text(json.dumps(raw), encoding="utf-8")
    build(d / "s.db", {"ar": d / "s.json"}, vocab_min=2)
    con = connect(d / "s.db")
    ds = load_dataset(con)
    yield con, dataclasses.replace(ds, vocab=frozenset(c for c, n in con.execute(
        "SELECT canonical, recipe_count FROM vocab") if n >= 2))
    con.close()


def run(eng, rid, removes, **kw):
    con, ds = eng
    return substitute.run(con, ds, f"ar:{rid}", removes, use_llm=False, **kw)


def test_egg_free_banana_bread_finds_evidence_and_a_verified_candidate(eng):
    res = run(eng, "bb1", ["eggs"], restrictions=["egg"])
    part = res.parts[0]
    assert [a[1] for a in part.affected] == ["2 eggs"] and part.roles == ["binding", "leavening", "moisture", "structure"]
    best = part.chosen
    assert best.name == "applesauce" and best.strength == "Strong"
    l1 = best.tiers["L1"]
    assert (l1.n_with, l1.n_without, l1.support) == (3, 5, 3) and l1.lift > 2
    assert {"ar:bb4", "ar:bb5", "ar:bb6"} == set(best.explicit)  # eggless / vegan / egg-free titles
    assert any(rid == "ar:bb4" and "applesauce" in text.lower() for rid, text in best.snippets)
    assert res.adaptation is not None and res.adaptation.gate == []  # egg-free: nothing left that contains egg
    ops = [(c["op"], c["text"]) for c in res.adaptation.ingredients]
    assert ("remove", "2 eggs") in ops and any(op == "add" and "applesauce" in t for op, t in ops)
    step = next(s for s in res.adaptation.steps if s["n"] == 3)
    assert "egg" not in step["text"].lower() and "applesauce" in step["text"] and step["changed"]


def test_cream_pasta_no_dairy_then_tree_nut_regrades(eng):
    con, ds = eng
    s = Session(con, ds, use_llm=False)
    s.state.selected_recipe_id = "ar:p2"
    t = s.respond("Replace cream in this pasta recipe without dairy")
    part = t.result.parts[0]
    assert part.chosen.name == "cashew" and part.chosen.strength == "Strong" and "dairy" in s.state.exclude_tags
    assert any(name == "half and half" and "dairy" in why for name, why in part.rejected)
    t = s.respond("I'm also allergic to tree nuts")
    part = t.result.parts[0]
    assert any(name == "cashew" and "tree_nut" in why for name, why in part.rejected)
    assert part.chosen.name == "coconut milk" and part.chosen.strength == "Weak" and part.conflicting
    assert t.result.adaptation is None  # Weak: no adaptation unless asked for anyway
    assert "Strong" not in t.reply.split("Rejected")[0] or "cashew" not in t.reply.split("Rejected")[0]


def test_meringue_egg_whites_is_weak_or_none_with_no_fake_adaptation(eng):
    res = run(eng, "m1", ["egg whites"], restrictions=["egg"])
    part = res.parts[0]
    assert part.strength in ("Weak", "None") and res.adaptation is None
    assert res.question and "meringue" in res.question.lower()  # defining ingredient: warn and ask
    assert any(name == "aquafaba" and "couldn't verify" in why for name, why in part.rejected)


def test_removing_an_absent_ingredient_says_not_in_this_recipe(eng):
    res = run(eng, "bb4", ["eggs"])
    assert res.parts == [] and "isn't in this recipe" in res.notes[0] and res.adaptation is None


def test_unverified_candidate_is_rejected(eng):
    res = run(eng, "bb1", ["butter"], replace_with="zorble paste")
    assert any(name == "zorble paste" and "couldn't verify" in why for name, why in res.parts[0].rejected)


def test_cited_id_failing_the_recheck_is_dropped(eng):
    con, ds = eng
    spec = substitute.spec_for("eggs", ds)
    assert evidence.cited(con, ["ar:bb4"], spec, "applesauce") == ["ar:bb4"]
    assert evidence.cited(con, ["ar:bb1"], spec, "applesauce") == []  # has eggs, no applesauce
    assert evidence.cited(con, ["ar:bb4", "ar:bb1", "ar:nope"], spec, "applesauce") == ["ar:bb4"]


ORIG = ["Mix the flour and sugar.", "Beat in the eggs and the butter.", "Bake for 50 minutes."]


def test_instruction_validator(eng):
    _, ds = eng
    rx = adapt.removed_rx(["egg"])
    ok = [{"n": 1, "text": ORIG[0], "changed": False, "reason": ""},
          {"n": 2, "text": "Beat in the applesauce and the butter.", "changed": True, "reason": "egg -> applesauce"},
          {"n": 3, "text": ORIG[2], "changed": False, "reason": ""}]
    assert adapt.validate_steps(ORIG, ok, rx, ["applesauce"], {"applesauce"}, ds.vocab)
    unmarked = [dict(ok[0], text="Whisk the flour and sugar."), ok[1], ok[2]]
    with pytest.raises(ValueError, match="not marked"):
        adapt.validate_steps(ORIG, unmarked, rx, ["applesauce"], {"applesauce"}, ds.vocab)
    leftover = [ok[0], dict(ok[1], text="Beat in the applesauce and one egg."), ok[2]]
    with pytest.raises(ValueError, match="still mentions"):
        adapt.validate_steps(ORIG, leftover, rx, ["applesauce"], {"applesauce"}, ds.vocab)
    new_ing = [ok[0], dict(ok[1], text="Beat in the applesauce, the butter and some cinnamon."), ok[2]]
    with pytest.raises(ValueError, match="new ingredient"):
        adapt.validate_steps(ORIG, new_ing, rx, ["applesauce"], {"applesauce"}, ds.vocab)


def test_final_safety_gate_blocks_an_allergen(eng):
    _, ds = eng
    fails = adapt.final_gate(["8 ounces penne pasta", "2 cloves garlic, minced"], ["almond milk"], ["tree_nut"], ds.vocab)
    assert fails and fails[0][0] == "almond milk" and "tree_nut" in fails[0][1]
    fails = adapt.final_gate(["1/2 cup grated parmesan cheese"], ["coconut milk"], ["dairy"], ds.vocab)
    assert fails == [("1/2 cup grated parmesan cheese", "contains dairy")]
    assert adapt.final_gate(["2 cloves garlic, minced"], ["coconut milk"], ["dairy"], ds.vocab) == []


def test_lift_never_divides_by_zero():
    assert evidence.lift(n_with=0, in_with=0, n_without=5, support=3) == pytest.approx((4 / 7) / (1 / 2))
    assert evidence.lift(0, 0, 0, 0) == pytest.approx(1.0)
    assert evidence.lift(n_with=339, in_with=0, n_without=11, support=0) == 1.0  # nothing observed: no fake 13x


def test_voice_validator_rejects_an_invented_count():
    facts = {"candidate": "applesauce", "tier": "L1", "support": 3, "n_without": 5, "n_with": 3}
    assert voice.check("3 of 5 egg-free banana breads use applesauce.", facts)
    with pytest.raises(ValueError):
        voice.check("18 of 41 egg-free banana breads use applesauce.", facts)


def test_session_resolves_the_dish_states_the_pick_and_switches_option(eng):
    con, ds = eng
    s = Session(con, ds, use_llm=False)
    t = s.respond("Take this banana bread recipe and remove eggs. Use only ingredients that appear in the dataset.")
    assert t.result.rid in ("ar:bb1", "ar:bb2", "ar:bb3") and "I picked" in t.reply and t.result.rid in t.reply
    first = t.result.parts[0].chosen.name
    t = s.respond("use the second option instead")
    assert t.result.parts[0].chosen.name != first and s.state.sub["option"] == 2
    t = s.respond("replace butter with vegetable oil")
    assert t.result.parts[0].item == "butter" and t.result.parts[0].chosen.name == "vegetable oil"
    assert t.result.parts[0].chosen.kind == "user"


def test_detail_and_bare_yes_are_not_forced_into_a_substitution():
    from app.rules import confident, rule_plan
    assert rule_plan("show me the first one")["intent"] == "recipe_detail"
    assert not confident("yes", rule_plan("yes"))  # may answer another question: the LLM reads the history
    assert confident("adapt it anyway", rule_plan("adapt it anyway"))


def test_explicit_variant_of_a_dish_staple_is_not_strong():
    T = evidence.Tier
    staple = {"L1": T(n_with=178, in_with=137, n_without=13, support=5, lift=0.5), "L2": T(), "L3": T()}
    assert evidence.strength(staple, ["ar:eggless"]) == "Weak"  # baking soda in an eggless banana bread
    rare = {"L1": T(n_with=181, in_with=0, n_without=1411, support=4, lift=0.6), "L2": T(), "L3": T()}
    assert evidence.strength(rare, ["ar:vegan"]) == "Strong"  # cashew in a vegan pasta, never with cream


def test_substitution_phrasings_from_the_exploratory_pass():
    from app.rules import rule_plan
    p = rule_plan("no eggs in this pls")
    assert p["substitution"]["remove"] == ["eggs"] and not p["substitution"]["dish"] and not p["state_patch"]["exclude_add"]
    assert rule_plan("the second option")["substitution"]["option"] == 2
    s = rule_plan("substitue the eggs in this quiche")["substitution"]
    assert (s["remove"], s["dish"]) == (["eggs"], "quiche")
    assert rule_plan("isme ande nahi chahiye")["substitution"]["remove"] == ["eggs"]
    s = rule_plan("replace butter with oil")["substitution"]
    assert (s["remove"], s["replace_with"]) == (["butter"], "oil")
    assert rule_plan("make it vegan")["substitution"]["remove_tags"]
    assert rule_plan("find a pasta recipe without dairy")["intent"] == "search"
