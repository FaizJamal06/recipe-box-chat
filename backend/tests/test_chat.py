"""Chatbot regressions: wheat allergy -> gluten, rule-parser keyword fallback, cuisine proxy, the voice validator,
plus small talk, 'why this one?', contradictions, spelling retry and follow-up suggestions."""
import dataclasses

import pytest

from app import guard, planner, talk, voice
from app import normalize as nz
from app.db import connect, load_dataset
from app.planner import finish
from app.rules import rule_plan
from app.search import correct
from app.session import Session, SessionState


@pytest.fixture(scope="module")
def eng(mini):
    con = connect(mini[0])
    ds = load_dataset(con)
    yield con, dataclasses.replace(ds, vocab=frozenset(c for c, in con.execute("SELECT canonical FROM vocab")))
    con.close()


def test_wheat_lexicon_and_allergy_phrases():
    for w in ("bucatini", "cavatapi", "orecchiette", "linguini", "atta", "pan dulce", "lo mein"):
        assert ("gluten", "contains") in nz.tags_for(w), w
    for w in ("brown rice pasta", "chickpea pasta", "rice vermicelli", "zucchini noodle", "gluten-free penne"):
        assert not any(t == "gluten" for t, _ in nz.tags_for(w)), w
    assert nz.tags_for("soba noodle") == (("gluten", "may_contain"),)
    assert nz.parse_line("1 pan dulce")[0].name.canonical == "pan dulce"  # not masked as a pan
    for text in ("im allergic to wheat", "I have a wheat allergy", "I'm celiac"):
        p = finish(rule_plan(text))
        assert p["intent"] == "search" and p["state_patch"]["exclude_tags_add"] == ["gluten"], text


def test_wheat_allergy_reply_says_it_is_stricter(eng):
    con, ds = eng
    s = Session(con, ds, use_llm=False)
    s.respond("Find a rice recipe")
    t = s.respond("I'm allergic to wheat")
    assert s.state.exclude_tags == ["gluten"] and "barley and rye" in t.reply


def test_keyword_fallback_when_nothing_matches(eng):
    con, ds = eng
    p, info = planner.plan("paneer ki koi recipe batao", SessionState(), use_llm=False)
    assert p["intent"] == "search" and p["keyword"] and p["state_patch"]["query_text"] == "paneer"
    t = Session(con, ds, use_llm=False).respond("tomato wala kuch batao")
    assert "keyword search" in t.reply and "ran as keyword search" in t.meta()
    t = Session(con, ds, use_llm=False).respond("whats the weather like today")
    assert t.plan["intent"] == "clarify" and t.reply == talk.ASK  # no food word: one question, not a guessed search


def test_cuisine_proxy_is_labelled_with_honest_count(eng):
    con, ds = eng
    assert guard.cuisine_of("Gujarati dishes") == "gujarati" and guard.check("any italian recipes?") == "cuisine"
    assert guard.cuisine_of("an italian sausage recipe") is None and guard.check("italian seasoning") is None
    s = Session(con, ds, use_llm=False)
    t = s.respond("Italian recipes without meat")
    assert "no cuisine field" in t.reply and "risotto" in t.reply and s.state.exclude_tags == ["meat"]
    assert t.result.total == len(t.result.hits) and "title has any of" in t.result.filters  # honest, even if 0
    t = s.respond("Gujarati dishes")
    assert t.result.total == 0 and "0 recipes match" in t.reply  # nothing in the fixture: says 0, not a guess


FACTS = {"user_said": "find penne", "active_filters": "no dairy", "notes": [], "kind": "search",
         "total_matches": 81, "top": [{"rank": 1, "title": "Pat's Simple Penne", "id": "ar:9mPiUMSt/0wx", "steps": 4,
                                       "ingredients": 5}, {"rank": 2, "title": "Pasta and Beans", "id": "fn:Ab.c9",
                                                           "steps": 3, "ingredients": 6}]}


def test_voice_validator_accepts_only_facts():
    ok = "I found 81 dairy-free penne recipes. Pat's Simple Penne (ar:9mPiUMSt/0wx) has 5 ingredients and 4 steps."
    assert voice.check(ok, FACTS) == ok
    assert voice.check("Two quick picks: Pat's Simple Penne and Pasta and Beans.", FACTS)  # 'two' = 2 results
    for bad in ("I found 82 recipes for you, all dairy-free.", "Pat's Simple Penne takes 20 minutes to make.",
                "Try ar:madeUpId123, it is great!", "There are seven great options here for you."):
        with pytest.raises(ValueError):
            voice.check(bad, FACTS)


def test_have_list_runs_match_through_the_session(eng):
    """Session-level guard: a have-list must run T2 matching (a dropped branch once turned it into a search)."""
    from app.match import MatchResult
    con, ds = eng
    s = Session(con, ds, use_llm=False)
    t = s.respond("i got eggs rice and onions, what can i make")
    assert isinstance(t.result, MatchResult) and s.state.active_task == "match"
    assert [h.term.text for h in t.result.have] == ["egg", "rice", "onion"]  # 'eggs rice' split by the vocab
    t = s.respond("exclude eggs too")
    assert isinstance(t.result, MatchResult) and "egg" in [h.term.text for h, _ in t.result.dropped]


def test_conversation_smalltalk_explain_conflict_spelling_followups(eng):
    from app.talk import suggestions
    con, ds = eng
    s = Session(con, ds, use_llm=False)
    assert "What are you in the mood for" in s.respond("hi there").reply
    assert "23 valid recipes" in s.respond("wat can u do?").reply
    t = s.respond("Find a rice recipe")
    first = s.state.last_results[0]
    t = s.respond("why the first one?")
    assert t.plan["intent"] == "explain" and first in t.reply and "#1 of 2 matches" in t.reply
    t = s.respond("vegan chicken pot pie")
    assert s.conflict == ("meat", "chicken") and "clashes" in t.reply and t.result is None
    labels = [x["message"] for x in suggestions(s.state, {"type": "text", "cards": []}, t.plan, s.conflict)]
    assert labels[0] == "meat is fine now" and labels[1] == "find a pot pie recipe"
    s.state.exclude_tags.append("poultry")  # the LLM may add poultry too: one chip must drop both
    assert s._conflict() == ("meat and poultry", "chicken")
    t = s.respond("meat and poultry are fine now")
    assert "meat" not in s.state.exclude_tags and "poultry" not in s.state.exclude_tags
    assert correct("chiken pot pie", ds.vocab) == "chicken pot pie"
    t = Session(con, ds, use_llm=False).respond("find a chiken pot pie recipe")
    assert "spelling corrected" in t.reply and t.result.total >= 1
