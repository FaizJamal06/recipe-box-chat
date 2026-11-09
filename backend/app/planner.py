"""LLM call #1 (user text -> JSON plan) with a regex rule-based fallback for when the LLM is down.

M2 ships the rule planner only; M3 adds the LLM call in front of it. Both produce the same plan shape
(PRD 5.2). The planner names ingredients in plain words; the executor canonicalizes them with normalize().
"""
import re

NUMBERS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten".split())}
# words people use for a restriction -> recipe_tags tags (anything else is treated as an ingredient)
TAG_WORDS = {"dairy": ["dairy"], "milk products": ["dairy"], "lactose": ["dairy"], "eggs": ["egg"], "egg": ["egg"],
             "gluten": ["gluten"], "wheat": ["gluten"], "peanuts": ["peanut"], "peanut": ["peanut"],
             "tree nuts": ["tree_nut"], "nuts": ["tree_nut", "peanut"], "meat": ["meat"], "pork": ["pork"],
             "fish": ["fish"], "shellfish": ["shellfish"], "seafood": ["fish", "shellfish"],
             "poultry": ["poultry"], "vegetarian": ["meat", "fish", "shellfish"]}
_SPLIT = re.compile(r"\s*(?:,|\band\b|&)\s*")
_FILLER = re.compile(r"^(?:both|the|a|an|some|any)\s+|\s+(?:in them|in it|each)$")
_LIMIT = re.compile(r"\b(?:top|which|first|the|show|list)?\s*(\d+|" + "|".join(NUMBERS) + r")\b(?:\s+recipes)?")


def _words(s: str) -> list[str]:
    """'both garlic and onion' -> ['garlic', 'onion']."""
    return [w for w in (_FILLER.sub("", p.strip(" ?.!")) for p in _SPLIT.split(s or "")) if w]


def _limit(s: str, default: int) -> int:
    m = _LIMIT.search(s)
    if not m:
        return default
    v = m.group(1)
    return int(v) if v.isdigit() else NUMBERS[v]


def _stats(op: str, **kw) -> dict:
    base = {"op": op, "field": "n_steps", "order": "asc", "limit": 5, "all_of": [], "any_of": [], "none_of": [],
            "title_contains": [], "normalization": "both"}
    return {"intent": "stats", "stats": {**base, **kw}}


def rule_plan(text: str) -> dict:
    """Plan from regexes (PRD 5.2 shape). Unknown phrasing -> intent 'clarify'."""
    t = " ".join(text.lower().split())
    contain = r"(?:contain|containing|have|having|has|use|using|with|include|including)s?"
    filt = re.search(rf"(?:among|of|for|in)\s+(?:the\s+)?recipes\s+(?:that\s+)?{contain}\s+([a-z ,&'-]+?)(?:,|\?|$|\s+which|\s+what)", t)
    all_of = _words(filt.group(1)) if filt else []
    m = re.search(r"\b(fewest|least|most|shortest|longest)\s+(?:instruction\s+)?(steps|ingredients)\b", t)
    if m:
        order = "asc" if m.group(1) in ("fewest", "least", "shortest") else "desc"
        return _stats("rank", field="n_steps" if m.group(2) == "steps" else "n_ingredients", order=order,
                      limit=_limit(t[:m.start()], 5), all_of=all_of)
    m = re.search(r"\b(average|mean|median)\s+(?:number\s+of\s+)?(steps|ingredients)\b", t)
    if m:
        op = "median" if m.group(1) == "median" else "mean"
        return _stats(op, field="n_steps" if m.group(2) == "steps" else "n_ingredients", all_of=all_of)
    m = re.search(r"\b(?:most\s+(?:common|frequent|popular|used)|top)\s+(\d+\s+|\w+\s+)?ingredients\b", t)
    if m:
        return _stats("top_ingredients", limit=_limit(m.group(0), 10), all_of=all_of)
    m = re.search(rf"how\s+many\s+(?:of\s+the\s+)?recipes\s+(?:\w+\s+)?{contain}\s+([a-z ,&'-]+?)(?:\?|$|\.)", t) \
        or re.search(rf"(?:percent(?:age)?|share|proportion|fraction)\s+of\s+(?:all\s+)?(?:the\s+)?(?:recipes|dataset)"
                     rf"\s+(?:\w+\s+)?{contain}\s+([a-z ,&'-]+?)(?:\?|$|\.)", t)
    if m:
        op = "percentage" if re.search(r"percent|%|share|proportion|fraction", t) else "count"
        return _stats(op, all_of=_words(m.group(1)))
    excl = [w for g in re.findall(r"(?:\bno|without|cannot have|can't have|can't eat|allergic to|free of)\s+"
                                  r"([a-z ,&'-]+?)(?:\.|,|\?|!|$| please)", t) for w in _words(g)]
    m = re.search(r"\b(?:find|show|give|search|suggest|want|need)\b(?:\s+me)?(?:\s+(?:for|a|an|some))*\s+"
                  r"([a-z ' -]+?)\s+recipes?\b", t)
    if m or excl:
        tags = [x for w in excl if w in TAG_WORDS for x in TAG_WORDS[w]]
        return {"intent": "search", "state_patch": {"mode": "new" if m else "refine",
                "query_text": m.group(1).strip() if m else None,
                "exclude_add": [w for w in excl if w not in TAG_WORDS], "exclude_tags_add": tags}}
    return {"intent": "clarify"}
