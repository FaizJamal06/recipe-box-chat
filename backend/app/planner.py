"""LLM call #1: user text + compact session state -> JSON plan (PRD 5.2), with the rule planner as fallback.

The LLM only classifies and extracts words; executors compute every fact. Its output is validated against
fixed enums (invalid -> one retry inside llm.generate_json, then the rule planner). Any LLM failure (no key,
429, network, invalid JSON twice) falls back to rules.rule_plan and the reply shows "rule parser".
"""
import json
from dataclasses import dataclass, field

from . import llm
from . import rules
from .rules import confident, keyword_plan, rule_plan

INTENTS = ["search", "recipe_detail", "stats", "match", "substitute", "unsupported", "clarify", "smalltalk",
           "explain", "offtopic"]
TALK = ["none", "greeting", "thanks", "capabilities", "bye"]
TAGS = ["dairy", "egg", "peanut", "tree_nut", "gluten", "soy", "sesame", "meat", "pork", "poultry", "fish",
        "shellfish", "gelatin", "honey", "alcohol", "root_veg"]
DIETS = list(rules.DIETS)
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
                        "max_steps": I, "have_set": L, "prefs_add": lenum(PREFS), "limit": I,
                        "diets_add": lenum(DIETS)}),
    "stats": obj({"op": enum(OPS), "field": enum(["n_ingredients", "n_steps"]), "order": enum(["asc", "desc"]),
                  "limit": I, "all_of": L, "any_of": L, "none_of": L, "title_contains": L, "tags": lenum(TAGS),
                  "tag_mode": enum(["free", "contains"])}),
    "target": obj({"kind": enum(["none", "result_index", "recipe_id", "title", "selected"]), "value": S}),
    "unsupported": obj({"attribute": enum(ATTRS), "reason": S}),
    "substitution": obj({"remove": L, "replace_with": S, "dish": S, "remove_tags": lenum(TAGS), "option": I,
                         "force": B, "dataset_only": B}),
    "talk": enum(TALK),
    "question": S,
})
SYSTEM = """Convert a message to a recipe chatbot into a JSON plan. Never answer it or state recipe facts; only use
ids from LAST_RESULTS. Unmentioned fields: "", 0 or [].
intent: search (dish words -> query_text) | match (user lists ingredients they have -> have_set, items as
written incl. quantity: "2 eggs") | recipe_detail (target) | stats (counts, %, ranks, averages) | unsupported
(nutrition, cook time, servings, ratings, category) | substitute (change THIS recipe: remove/replace an ingredient,
"make it vegan" -> remove_tags, "use the second option" -> option 2, "adapt it anyway" -> force; dish = the dish
the user names, else "") | explain ("why this one?": target) | smalltalk (talk:
greeting/thanks/capabilities/bye) | offtopic (not about food or these recipes) | clarify (only when truly
ambiguous: put ONE short question, no numbers, in question).
state_patch.mode: new = new dish or have-list; refine = only adds/removes restrictions. Allergen/diet words ->
exclude_tags_add (eggs -> egg; wheat -> gluten); a diet or allergy preset (vegetarian, vegan, pescatarian, halal,
jain, kosher, lactose intolerant, celiac / wheat, nut allergy) -> diets_add (the executor expands it); other
"no X" -> exclude_add. Messages may have typos, slang or Hinglish: plan by meaning.
"X is fine now" -> *_remove. max_steps: "at most 6" -> 6, "under 5" -> 4, drop limit -> -1.
prefs_add: as many as possible -> use_most; fewest additional -> fewest_extra; fewest steps -> fewest_steps;
no salt/pepper/water assumed -> no_staples. limit = recipes asked for.
stats: ingredients as plain words in all_of/any_of/none_of; "dairy-free" -> tags [dairy], tag_mode free;
"fewest steps" -> op rank, field n_steps, order asc.
target: "the second one" -> result_index "2"; last -> "-1"; this/that/it -> selected; else recipe_id or title.
"""


@dataclass
class PlanInfo:
    """How the plan was made, for the per-turn report."""
    source: str  # 'llm' | 'rule' (LLM failed or off) | 'rule_direct' (high-confidence pattern) | 'guard'
    calls: list = field(default_factory=list)  # llm.Call per request (cache hits included, ms = 0)
    reason: str = ""  # why the rule parser was used


