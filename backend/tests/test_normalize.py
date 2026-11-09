"""normalize.py: the tricky cases of PRD 4.5 (qty, units, headers, compounds, identity, tags) and 4.4 sentences."""
import pytest

from app.normalize import count_sentences, parse_line, tags_for


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
                   "rice vinegar", "rice flour", "egg", "egg noodles", "onion", "green onion", "onion powder"]
    assert [parse_line(x)[0].name.family for x in ["1 red onion", "2 green onions", "1 cup cherry tomatoes"]] \
        == ["onion", "green onion", "tomato"]


def test_vocab_fallback_never_adds_a_tag():
    assert canon("2 pounds heritage pork loin", vocab={"pork loin"}) == ["pork loin"]
    assert canon("1 cup cashew butter", vocab={"butter"}) == ["cashew butter"]
    assert canon("1 cup vegan cheese", vocab={"cheese"}) == ["vegan cheese"]


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
