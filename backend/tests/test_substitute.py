"""T3 substitution (PRD 6.4) on a purpose-built fixture: evidence tiers, curated + data-discovered candidates,
"unknown is not safe" for candidates, cited-ID re-checks, the instruction validator, the final safety gate, and the
session flows of demos 7, 8 and 9. No LLM: adaptations use the deterministic fallback."""
import dataclasses
import json
import math

import pytest

from app import adapt, amounts, evidence, llm, substitute, subview, voice
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
    "bm1": ("Blueberry Muffins", ["2 cups all-purpose flour", "1 cup white sugar", "1 egg", "1 cup soy milk",
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
    "p7": ("Vegan Coconut Penne", ["8 ounces penne pasta", "1 cup coconut milk", "2 cloves garlic, minced",
                                   "1 tablespoon lemon juice"],
           "Cook the penne.\nSimmer the coconut milk with the garlic.\nToss with the pasta."),
    "bm0": ("Blueberry Muffins", ["1 (18.25 ounce) package yellow cake mix", "2 eggs", "1 cup blueberries",
                                  "1/2 cup vegetable oil"], BAKE),  # the cake mix may contain egg: the gate can't pass
    "pk1": ("Cornbread Squares", ["1 cup cornmeal", "1 tablespoon white sugar", "1 cup buttermilk",
                                  "2 tablespoons butter and maple syrup"],
            "Preheat oven to 400 degrees F.\nStir the cornmeal, sugar and buttermilk.\nBake for 20 minutes."),
    "cs1": ("Cauliflower Cream Sauce", ["1 head cauliflower", "2 cloves garlic, minced", "2 tablespoons olive oil"],
            "Boil the cauliflower.\nBlend with the garlic and olive oil."),  # cream sauces without cream: an L1 level
    "cs2": ("Potato Cream Sauce", ["2 potatoes", "2 cloves garlic, minced", "1/2 cup water"],
            "Boil the potatoes.\nBlend with the garlic and water."),
    "cs3": ("White Bean Cream Sauce", ["1 can white beans", "2 cloves garlic, minced", "1 tablespoon lemon juice"],
            "Blend everything until smooth."),
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
    assert (l1.n_with, l1.n_without, l1.support) == (3, 5, 3) and l1.lift is None  # n_with < 20: too few to compute
    assert next(c for c in part.candidates if c.name == "baking soda").strength != "Strong"  # a staple
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
    assert part.chosen.name == "coconut milk" and part.chosen.strength == "Strong"  # 2 of 5 + 'Vegan Coconut Penne'
    assert t.result.adaptation is not None and t.result.adaptation.gate == []


def test_meringue_egg_whites_is_weak_or_none_with_no_fake_adaptation(eng):
    res = run(eng, "m1", ["egg whites"], restrictions=["egg"])
    part = res.parts[0]
    assert part.strength in ("Weak", "None") and res.adaptation is None
    assert res.question and "meringue" in res.question.lower()  # defining ingredient: warn and ask
    # aquafaba is below the vocab threshold, but its tags are declared in candidates.yaml and 1 recipe uses it
    assert "aquafaba" in [c.name for c in part.candidates] and "aquafaba" not in [n for n, _ in part.rejected]


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


def test_lift_uses_raw_rates_and_says_when_there_are_too_few():
    assert evidence.lift(n_with=181, in_with=0, n_without=1411, support=3) == math.inf  # silken tofu, never with cream
    assert evidence.lift(n_with=178, in_with=10, n_without=13, support=2) is None  # support < 3
    assert evidence.lift(n_with=19, in_with=1, n_without=13, support=5) is None  # n_with < 20
    assert evidence.lift(n_with=100, in_with=10, n_without=50, support=10) == pytest.approx(2.0)
    assert evidence.fmt_lift(None) == "too few to compute" and evidence.fmt_lift(math.inf) == "∞"


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
    from app.planner import confident
    from app.rules import rule_plan
    assert rule_plan("show me the first one")["intent"] == "recipe_detail"
    assert not confident("yes", rule_plan("yes"))  # may answer another question: the LLM reads the history
    assert confident("adapt it anyway", rule_plan("adapt it anyway"))


def test_strength_rules():
    T = evidence.Tier
    l1 = lambda **k: {"L1": T(**k), "L2": T(), "L3": T()}
    assert evidence.strength(l1(n_with=178, in_with=137, n_without=13, support=5), ["ar:eggless"]) == "Weak"  # baking soda
    assert evidence.strength(l1(n_with=181, in_with=0, n_without=1411, support=4), ["ar:vegan"]) == "Strong"  # cashew
    assert evidence.strength(l1(n_with=10, in_with=1, n_without=5, support=2), ["ar:x"]) == "Strong"  # explicit + 2
    assert evidence.strength(l1(n_with=10, in_with=1, n_without=5, support=2), []) == "Weak"  # 2 alone isn't enough
    assert evidence.strength(l1(n_with=164, in_with=6, n_without=52, support=3), []) == "Strong"
    assert evidence.strength(l1(n_with=10, in_with=1, n_without=5, support=1), []) == "Weak"
    assert evidence.strength(l1(n_with=10, in_with=0, n_without=5, support=4), ["ar:x"], staple=True) != "Strong"
    t = {"L1": T(n_with=10, in_with=0, n_without=3, support=1), "L2": T(n_with=30, in_with=1, n_without=20, support=3),
         "L3": T()}
    assert evidence.strength(t, ["ar:vegan"]) == "Strong" and evidence.strength(t, []) == "Moderate"  # explicit + L2


def test_l1_is_the_most_specific_title_phrase(eng):
    ps = [" ".join(p) for p in evidence.phrases("Pasta with Tomato Cream Sauce")]
    assert ps == ["tomato cream sauce", "cream sauce", "pasta", "sauce"]
    assert evidence.phrases("Chicken Paella with Saffron Rice and Green Peas") == [["chicken", "paella"], ["paella"]]
    assert evidence.phrases("Classic Banana Bread II")[0] == ["banana", "bread"]
    res = run(eng, "p2", ["cream"])  # 'cream sauce' has 1 recipe, 'penne' 7: no phrase reaches 10, so the largest
    assert res.dish == ["penne"] and res.tiers["L1"] == 7 and res.l1_without == 5 and "'penne'" in "\n".join(subview.markdown(res))


def test_conflicting_candidate_is_never_chosen_over_a_clean_one(eng):
    T = evidence.Tier
    tiers = lambda n: {"L1": T(support=n), "L2": T(), "L3": T()}
    bad = substitute.Cand("a", "curated", tiers=tiers(5), strength="Strong", conflicting=True)
    ok = substitute.Cand("b", "curated", tiers=tiers(1), strength="Moderate")
    assert sorted([bad, ok], key=substitute.rank)[0] is ok
    garlic = substitute.Cand("garlic", "discovered", tiers=tiers(4), strength="Weak")  # quiche: co-occurs with no eggs
    flax = substitute.Cand("flaxseed", "curated", tiers=tiers(0), strength="Weak")
    assert sorted([garlic, flax], key=substitute.rank)[0] is flax
    res = run(eng, "bb1", ["eggs"], restrictions=["egg"])
    assert "Chosen because" in "\n".join(subview.summary(res))


def test_l1_widens_until_a_strong_or_moderate_candidate(eng, monkeypatch):
    monkeypatch.setattr(evidence, "MIN_L1", 4)  # 'cream sauce' (4 recipes, 3 without cream) and 'penne' qualify
    res = run(eng, "p2", ["cream"], restrictions=["dairy", "tree_nut"])
    assert res.dish == ["penne"] and "widened from 'cream sauce'" in res.widened
    assert res.parts[0].chosen.name == "coconut milk" and res.parts[0].chosen.strength == "Strong"
    assert "widened from 'cream sauce'" in "\n".join(subview.summary(res))


def test_role_coverage_ranks_before_support():
    T = evidence.Tier
    tiers = lambda n: {"L1": T(support=n), "L2": T(), "L3": T()}
    broad = substitute.Cand("silken tofu", "curated", roles=["binding", "structure"], tiers=tiers(0), strength="Weak")
    narrow = substitute.Cand("applesauce", "curated", roles=["moisture"], tiers=tiers(5), strength="Weak")
    assert sorted([narrow, broad], key=substitute.rank)[0] is broad


def test_weak_best_candidate_is_adapted_with_a_label(eng):
    res = run(eng, "bm1", ["eggs"], restrictions=["egg"])  # best verified candidate is Weak, no defining ingredient
    c = res.parts[0].chosen
    assert (c.name, c.kind, c.strength) == ("applesauce", "curated", "Weak") and res.adaptation is not None
    assert res.adaptation.caveat == "Weak evidence for applesauce: based on 1 recipe without eggs ('muffins' titles)."
    assert "Weak evidence" in "\n".join(subview.summary(res))


def test_target_prefers_a_recipe_the_gate_can_pass_but_respects_a_selection(eng):
    con, ds = eng
    s = Session(con, ds, use_llm=False)
    t = s.respond("Take this blueberry muffins recipe and remove eggs")
    assert t.result.rid == "ar:bm1" and "verified free of egg" in t.reply  # not bm0 with the cake mix
    s = Session(con, ds, use_llm=False)
    s.state.selected_recipe_id = "ar:bm0"
    assert s.respond("remove the eggs").result.rid == "ar:bm0"


def test_estimate_scales_with_the_removed_amount(eng):
    assert amounts.scale("1/4 cup per egg", ["3 eggs"]) == "3/4 cup"
    assert amounts.scale("1 tablespoon ground flaxseed + 3 tablespoons water per egg", ["2 eggs"]) == \
        "2 tablespoons ground flaxseed + 6 tablespoons water"
    assert amounts.scale("1/2 cup soaked cashews blended with 1/2 cup water per cup of cream", ["2 cups heavy cream"]) == \
        "1 cup soaked cashews blended with 1 cup water"
    assert amounts.scale("the same volume (full-fat)", ["1 cup heavy cream"]) == "1 cup"
    res = run(eng, "bb1", ["eggs"], replace_with="yogurt")  # 1 supporting recipe: no observed median
    assert any(d["text"] == "1/2 cup yogurt (estimate: 1/4 cup per egg; replaces 2 eggs)"
               for d in res.adaptation.ingredients)


def test_compound_line_keeps_its_other_item(eng):
    res = run(eng, "pk1", ["butter"], replace_with="vegetable oil")
    ops = [(d["op"], d["text"]) for d in res.adaptation.ingredients]
    assert ("remove", "2 tablespoons butter and maple syrup") in ops
    assert any(op == "add" and t.startswith("maple syrup") for op, t in ops)


def test_model_timeout_labels_the_predicted_block(eng, monkeypatch):
    def slow(*a, **k):
        raise llm.LLMError("timeout > 12 s", [])
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "generate_json", slow)
    con, ds = eng
    res = substitute.run(con, ds, "ar:bb1", ["eggs"], restrictions=["egg"], use_llm=True)
    assert res.adaptation.predicted is None and res.adaptation.predicted_status == "not generated (model timeout)"


def test_chat_bubble_is_a_summary(eng):
    res = run(eng, "bb1", ["eggs"], restrictions=["egg"])
    md = "\n".join(subview.summary(res))
    assert "applesauce" in md and "Strong" in md and "✓" in md and "panel" in md
    assert "Verified from dataset" not in md and "Adapted recipe" not in md and len(subview.summary(res)) <= 9


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


def test_dish_words_can_start_an_l1_phrase():
    assert evidence.phrases("Sugar Cookies")[0] == ["sugar", "cookies"]
    assert evidence.phrases("Egg Salad")[0] == ["egg", "salad"]
    assert evidence.phrases("Sugar Free Banana Bread")[0] == ["banana", "bread"]


def test_recipe_canon_and_size_are_exact(eng):
    con, _ = eng
    want = dict(con.execute("SELECT recipe_id, COUNT(DISTINCT canonical) FROM ingredient_lines WHERE is_alt = 0 AND "
                            "canonical IS NOT NULL GROUP BY recipe_id"))
    assert dict(con.execute("SELECT recipe_id, n FROM recipe_size")) == want
    assert con.execute("SELECT COUNT(*) FROM recipe_canon").fetchone()[0] == sum(want.values())
    assert evidence.sizes(con) == want  # L2's Jaccard set sizes


def test_a_question_for_recipes_is_not_a_substitution():
    from app.rules import rule_plan
    q = "which recipes in the dataset are egg-free banana breads that use applesauce instead of eggs?"
    assert rule_plan(q)["intent"] != "substitute"
    assert rule_plan("use applesauce instead of eggs")["intent"] == "substitute"  # an edit of the open recipe


def test_per_result_tag_lookup_uses_the_recipe_index(eng):
    con, _ = eng
    # ingest ends with ANALYZE; without ix_tags_recipe its stats turned this into a 30k-row scan per result
    plan = " ".join(r[3] for r in con.execute(
        "EXPLAIN QUERY PLAN SELECT t.level, l.raw FROM recipe_tags t JOIN ingredient_lines l ON l.recipe_id = "
        "t.recipe_id AND l.line_no = t.evidence_line_no WHERE t.recipe_id = ? AND t.tag = ? LIMIT 1", ("ar:p1", "dairy")))
    assert "ix_tags_recipe" in plan