def finish(plan: dict) -> dict:
    """Fill every key so executors never check for missing fields (rule and LLM plans share one shape)."""
    p = plan.get("state_patch") or {}
    st = plan.get("stats") or {}
    patch = {"mode": p.get("mode") or "refine", "query_text": p.get("query_text") or None}
    for k in ("include_add", "exclude_add", "exclude_remove", "exclude_tags_add", "exclude_tags_remove",
              "have_set", "prefs_add", "diets_add"):
        patch[k] = [str(x).strip() for x in p.get(k) or [] if str(x).strip()]
    patch["max_steps"] = p.get("max_steps") or None  # 0 / None = unchanged
    patch["limit"] = p.get("limit") or None
    # a fresh request with no dish words ('something vegan for dinner'): drop the old dish, keep restrictions
    patch["reset"] = bool(p.get("reset")) or (patch["mode"] == "new" and not patch["query_text"]
                                              and not patch["have_set"])
    stats = {"op": st.get("op") or "count", "field": st.get("field") or "n_steps", "order": st.get("order") or "asc",
             "limit": st.get("limit") or (10 if st.get("op") == "top_ingredients" else 5),
             **{k: list(st.get(k) or []) for k in ("all_of", "any_of", "none_of", "title_contains", "tags")},
             "tag_mode": st.get("tag_mode") or "free", "normalization": "both"}
    tg = plan.get("target") or {}
    target = {"kind": tg.get("kind") or "none", "value": str(tg.get("value") or "")}
    un = plan.get("unsupported") or {}
    sb = plan.get("substitution") or {}
    substitution = {"remove": [str(x).strip() for x in sb.get("remove") or [] if str(x).strip()],
                    "replace_with": str(sb.get("replace_with") or "").strip(), "dish": str(sb.get("dish") or "").strip(),
                    "remove_tags": [t for t in sb.get("remove_tags") or [] if t in TAGS], "option": int(sb.get("option") or 0),
                    "force": bool(sb.get("force")), "dataset_only": sb.get("dataset_only") is not False}
    return {"intent": plan.get("intent") or "clarify", "state_patch": patch, "stats": stats, "target": target,
            "unsupported": {"attribute": un.get("attribute") or "none", "reason": un.get("reason") or ""},
            "substitution": substitution, "talk": plan.get("talk") or "none", "question": str(plan.get("question") or "")[:200],
            "keyword": bool(plan.get("keyword"))}


def validate(d: dict) -> dict:
    """LLM JSON -> finished plan; ValueError on anything outside the schema's enums (triggers the retry)."""
    if d.get("intent") not in INTENTS:
        raise ValueError("intent")
    p, st = d.get("state_patch") or {}, d.get("stats") or {}
    if not (set(p.get("exclude_tags_add") or []) <= set(TAGS) and set(st.get("tags") or []) <= set(TAGS)
            and set(p.get("diets_add") or []) <= set(DIETS)):
        raise ValueError("tags")
    if d["intent"] == "stats" and st.get("op") not in OPS:
        raise ValueError("op")
    if d.get("talk", "none") not in TALK:
        raise ValueError("talk")
    if not isinstance(p.get("max_steps", 0), int) or not isinstance(p.get("limit", 0), int):
        raise ValueError("ints")
    return finish(d)


def prompt(text: str, state) -> str:
    """Compact prompt: non-empty state fields, numbered last results (max 10, short titles), last 4 turns
    (bot side cut to 80 chars), the message. Sorted keys keep it cacheable."""
    st = {k: v for k in ("active_task", "query_text", "exclude", "exclude_tags", "max_steps", "have", "prefs",
                         "selected_recipe_id") if (v := getattr(state, k))}
    res = "\n".join(f"{i}. {rid} | {title[:50]}" for i, (rid, title) in enumerate(state.last_titles[:10], 1))
    hist = "\n".join(f"user: {u}\nbot: {b[:80]}" for u, b in state.history[-4:])
    parts = [f"STATE: {json.dumps(st, sort_keys=True)}" if st else "", f"LAST_RESULTS:\n{res}" if res else "",
             f"HISTORY:\n{hist}" if hist else "", f"MESSAGE: {text}"]
    return "\n".join(p for p in parts if p)


def plan(text: str, state, use_llm: bool = True, known=lambda w: True) -> tuple[dict, PlanInfo]:
    """Rule plan when it is a high-confidence pattern (no LLM call); else the LLM plan; else the rule plan
    with the reason the LLM was unavailable (no key, 429, timeout, network, invalid JSON twice).
    known(word): is it a dataset ingredient (used by the high-confidence check)."""
    rp = rule_plan(text)
    if confident(text, rp, known):
        return finish(rp), PlanInfo("rule_direct")
    fallback = rp if rp["intent"] != "clarify" else keyword_plan(text)  # unclassified -> keyword search
    if not use_llm or not llm.available():
        return finish(fallback), PlanInfo("rule", reason="LLM disabled" if not use_llm else "no GEMINI_API_KEY")
    try:
        p, calls = llm.generate_json(SYSTEM, prompt(text, state), SCHEMA, validate)
        return p, PlanInfo("llm", calls)
    except llm.LLMError as e:
        return finish(fallback), PlanInfo("rule", e.calls, str(e))
