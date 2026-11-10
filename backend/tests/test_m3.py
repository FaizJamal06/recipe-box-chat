"""M3 on the fixture DB: rule planner phrasings, LLM planner (mocked network) + fallback, sticky session,
unsupported guard, T2 matching (score, staples, quantities, no-match), tag stats."""
import dataclasses

import pytest

from app import guard, llm, match, planner, stats
from app.db import connect, load_dataset
from app.planner import finish
from app.rules import rule_plan
from app.session import Session

DEMO5 = ("I have eggs, onions, tomatoes, and rice. Suggest five recipes using as many as possible, no peanuts, "
         "at most six steps, fewest additional ingredients.")


@pytest.fixture(scope="module")
def eng(mini):
    """Fixture DB + a Dataset whose vocab holds every canonical (the fixture is too small for VOCAB_MIN=5)."""
    con = connect(mini[0])
    ds = load_dataset(con)
    yield con, dataclasses.replace(ds, vocab=frozenset(c for c, in con.execute("SELECT canonical FROM vocab")))
    con.close()


def p(text: str) -> dict:
    return finish(rule_plan(text))


def test_rule_planner_m3_phrasings():
    d = p(DEMO5)
    assert d["intent"] == "match"
    s = d["state_patch"]
    assert (s["have_set"], s["exclude_tags_add"], s["max_steps"], s["prefs_add"], s["limit"]) == (
        ["eggs", "onions", "tomatoes", "rice"], ["peanut"], 6, ["use_most", "fewest_extra"], 5)
    assert p("Exclude eggs too.")["state_patch"]["exclude_tags_add"] == ["egg"]
    assert p("I have 2 eggs and 1 cup rice")["state_patch"]["have_set"] == ["2 eggs", "1 cup rice"]
    assert p("show me the steps for the second one")["target"] == {"kind": "result_index", "value": "2"}
    assert p("also no garlic")["state_patch"]["exclude_add"] == ["garlic"]
    assert p("I cannot have dairy")["state_patch"]["exclude_tags_add"] == ["dairy"]
    assert p("dairy is fine now")["state_patch"]["exclude_tags_remove"] == ["dairy"]
    assert p("something under 5 steps please")["state_patch"]["max_steps"] == 4
    assert p("no more than 3 steps")["state_patch"]["exclude_add"] == []  # 'no more' is not an exclusion
    st = p("How many recipes are dairy-free?")["stats"]
    assert (st["tags"], st["tag_mode"]) == (["dairy"], "free")
    assert p("Find a dairy-free pasta recipe")["state_patch"]["query_text"] == "pasta"


def test_guard_detects_unsupported_and_leaves_normal_questions():
    assert guard.check("How many calories are in that one?") == "nutrition"
    assert guard.check("How long does it take to make?") == "cook_time"
    assert guard.check("How many servings does it make?") == "servings"
    assert guard.check("What's the average number of ingredients in desserts?") == "category"
    for ok in ("Find a dessert recipe", "at most six steps", "How many recipes contain garlic?"):
        assert guard.check(ok) is None


def test_category_proxy_is_labelled_and_computed(eng):
    con, ds = eng
    text, res = guard.answer(con, ds, "category", "What's the average number of ingredients in desserts?", None)
    assert "no category field" in text and "PROXY (labelled)" in text and "cookie" in text
    assert res.value == 4.5 and res.n_analyzed == 4  # Sugar Cookies, Lemon Tart, Meringue Cookies, Chicken Pot Pie
    text, _ = guard.answer(con, ds, "cook_time", "how long does it take", "ar:a04")
    assert "no cook-time" in text and "mentioned in instructions, not a total time" in text
    text, _ = guard.answer(con, ds, "nutrition", "calories?", "ar:a01")
    assert "no nutrition fields" in text and "its 5 ingredient lines" in text


def test_tag_stats_state_both_levels(eng):
    con, ds = eng
    r = stats.tag_count(con, ds, ["dairy"], "free")
    assert [(x.mode, x.value) for x in r] == [("lenient", 15), ("strict", 12)]  # 8 contains, + 3 may_contain
    assert "may_contain" in r[0].method and "alt" in r[0].normalization_note


