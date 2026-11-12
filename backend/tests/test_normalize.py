"""normalize.py: the tricky cases of PRD 4.5 (qty, units, headers, compounds, identity, tags) and 4.4 sentences."""
import pytest

from app import normalize as nz
from app.ingest import count_sentences
from app.normalize import BROAD, family_for, line_tags, normalize, parse_line, tags_for


def canon(raw: str, vocab=None) -> list[str]:
    """Canonicals of the required items on one line."""
    return [p.name.canonical for p in parse_line(raw, vocab)]


@pytest.mark.parametrize("raw, qty, rng, unit, family", [
    ("1 1/2 cups milk", 1.5, None, "cup", "volume"),
    ("½ cup sugar", 0.5, None, "cup", "volume"),
    ("1½ cups milk", 1.5, None, "cup", "volume"),
    ("1.5 cups water", 1.5, None, "cup", "volume"),
    ("2-3 cloves garlic, minced", 2.5, (2, 3), "clove", "count"),
    ("3 1/2 to 4 1/2 cups chicken stock", 4.0, (3.5, 4.5), "cup", "volume"),
    ("1 (15 ounce) can black beans, rinsed and drained", 15, None, "ounce", "mass"),
    ("2 15-ounce cans black beans", 30, None, "ounce", "mass"),
    ("1 can cream of mushroom soup", 1, None, "can", "container"),
    ("1 pinch of salt", 1, None, "pinch", "volume"),
    ("1 tsp. vanilla extract", 1, None, "teaspoon", "volume"),
    ("2 eggs", 2, None, None, None),
])
def test_qty_unit(raw, qty, rng, unit, family):
    p = parse_line(raw)[0]
    assert (p.qty, p.qty_range, p.unit, p.unit_family) == (pytest.approx(qty), rng, unit, family)


def test_advertisement_and_headers():
    assert canon("1 cup white sugarADVERTISEMENT") == ["sugar"]
    assert parse_line("ADVERTISEMENT") == []
    assert parse_line("For the sauce:")[0].is_header
    assert parse_line("For the topping")[0].is_header
    assert not parse_line("Grilled bread (optional)")[0].is_header


@pytest.mark.parametrize("raw, expected", [
    ("Salt and pepper to taste", ["salt", "black pepper"]),
    ("salt and freshly ground black pepper", ["salt", "black pepper"]),
    ("Kosher salt & pepper", ["salt", "black pepper"]),
    ("1 cup half and half", ["half and half"]),
    ("1 cup half-and-half", ["half and half"]),
    ("1 box macaroni and cheese", ["macaroni and cheese"]),
    ("1/2 cup sweet and sour sauce", ["sweet and sour sauce"]),
    ("1 can cream of mushroom soup", ["cream of mushroom soup"]),
    ("1 onion, peeled and chopped", ["onion"]),
])
def test_compound_lines(raw, expected):
    assert canon(raw) == expected


def test_alternatives():
    p, = parse_line("2 tablespoons butter or margarine")
    assert p.name.canonical == "butter" and [a.canonical for a in p.alternatives] == ["margarine"]
    p, = parse_line("3 1/2 cups chicken stock or low-salt chicken broth, divided")
    assert [o.canonical for o in p.options] == ["chicken broth", "chicken broth"]
    assert [o.canonical for o in parse_line("1 cup peanut oil/vegetable oil")[0].options] == ["peanut oil", "vegetable oil"]


@pytest.mark.parametrize("raw, expected", [
    ("4 scallions, thinly sliced", "green onion"),
    ("2 spring onions", "green onion"),
    ("1 cup garbanzo beans", "chickpea"),
    ("1/2 cup chopped fresh coriander leaves", "cilantro"),
    ("2 boneless, skinless chicken breast halves", "chicken breast"),
    ("1 large onion, diced", "onion"),
    ("1 lb lean ground beef", "ground beef"),
    ("1 teaspoon ground cinnamon", "cinnamon"),
    ("1 cup all-purpose flour", "flour"),
    ("1/4 cup extra-virgin olive oil", "olive oil"),
])
def test_synonyms_and_descriptors(raw, expected):
    assert canon(raw) == [expected]


