"""Unsupported-attribute guard (PRD 5.3): deterministic, runs before any planner output is trusted.

The dataset has no nutrition, cook-time, servings, rating or category field. These questions are answered
here (no LLM call): say what is missing, then offer what the data does have, clearly labelled:
cook time -> durations *mentioned in the instructions* (not a total time); category -> a title-keyword proxy
with its keyword list shown, computed by the normal stats executor.
"""
import re
import sqlite3

from . import compose, stats
from .db import Dataset
from .rules import rule_plan

NUTRITION = re.compile(r"\b(?:calories?|kcal|nutrition(?:al)?|macros?|protein|carbs?|carbohydrates?|fat content|"
                       r"grams of fat|sodium|cholesterol|fiber|sugar content|healthy|healthiest)\b")
COOK_TIME = re.compile(r"\b(?:how long|cook(?:ing)? time|prep(?:aration)? time|total time|takes? (?:to make|long)|"
                       r"\d+\s*(?:minutes?|mins?|hours?|hrs?)|an hour|half an hour)\b")
SERVINGS = re.compile(r"\b(?:servings?|serves|how many people|feeds|portions?|yields?)\b")
RATING = re.compile(r"\b(?:ratings?|rated|stars|reviews?|best[- ]rated|most popular)\b")
STATS_WORDS = re.compile(r"\b(?:average|mean|median|how many|number of|percent(?:age)?|share|proportion|"
                         r"most common|top \d+|fewest|most)\b")
# category -> title keywords (whole words, porter-stemmed by FTS). A proxy, not a category field.
CATEGORIES = {
    "dessert": ["cake", "cookie", "pie", "brownie", "pudding", "tart", "cupcake", "cheesecake", "fudge", "mousse",
                "cobbler", "ice cream", "sorbet", "dessert"],
    "breakfast": ["breakfast", "pancake", "waffle", "omelet", "omelette", "frittata", "granola", "muffin", "scone"],
    "soup": ["soup", "stew", "chowder", "bisque"],
    "salad": ["salad", "slaw"],
    "drink": ["cocktail", "smoothie", "punch", "lemonade", "sangria", "martini", "margarita", "drink"],
}
_CAT = re.compile(r"\b(desserts?|sweets|breakfasts?|soups?|salads?|drinks?|cocktails?|beverages?)\b")
_CAT_KEY = {"sweets": "dessert", "cocktail": "drink", "beverage": "drink"}
DURATION = re.compile(r"\b\d+(?:\s*(?:-|to)\s*\d+)?\s*(?:minutes?|mins?|hours?|hrs?)\b", re.I)


def check(text: str) -> str | None:
    """The unsupported attribute a message asks about, or None. Category only for dataset-stats questions."""
    t = text.lower()
    for attr, rx in (("nutrition", NUTRITION), ("cook_time", COOK_TIME), ("servings", SERVINGS), ("rating", RATING)):
        if rx.search(t):
            return attr
    return "category" if _CAT.search(t) and STATS_WORDS.search(t) else None


def _recipe(con: sqlite3.Connection, rid: str | None):
    return con.execute("SELECT id, title, instructions_raw, n_ingredients FROM recipes WHERE id = ?",
                       (rid,)).fetchone() if rid else None


def answer(con: sqlite3.Connection, ds: Dataset, attr: str, text: str, rid: str | None) -> tuple[str, object]:
    """(reply, stats result or None). `rid` = the recipe the message refers to, if any."""
    rec = _recipe(con, rid)
    name = f"`{rec[0]}` '{rec[1].strip()}'" if rec else None
    if attr == "nutrition":
        out = ["Not in the dataset: there are no nutrition fields (no calories, macros, sodium, sugar or fibre), "
               "so I can't compute or estimate them from this data."]
        if rec:
            lines = [r for r, in con.execute("SELECT DISTINCT raw FROM ingredient_lines WHERE recipe_id = ? AND "
                                             "is_header = 0 AND is_not_food = 0 ORDER BY line_no", (rid,))]
            out.append(f"What the data does have for {name}: its {len(lines)} ingredient lines:")
            out += [f"  - {x}" for x in lines]
        else:
            out.append("I can list a recipe's ingredient lines instead; pick one from a search first.")
        return "\n".join(out), None
    if attr == "cook_time":
        out = ["Not in the dataset: there is no cook-time or prep-time field."]
        if rec:
            steps = [s for s in rec[2].split("\n") if s.strip()]
            found = [(i, m.group(0)) for i, s in enumerate(steps, 1) for m in DURATION.finditer(s)]
            out.append(f"Durations mentioned in the instructions of {name} (mentioned in instructions, not a total "
                       "time; steps may overlap or be missing times):")
            out += [f"  - step {i}: {d}" for i, d in found] or ["  (no durations mentioned)"]
        else:
            out.append("Ask about a specific recipe and I'll list the durations mentioned in its instructions.")
        return "\n".join(out), None
    if attr in ("servings", "rating"):
        what = {"servings": "servings / yield", "rating": "rating or review"}[attr]
        return f"Not in the dataset: there is no {what} field, so I can't answer that from this data.", None
    m = _CAT.search(text.lower())
    word = m.group(1).rstrip("s") if m else "category"
    cat = _CAT_KEY.get(word, word)
    kws = CATEGORIES.get(cat)
    head = f"Not in the dataset: there is no category field, so '{m.group(1) if m else 'category'}' isn't a filter."
    if not kws:
        return head + " Try a title keyword search instead.", None
    plan = rule_plan(text)
    s = plan.get("stats") if plan.get("intent") == "stats" else None
    s = {"op": "count", "field": "n_ingredients", "limit": 5, "order": "asc", **(s or {})}
    f = stats.Filters(all_of=[stats.term(w, ds) for w in s.get("all_of") or []], title_any=kws)
    if s["op"] in ("mean", "median"):
        res = stats.summary(con, ds, f, s["op"], s["field"])
    elif s["op"] == "rank":
        res = stats.rank(con, ds, f, s["field"], s["order"], s["limit"])
    elif s["op"] == "top_ingredients":
        res = stats.top_ingredients(con, ds, f, s["limit"])
    else:
        res = stats.count(con, ds, f, "percentage" if s["op"] == "percentage" else "count")
    body = compose.stats_reply(res, ds, {"stats": s})
    proxy = (f"PROXY (labelled): '{cat}' approximated as recipes whose title has any of these words: "
             f"{', '.join(kws)}. It misses {cat}s not named that way"
             + (" and includes savoury pies (e.g. pot pie)." if cat == "dessert" else "."))
    return "\n".join([head, proxy, body]), res
