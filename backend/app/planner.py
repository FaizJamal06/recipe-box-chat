"""LLM call #1: user text + compact session state -> JSON plan (PRD 5.2), with the rule planner as fallback.

The LLM only classifies and extracts words; executors compute every fact. Its output is validated against
fixed enums (invalid -> one retry inside llm.generate_json, then the rule planner). Any LLM failure (no key,
429, network, invalid JSON twice) falls back to rules.rule_plan and the reply shows "rule parser".
"""
import json
from dataclasses import dataclass, field

from . import llm
from .rules import rule_plan

INTENTS = ["search", "recipe_detail", "stats", "match", "unsupported", "clarify", "smalltalk"]
TAGS = ["dairy", "egg", "peanut", "tree_nut", "gluten", "meat", "pork", "poultry", "fish", "shellfish"]
OPS = ["count", "percentage", "top_ingredients", "mean", "median", "rank"]
PREFS = ["use_most", "fewest_extra", "fewest_steps", "no_staples"]
ATTRS = ["none", "nutrition", "cook_time", "servings", "rating", "category", "other"]
S, I, B = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
L = {"type": "array", "items": S}
enum = lambda xs: {"type": "string", "enum": xs}
lenum = lambda xs: {"type": "array", "items": enum(xs)}
obj = lambda props: {"type": "object", "properties": props, "required": list(props)}
SCHEMA = obj({
    "intent": enum(INTENTS),
    "state_patch": obj({"mode": enum(["refine", "new"]), "query_text": S, "include_add": L, "exclude_add": L,
                        "exclude_remove": L, "exclude_tags_add": lenum(TAGS), "exclude_tags_remove": lenum(TAGS),
                        "max_steps": I, "have_set": L, "prefs_add": lenum(PREFS), "limit": I}),
    "stats": obj({"op": enum(OPS), "field": enum(["n_ingredients", "n_steps"]), "order": enum(["asc", "desc"]),
                  "limit": I, "all_of": L, "any_of": L, "none_of": L, "title_contains": L, "tags": lenum(TAGS),
                  "tag_mode": enum(["free", "contains"])}),
    "target": obj({"kind": enum(["none", "result_index", "recipe_id", "title", "selected"]), "value": S}),
    "unsupported": obj({"attribute": enum(ATTRS), "reason": S}),
})
SYSTEM = f"""You turn one message to a recipe-database chatbot into a JSON plan. Never answer the question, never
state facts or numbers about recipes, never invent recipe ids (only ids listed in LAST_RESULTS).
Fill every field; use "" / 0 / [] for "not mentioned".
intent: search = find recipes (dish words go to query_text); match = the user lists ingredients they have
(have_set: each item as written, with its quantity, e.g. "2 eggs", "1 cup rice"); recipe_detail = show one
recipe's steps/ingredients (target); stats = counts/percentages/rankings/averages over the dataset;
unsupported = nutrition/calories, cook or prep time, servings, ratings, or a category/cuisine field (e.g.
"desserts"); clarify = unclear; smalltalk = greeting/thanks.
state_patch: mode "new" for a new dish or a new have-list, "refine" when the user only adds/removes
restrictions to the current task. exclude_tags_add uses only these tags: {', '.join(TAGS)} ("eggs" -> egg,
"vegetarian" -> meat, poultry, fish, shellfish); any other "no X" goes to exclude_add as plain words.
"X is fine now" -> exclude_remove / exclude_tags_remove. max_steps: "at most 6 steps" -> 6, "under 5 steps" -> 4,
remove the limit -> -1, not mentioned -> 0. prefs_add: "as many as possible" -> use_most, "fewest additional
ingredients" -> fewest_extra, "fewest steps" -> fewest_steps, "don't assume salt/pepper/water" -> no_staples.
limit: number of recipes asked for, else 0.
stats: ingredient words go to all_of/any_of/none_of as plain words. "How many recipes are dairy-free" -> op count,
tags [dairy], tag_mode free; "how many contain dairy" -> tag_mode contains. Ranks: "fewest steps" -> op rank,
field n_steps, order asc. Default limit 5 for rank, 10 for top_ingredients.
target: "the second one" -> result_index "2"; "the last one" -> result_index "-1"; "this/that recipe", "it" ->
selected; a listed id -> recipe_id; a title -> title.
"""