def test_identity_forms_stay_distinct():
    lines = ["2 tomatoes", "1 tablespoon tomato paste", "1 cup tomato sauce", "1/4 cup sun-dried tomatoes",
             "3 cloves garlic", "1 teaspoon garlic powder", "1 cup rice", "2 tablespoons rice vinegar",
             "1/2 cup rice flour", "2 eggs", "8 ounces egg noodles", "1 onion", "2 green onions",
             "1 teaspoon onion powder"]
    got = [canon(x)[0] for x in lines]
    assert got == ["tomato", "tomato paste", "tomato sauce", "sun-dried tomato", "garlic", "garlic powder", "rice",
                   "rice vinegar", "rice flour", "egg", "egg noodle", "onion", "green onion", "onion powder"]
    assert [parse_line(x)[0].name.family for x in ["1 red onion", "2 green onions", "1 cup cherry tomatoes"]] \
        == ["onion", "green onion", "tomato"]


def test_vocab_fallback_never_adds_a_tag_or_lands_on_a_deceptive_head():
    p, = parse_line("2 pounds heritage pork loin", vocab={"pork loin"})
    assert p.name.canonical == "pork loin" and dict(p.name.tags)["pork"] == "contains"
    for raw, head in [("1 cup cashew butter", "butter"), ("1 cup vegan cheese", "cheese"),
                      ("1 cup apple butter", "butter"), ("1 cup oat milk", "milk"),
                      ("2 tablespoons teriyaki marinade sauce", "sauce"), ("1 tsp ancho powder", "powder")]:
        assert canon(raw, vocab={head}) == [raw.split(maxsplit=2)[2]]


def test_line_tags_scan_whole_line():
    assert ("dairy", "contains") in line_tags("salt, pepper and butter")
    assert "dairy" not in dict(line_tags("1 cup dairy-free chocolate chips"))
    assert "dairy" not in dict(line_tags("1/2 cup coconut milk, or non-dairy creamer"))
    assert ("dairy", "contains") in line_tags("1 cup vegetable oil (or melted butter)")
    assert "meat" not in dict(line_tags("4 ribs celery, chopped")) | dict(line_tags("1 cup celery (about 2 ribs)"))
    assert dict(line_tags("1 tablespoon butter, for the baking dish")) == {"dairy": "contains"}


@pytest.mark.parametrize("raw, tag", [  # false positives seen in the M1 fixes rebuild
    ("1/2 cup butter flavored shortening", "dairy"),
    ("1/3 cup prepared white cream-style horseradish", "dairy"),
    ("A few ribs celery and leafy tops, chopped", "meat"),
    ("3 pounds kale, stems and ribs removed, coarsely chopped", "meat"),
    ("12 large Tuscan kale leaves, rinsed, center ribs removed", "meat"),
    ("1/2 cup grated cheese, such as Parmesan, goat's cheese", "meat"),
    ("3/4 ounce Grey Goose Orange", "meat"),
    ("3/4 ounce Grey Goose Orange", "poultry"),
    ("3 cups bottled spaghetti sauce (use your favorite brand)", "gluten"),
    ("2 bottles, 12 ounces each, ginger beer or all-natural ginger soda", "gluten"),
    ("A heavy-duty rimmed baking sheet, a.k.a. half sheet pan or jelly roll pan", "gluten"),
])
def test_tag_false_positives(raw, tag):
    assert tag not in dict(line_tags(raw))
    assert all(tag not in dict(o.tags) for p in parse_line(raw) for o in p.options)


def test_false_positive_fixes_keep_real_tags():
    assert dict(line_tags("1/2 cup grated cheese, such as Parmesan, goat's cheese"))["dairy"] == "contains"
    assert dict(line_tags("4 beef short ribs"))["meat"] == "contains"
    assert dict(line_tags("1 pound spaghetti"))["gluten"] == "contains"


@pytest.mark.parametrize("raw", ["1 9-inch skillet", "Toothpicks", "Parchment paper", "1 (9x13 inch) baking pan",
                                 "Kitchen string", "Optional, for serving",
                                 "Special equipment: a 9-inch tart pan with removable bottom"])
def test_equipment_and_notes_are_not_food(raw):
    p, = parse_line(raw)
    assert p.not_food and p.name is None and line_tags(raw) == ()