def test_match_score_quantities_and_staples(eng):
    con, ds = eng
    res = match.match(con, ds, ["2 eggs", "1 cup rice"], limit=20)
    rows = {r.id: r for r in res.rows}
    assert rows["ar:a01"].qty == ["egg: sufficient (recipe needs 2, you have 2)"]
    assert rows["epi:e03"].qty == ["egg: short by 3 (recipe needs 5, you have 2)"]  # 3 yolks + 2 whites
    e01 = rows["epi:e01"]  # rice vinegar / rice flour are their own families: extra, not matched
    assert (e01.matched, e01.unused, sorted(e01.extra)) == (["rice"], ["egg"], ["garlic", "garlic powder",
                                                                               "rice flour", "rice vinegar"])
    assert e01.score == pytest.approx(2.0 * 1 - 1.0 * 4 - 0.1 * 2)
    assert rows["fn:f04"].extra == [] and rows["fn:f04"].staples == ["salt", "water"]
    keys = [(-r.score, -len(r.matched), len(r.extra), r.n_steps, r.id) for r in res.rows]
    assert keys == sorted(keys)
    no_staples = match.match(con, ds, ["rice"], staples=(), limit=20)
    assert sorted({r.id: r for r in no_staples.rows}["fn:f04"].extra) == ["salt", "water"]
    assert match._in_unit(2, "tablespoon", "cup") == pytest.approx(0.125) and match._in_unit(1, "pound", "cup") is None


def test_match_no_match_lists_relaxations_separately(eng):
    con, ds = eng
    res = match.match(con, ds, ["eggs"], exclude=[stats.term("sugar", ds)], max_steps=1)
    assert res.rows == [] and [label for label, _ in res.alternatives] == ["no sugar", "at most 1 step"]
    assert res.alternatives[0][1] == [] and "fn:f08" in [r.id for r in res.alternatives[1][1]]
    from app.compose import match_reply
    text = match_reply(res, ds)
    assert "No recipe satisfies all hard constraints" in text
    assert text.index("No recipe satisfies") < text.index("CLOSEST ALTERNATIVES") and "Eligible:" not in text
    dropped = match.match(con, ds, ["eggs", "rice"], exclude_tags=["egg"])
    assert [h.term.text for h, _ in dropped.dropped] == ["egg"] and all("egg" not in r.matched for r in dropped.rows)


def test_session_sticky_restrictions_and_references(eng):
    con, ds = eng
    s = Session(con, ds, use_llm=False)
    t = s.respond("Find a rice recipe")
    assert "fn:f04" in s.state.last_results and t.info.source == "rule" and "rule parser" in t.meta()
    s.respond("I cannot have dairy")
    assert s.state.exclude_tags == ["dairy"] and "fn:f04" not in s.state.last_results  # f04 has butter
    first = s.state.last_results[0]
    t = s.respond("show me the steps for the first one")
    assert s.state.selected_recipe_id == first and "Steps:" in t.reply and "no dairy" in t.reply
    s.respond("also no garlic")
    assert s.state.exclude == ["garlic"] and "epi:e01" not in s.state.last_results
    t = s.respond("Find a tomato recipe")
    assert s.state.query_text == "tomato" and s.state.exclude_tags == ["dairy"] and "Kept your restrictions" in t.reply
    s.respond("dairy is fine now")
    assert s.state.exclude_tags == [] and s.state.exclude == ["garlic"]
    assert s._resolve({"kind": "recipe_id", "value": "ar:a01"}, "") is None  # never an id it didn't show
    t = s.respond("How many calories are in this recipe?")
    assert t.info.source == "guard" and t.llm_calls == 0