@dataclass
class PlanInfo:
    """How the plan was made, for the per-turn report."""
    source: str  # 'llm' | 'rule' | 'guard'
    calls: list = field(default_factory=list)  # llm.Call per request (cache hits included, ms = 0)
    reason: str = ""  # why the rule parser was used


def finish(plan: dict) -> dict:
    """Fill every key so executors never check for missing fields (rule and LLM plans share one shape)."""
    p = plan.get("state_patch") or {}
    st = plan.get("stats") or {}
    patch = {"mode": p.get("mode") or "refine", "query_text": p.get("query_text") or None}
    for k in ("include_add", "exclude_add", "exclude_remove", "exclude_tags_add", "exclude_tags_remove",
              "have_set", "prefs_add"):
        patch[k] = [str(x).strip() for x in p.get(k) or [] if str(x).strip()]
    patch["max_steps"] = p.get("max_steps") or None  # 0 / None = unchanged
    patch["limit"] = p.get("limit") or None
    stats = {"op": st.get("op") or "count", "field": st.get("field") or "n_steps", "order": st.get("order") or "asc",
             "limit": st.get("limit") or (10 if st.get("op") == "top_ingredients" else 5),
             **{k: list(st.get(k) or []) for k in ("all_of", "any_of", "none_of", "title_contains", "tags")},
             "tag_mode": st.get("tag_mode") or "free", "normalization": "both"}
    tg = plan.get("target") or {}
    target = {"kind": tg.get("kind") or "none", "value": str(tg.get("value") or "")}
    un = plan.get("unsupported") or {}
    return {"intent": plan.get("intent") or "clarify", "state_patch": patch, "stats": stats, "target": target,
            "unsupported": {"attribute": un.get("attribute") or "none", "reason": un.get("reason") or ""}}


def validate(d: dict) -> dict:
    """LLM JSON -> finished plan; ValueError on anything outside the schema's enums (triggers the retry)."""
    if d.get("intent") not in INTENTS:
        raise ValueError("intent")
    p, st = d.get("state_patch") or {}, d.get("stats") or {}
    if not set(p.get("exclude_tags_add") or []) <= set(TAGS) or not set(st.get("tags") or []) <= set(TAGS):
        raise ValueError("tags")
    if d["intent"] == "stats" and st.get("op") not in OPS:
        raise ValueError("op")
    if not isinstance(p.get("max_steps", 0), int) or not isinstance(p.get("limit", 0), int):
        raise ValueError("ints")
    return finish(d)


def prompt(text: str, state) -> str:
    """State JSON + numbered last results (max 10) + last 6 turns + the message; sorted keys keep it cacheable."""
    st = {k: getattr(state, k) for k in ("active_task", "query_text", "exclude", "exclude_tags", "max_steps", "have",
                                         "prefs", "selected_recipe_id")}
    res = "\n".join(f"{i}. {rid} | {title}" for i, (rid, title) in enumerate(state.last_titles[:10], 1)) or "(none)"
    hist = "\n".join(f"user: {u}\nbot: {b}" for u, b in state.history[-6:]) or "(none)"
    return f"STATE: {json.dumps(st, sort_keys=True)}\nLAST_RESULTS:\n{res}\nHISTORY:\n{hist}\nMESSAGE: {text}"


def plan(text: str, state, use_llm: bool = True) -> tuple[dict, PlanInfo]:
    """LLM plan, or the rule plan (with the reason) on any LLM failure."""
    if not use_llm or not llm.available():
        return finish(rule_plan(text)), PlanInfo("rule", reason="LLM disabled" if not use_llm else "no GEMINI_API_KEY")
    try:
        p, calls = llm.generate_json(SYSTEM, prompt(text, state), SCHEMA, validate)
        return p, PlanInfo("llm", calls)
    except llm.LLMError as e:
        return finish(rule_plan(text)), PlanInfo("rule", e.calls, str(e))