def test_food_next_to_equipment_words_survives():
    assert canon("2 sheets puff pastry") == ["puff pastry"]
    assert canon("1 cup butter, plus more for the pan") == ["butter"]
    assert canon("8 ounces pan-fried noodles") == ["pan-fried noodle"]
    assert not parse_line("Assorted crackers, for serving")[0].not_food


V = {"salt", "black pepper", "paprika", "onion", "garlic", "egg", "water"}


def test_comma_lists_split_only_when_every_part_is_known():
    assert canon("1 teaspoon salt, pepper and paprika", V) == ["salt", "black pepper", "paprika"]
    assert canon("salt, pepper, and paprika", V) == ["salt", "black pepper", "paprika"]
    assert canon("1 teaspoon salt, pepper and paprika") == ["salt"]  # no vocab: first-part rule
    assert canon("1 onion, peeled and chopped", V) == ["onion"]
    assert canon("1 onion, finely chopped", V) == ["onion"]


def test_only_first_item_keeps_the_amount():
    assert [(p.qty, p.unit) for p in parse_line("1 teaspoon salt, pepper and paprika", V)] \
        == [(1, "teaspoon"), (None, None), (None, None)]
    assert [(p.qty, p.unit) for p in parse_line("2 teaspoons salt and pepper")] == [(2, "teaspoon"), (None, None)]


def test_singular_everywhere():
    assert normalize("peanuts") == normalize("1 cup salted peanuts") == ["peanut"]
    assert normalize("2 cans black beans") == ["black bean"] and normalize("foie gras") == ["foie gras"]


@pytest.mark.parametrize("canonical, family", [
    ("garlic", "garlic"), ("minced garlic", "garlic"), ("garlic powder", "garlic powder"),
    ("sweet onion", "onion"), ("red onion", "onion"), ("sliced green onion", "green onion"), ("shallot", "shallot"),
    ("diced tomato", "tomato"), ("tomato paste", "tomato paste"), ("egg white", "egg"), ("egg yolk", "egg"),
    ("jasmine rice", "rice"), ("basmati rice", "rice"), ("rice vinegar", "vinegar"), ("rice flour", "rice flour"),
    ("heavy cream", "cream"), ("half and half", "cream"), ("sour cream", "sour cream"),
    ("vanilla ice cream", "vanilla ice cream"), ("penne", "pasta"), ("penne pasta", "pasta"),
    ("vanilla bean", "vanilla bean"), ("black bean", "bean"), ("extra lean ground beef", "beef"),
    ("sun-dried tomatoes in oil", "sun-dried tomatoes in oil"), ("olive oil", "oil"), ("tuna steak", "tuna steak"),
])
def test_families(canonical, family):
    assert family_for(canonical) == family


def test_broad_families():
    assert {"green onion", "shallot", "onion powder"} <= set(BROAD["onion"])
    assert {"garlic powder", "garlic salt"} <= set(BROAD["garlic"])
    assert {"tomato paste", "tomato sauce", "tomato puree"} <= set(BROAD["tomato"])


def level(name: str, tag: str):
    """Tag level for one name, or None."""
    return dict(tags_for(name)).get(tag)


@pytest.mark.parametrize("tag, contains, may_contain, none", [
    ("dairy", ["milk", "heavy cream", "butter", "cheddar cheese", "greek yogurt", "ghee", "whey", "buttermilk",
               "sour cream", "half and half", "parmesan cheese"],
     ["margarine", "chocolate", "bread"],
     ["coconut milk", "coconut cream", "almond milk", "soy milk", "oat milk", "peanut butter", "cream of tartar",
      "butternut squash", "cocoa butter", "vegan cheese", "dairy-free milk", "butter lettuce"]),
    ("egg", ["egg", "egg white", "egg yolk", "mayonnaise", "egg noodles", "meringue"], [], ["eggplant"]),
    ("peanut", ["peanuts", "peanut butter", "peanut oil"], [], ["almonds", "pine nuts"]),
    ("tree_nut", ["almonds", "cashews", "walnuts", "pecans", "pine nuts"], ["pesto"],
     ["peanuts", "nutmeg", "coconut", "water chestnut", "butternut squash"]),
    ("gluten", ["flour", "soy sauce", "bread crumbs", "spaghetti", "beer"], ["rolled oats"],
     ["almond flour", "gluten-free flour", "rice flour", "corn tortilla", "cornstarch"]),
    ("meat", ["bacon", "ground beef", "chicken breast", "chicken broth"], ["broth"],
     ["vegetarian sausage", "vegetable broth", "crab meat", "poultry seasoning"]),
    ("pork", ["bacon", "ham", "prosciutto"], ["sausage"], ["turkey bacon", "hamburger bun"]),
    ("poultry", ["chicken", "turkey breast"], [], ["chickpea", "beef broth", "quail egg"]),
    ("fish", ["salmon", "fish sauce", "anchovy", "worcestershire sauce"], [], ["shrimp"]),
    ("shellfish", ["shrimp", "crabmeat", "oyster sauce"], [], ["oyster mushroom", "salmon"]),
])
def test_tags(tag, contains, may_contain, none):
    assert {n: level(n, tag) for n in contains} == {n: "contains" for n in contains}
    assert {n: level(n, tag) for n in may_contain} == {n: "may_contain" for n in may_contain}
    assert {n: level(n, tag) for n in none} == {n: None for n in none}
    assert level("cookie cutter", "gluten") is None