@pytest.fixture
def fake_llm(monkeypatch, tmp_path):
    """A key, a private cache file, and a scripted _remote: returns the queued answers in order."""
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(llm, "LLM_CACHE", tmp_path / "cache.sqlite")
    queue = []

    def remote(system, prompt, schema):
        x = queue.pop(0)
        if isinstance(x, Exception):
            raise x
        return x, {"prompt_tokens": 100}
    monkeypatch.setattr(llm, "_remote", remote)
    return queue


GOOD = ('{"intent":"search","state_patch":{"mode":"new","query_text":"penne pasta","include_add":[],"exclude_add":[],'
        '"exclude_remove":[],"exclude_tags_add":["dairy"],"exclude_tags_remove":[],"max_steps":0,"have_set":[],'
        '"prefs_add":[],"limit":0},"stats":{"op":"count","field":"n_steps","order":"asc","limit":0,"all_of":[],'
        '"any_of":[],"none_of":[],"title_contains":[],"tags":[],"tag_mode":"free"},"target":{"kind":"none",'
        '"value":""},"unsupported":{"attribute":"none","reason":""}}')


def test_llm_plan_retry_cache_and_fallback(fake_llm, eng):
    con, ds = eng
    s = Session(con, ds)
    fake_llm += ['{"intent": "dance"}', GOOD]  # invalid, then valid: 2 requests, the max
    t = s.respond("what penne dish works without dairy?")
    assert t.info.source == "llm" and t.llm_calls == 2 and s.state.exclude_tags == ["dairy"]
    s2 = Session(con, ds)  # same prompt (fresh state) -> cache hit, no request
    t = s2.respond("what penne dish works without dairy?")
    assert t.info.source == "llm" and t.llm_calls == 0 and t.info.calls[0].cached
    fake_llm += [llm.LLMError("HTTP 429 RESOURCE_EXHAUSTED")]
    t = Session(con, ds).respond("Find a rice recipe")
    assert t.info.source == "rule" and "LLM unavailable: HTTP 429" in t.meta() and t.llm_calls == 1
    fake_llm += ["not json", '{"intent": 3}']
    t = Session(con, ds).respond("Find a tomato recipe")
    assert t.info.source == "rule" and t.llm_calls == 2 and not fake_llm


def test_slow_llm_times_out_client_side(monkeypatch):
    import time
    from types import SimpleNamespace
    slow = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: time.sleep(0.5)))
    monkeypatch.setattr(llm, "_client", slow)
    monkeypatch.setattr(llm, "TIMEOUT_MS", 100)
    t = time.perf_counter()
    with pytest.raises(llm.LLMError, match="timeout"):
        llm._remote("s", "p", {"type": "object"})
    assert time.perf_counter() - t < 0.4


def test_high_confidence_rule_patterns_skip_the_llm(fake_llm):
    from app.session import SessionState
    st, known = SessionState(), lambda w: w in ("garlic", "dairy", "eggs")
    for text in ("I cannot have dairy", "also no garlic", "Exclude eggs too.", "dairy is fine now",
                 "show me the steps for the second one", "at most 1 step", "I have 2 eggs and 1 cup rice", DEMO5):
        assert planner.plan(text, st, known=known)[1].source == "rule_direct", text
    fake_llm += [GOOD, GOOD]  # these go to the LLM: a new dish, and an exclusion of an unknown word
    for text in ("Find a penne pasta recipe", "no I meant the other one"):
        assert planner.plan(text, st, known=known)[1].source == "llm", text
    assert not fake_llm


def test_prompt_is_compact():
    from app.session import SessionState
    st = SessionState(exclude_tags=["dairy"], history=[(f"u{i}", "b" * 200) for i in range(6)])
    text = planner.prompt("hi", st)
    assert text.count("user: ") == 4 and "b" * 81 not in text and "have" not in text.split("MESSAGE")[0]
    assert planner.prompt("hi", SessionState()) == "MESSAGE: hi"


def test_planner_validation_rejects_unknown_enums():
    with pytest.raises(ValueError):
        planner.validate({"intent": "search", "state_patch": {"exclude_tags_add": ["sugar"]}})
    assert planner.validate({"intent": "stats", "stats": {"op": "rank"}})["stats"]["limit"] == 5
