"""One conversation turn: plan -> execute -> compose. M2: stateless (each message stands alone);
M3 adds the sticky SessionState of PRD 5.1 and the LLM planner in front of the rule planner.

The CLI, the API and eval/oracle.py all go through respond(), so what the oracle checks is what users see.
"""
import sqlite3

from . import compose, search, stats
from .db import Dataset
from .planner import rule_plan

HELP = ("I can answer, for example: 'How many recipes contain garlic and onion?', 'Among recipes containing "
        "tomato, which five have the fewest steps?', 'Average number of ingredients', 'Find a penne pasta recipe "
        "with no dairy'.")


def execute(con: sqlite3.Connection, ds: Dataset, plan: dict):
    """Run a plan's executor; returns its Result(s) / SearchResult. Raises stats.UnknownIngredient."""
    if plan["intent"] == "stats":
        s = plan["stats"]
        terms = lambda k: [stats.term(w, ds) for w in s.get(k) or []]
        f = stats.Filters(terms("all_of"), terms("any_of"), terms("none_of"), list(s.get("title_contains") or []))
        if s["op"] in ("count", "percentage"):
            return stats.count(con, ds, f, s["op"])
        if s["op"] == "rank":
            return stats.rank(con, ds, f, s["field"], s["order"], s["limit"])
        if s["op"] in ("mean", "median"):
            return stats.summary(con, ds, f, s["op"], s["field"])
        return stats.top_ingredients(con, ds, f, s["limit"])
    p = plan["state_patch"]
    return search.search(con, p.get("query_text") or "", [], [stats.term(w, ds) for w in p.get("exclude_add") or []],
                         p.get("exclude_tags_add") or [], p.get("max_steps"))


def respond(con: sqlite3.Connection, ds: Dataset, text: str) -> tuple[str, dict, object]:
    """(reply text, plan, executor result or None) for one user message."""
    plan = rule_plan(text)
    if plan["intent"] not in ("stats", "search"):
        return HELP, plan, None
    try:
        res = execute(con, ds, plan)
    except stats.UnknownIngredient as e:
        return f"I don't recognise '{e}' as an ingredient in this dataset. {HELP}", plan, None
    reply = compose.stats_reply(res, ds, plan) if plan["intent"] == "stats" else compose.search_reply(res, ds)
    return reply, plan, res