@pytest.mark.parametrize("text, n", [
    ("Add 1 tsp. salt. Bake at 350 F. for 1.5 hours. Cool approx. 10 min.", 3),
    ("Use 2 oz. cheese and 1 tbsp. oil. Serve!", 2),
    ("1. Preheat oven.\n2. Mix.", 2),
    ("Mix well\nBake", 2),
    ("", 0),
])
def test_count_sentences(text, n):
    assert count_sentences(text) == n


@pytest.mark.parametrize("name, tag, level", [  # M6 audit fixes (docs/tag_audit.md, docs/lexicon_todo.md)
    ("chevre", "dairy", "contains"), ("grana padano", "dairy", "contains"), ("velveeta", "dairy", "contains"),
    ("jack", "dairy", "contains"), ("peanut butter cup", "dairy", "contains"),
    ("peanut butter chip", "dairy", "may_contain"), ("vanilla wafer", "dairy", "may_contain"),
    ("vanilla wafer", "egg", "may_contain"), ("won ton wrapper", "egg", "may_contain"), ("royal icing", "egg", "contains"),
    ("saltine", "gluten", "contains"), ("piecrust", "gluten", "contains"), ("guinness", "gluten", "contains"),
    ("guinness", "alcohol", "contains"), ("hard apple cider", "alcohol", "contains"), ("spirits", "alcohol", "contains"),
    ("rum extract", "alcohol", "may_contain"), ("pig", "pork", "contains"), ("speck", "pork", "contains"),
    ("poussin", "poultry", "contains"), ("schmaltz", "poultry", "contains"), ("bluefish", "fish", "contains"),
    ("orange roughy", "fish", "contains"), ("snail", "shellfish", "contains"),
])
def test_audit_misses_are_tagged(name, tag, level):
    assert dict(nz.tags_for(name)).get(tag) == level


@pytest.mark.parametrize("name, tag", [("peanut butter", "dairy"), ("jack daniel", "dairy"), ("spirit vinegar", "alcohol"),
                                       ("pie weight", "gluten"), ("whiskey", "gluten"), ("ginger beer", "alcohol")])
def test_audit_kept_out(name, tag):
    assert tag not in dict(nz.tags_for(name))


@pytest.mark.parametrize("raw, canonical", [("2 tablespoons buttermilk for brushing", "buttermilk"),
                                            ("Paprika for sprinkling", "paprika"), ("flour, for dusting", "flour"),
                                            ("1/4 cup Asiago cheese for topping", "asiago cheese")])
def test_purpose_phrase_is_not_the_ingredient(raw, canonical):
    assert nz.parse_line(raw)[0].name.canonical == canonical


def test_no_sugar_also_drops_sugar_made_sweets():
    assert {"marshmallow", "miniature marshmallow", "caramel", "candy"} <= set(BROAD["sugar"])


def test_ordinal_typos_are_result_references():
    from app.rules import rule_plan
    assert rule_plan("show me the frist one")["target"] == {"kind": "result_index", "value": "1"}
    assert rule_plan("show me the secnd one")["target"] == {"kind": "result_index", "value": "2"}
