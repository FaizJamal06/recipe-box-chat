"""M2 engine on the fixture DB: dataset line, rule planner, strict/broad stats, ranking, search, oracle = CLI."""
import pytest

import oracle
from app import stats
from app.db import connect, load_dataset
from app.planner import finish
from app.rules import rule_plan
from app.search import search
from app.session import respond


@pytest.fixture(scope="module")
def eng(mini):
    con = connect(mini[0])
    yield con, load_dataset(con)
    con.close()


def test_dataset_line_is_queried_not_hardcoded(eng):
    _, ds = eng
    assert ds.header(2) == ("2 of 23 valid recipes (30 records; invalid: no_ingredients 2, no_instructions 2, "
                            "no_title 2, empty_record 1)")


def test_rule_planner_demo_shapes():
    plan = lambda t: finish(rule_plan(t))
    s = plan(oracle.DEMO2)["stats"]
    assert (s["op"], s["all_of"], s["normalization"]) == ("percentage", ["garlic", "onion"], "both")
    s = plan(oracle.DEMO3)["stats"]
    assert (s["op"], s["field"], s["order"], s["limit"], s["all_of"]) == ("rank", "n_steps", "asc", 5, ["tomato"])
    s = plan("What is the median number of steps in recipes containing chicken?")["stats"]
    assert (s["op"], s["field"], s["all_of"]) == ("median", "n_steps", ["chicken"])
    assert plan("How many recipes contain garlic?")["stats"]["all_of"] == ["garlic"]
    p = plan("Find a penne pasta recipe, I cannot have dairy")["state_patch"]
    assert (p["mode"], p["query_text"], p["exclude_add"], p["exclude_tags_add"]) == ("new", "penne pasta", [], ["dairy"])
    assert plan("tell me a joke")["intent"] == "clarify"


def test_presence_is_strict_and_broad(eng):
    con, ds = eng
    got = lambda w: [(r.mode, r.value) for r in stats.count(con, ds, stats.Filters([stats.term(w, ds)]))]
    assert got("onion") == [("strict", 1), ("broad", 2)]  # broad adds a06's scallions (green onion)
    assert got("garlic") == [("strict", 3), ("broad", 3)]
    assert got("tomatoes") == [("strict", 1), ("broad", 1)]


def test_answers_state_dataset_line_rule_and_definitions(eng):
    con, ds = eng
    text, _, res = respond(con, ds, oracle.DEMO2)
    assert ds.header(res[0].value) in text and ds.header(res[1].value) in text
    assert "Normalization: strict garlic = the 'garlic' family" in text and "broad adds" in text
    assert "SQL (strict): SELECT COUNT(*)" in text and "SQL (broad):" in text
    text, _, res = respond(con, ds, oracle.DEMO3)
    assert stats.STEP_RULE in text and ds.header(res.n_analyzed) in text and "broad definition would match" in text
    text, _, _ = respond(con, ds, "Average number of steps")
    assert stats.STEP_RULE in text and ds.header(23) in text


def test_rank_uses_effective_steps_then_ingredients_then_id(eng):
    con, ds = eng
    r = stats.rank(con, ds, stats.Filters(), "n_steps", "asc", 30)
    keys = [(row[2], row[6], row[0]) for row in r.rows]  # n_steps, n_ingredients, id
    assert keys == sorted(keys) and len(keys) == 23
    para = {row[0]: row for row in r.rows}["fn:f04"]
    assert (para[2], para[3], para[5]) == (4, 1, 1)  # paragraph-format: effective steps = 4 sentences


def test_search_hard_filters_and_evidence(eng):
    con, ds = eng
    res = search(con, "", exclude_tags=["dairy"], limit=30)
    dairy = {r for r, in con.execute("SELECT recipe_id FROM recipe_tags WHERE tag = 'dairy' AND level = 'contains'")}
    assert res.total == len(res.hits) and not dairy & {h.id for h in res.hits}
    assert all(h.evidence and h.evidence[0].startswith("no dairy") for h in res.hits)
    garlic = stats.term("garlic", ds)
    assert {h.id for h in search(con, "", exclude=[garlic], limit=30).hits} & {"ar:a04", "epi:e01", "epi:e02"} == set()


def test_oracle_matches_cli(mini):
    db, files = mini
    bad = [r for r in oracle.check(files, db) if not r[3]]
    assert bad == []
