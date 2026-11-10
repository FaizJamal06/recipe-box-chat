"""Rule (regex) planner: the fallback when the LLM is unavailable (PRD 5.2). Same plan shape as the LLM.

Covers the demo conversations plus generic phrasings: "how many recipes contain X and Y", "fewest steps",
"how many recipes are dairy-free", "I have ...", "no X" / "exclude X too", "X is fine now", "the second one".
Ingredient words stay plain; the executor canonicalizes them with normalize(). Anything else -> 'clarify'.
"""
import re

NUMBERS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten".split())}
ORDINALS = {w: i for i, w in enumerate("first second third fourth fifth sixth seventh eighth ninth tenth".split(), 1)}
# words people use for a restriction -> recipe_tags tags (anything else is treated as an ingredient)
TAG_WORDS = {"dairy": ["dairy"], "milk products": ["dairy"], "lactose": ["dairy"], "eggs": ["egg"], "egg": ["egg"],
             "gluten": ["gluten"], "wheat": ["gluten"], "peanuts": ["peanut"], "peanut": ["peanut"],
             "tree nuts": ["tree_nut"], "tree nut": ["tree_nut"], "nuts": ["tree_nut", "peanut"], "meat": ["meat"],
             "pork": ["pork"], "fish": ["fish"], "shellfish": ["shellfish"], "seafood": ["fish", "shellfish"],
             "poultry": ["poultry"], "vegetarian": ["meat", "fish", "shellfish"],
             "vegan": ["meat", "fish", "shellfish", "dairy", "egg"]}
NUM = r"(\d+|" + "|".join(NUMBERS) + r")"
_SPLIT = re.compile(r"\s*(?:,|\band\b|&)\s*")
_FILLER = re.compile(r"^(?:both|the|a|an|some|any|also|my)\s+|\s+(?:in them|in it|each|too|as well|either|please)$")
_LIMIT = re.compile(r"\b(?:top|which|first|the|show|list|suggest|give|find)?\s*" + NUM + r"\b(?:\s+recipes)?")
_EXCL = re.compile(r"(?:\bno\s+(?!more\b|longer\b|less\b|than\b)|\bwithout\s+|\bcannot have\s+|\bcan'?t have\s+|"
                   r"\bcan'?t eat\s+|\ballergic to\s+|\bfree of\s+|\bexclude\s+|\bavoid\s+|\bhold the\s+)"
                   r"([a-z ,&'-]+?)(?=\.|,|\?|!|$| please| at most| and at| suggest| using)")
_FREE = re.compile(r"\b([a-z]+(?: [a-z]+)?)[- ]free\b")


def _words(s: str) -> list[str]:
    """'both garlic and onion' -> ['garlic', 'onion']; repeated so 'also eggs too' -> ['eggs']."""
    out = []
    for p in _SPLIT.split(s or ""):
        w = p.strip(" ?.!")
        while (x := _FILLER.sub("", w)) != w:
            w = x
        if w:
            out.append(w)
    return out


def _num(v: str) -> int:
    return int(v) if v.isdigit() else NUMBERS[v]


def _limit(s: str, default: int) -> int:
    m = _LIMIT.search(s)
    return _num(m.group(1)) if m else default


def _stats(op: str, **kw) -> dict:
    return {"intent": "stats", "stats": {"op": op, **kw}}


def _max_steps(t: str) -> int | None:
    """'at most six steps' -> 6, 'under 5 steps' -> 4, 'remove the step limit' -> -1 (clear)."""
    if re.search(r"\b(?:any number of steps|no step limit|remove the step limit)\b", t):
        return -1
    m = re.search(rf"\b(?:at most|no more than|max(?:imum)?(?: of)?|up to|within)\s+{NUM}\s+steps?\b", t) \
        or re.search(rf"\b{NUM}\s+steps?\s+or\s+(?:less|fewer)\b", t)
    if m:
        return _num(m.group(1))
    m = re.search(rf"\b(?:under|fewer than|less than)\s+{NUM}\s+steps?\b", t)
    return _num(m.group(1)) - 1 if m else None


def _restrictions(t: str) -> dict:
    """exclude_add / exclude_tags_add / *_remove / max_steps / prefs found anywhere in the message."""
    excl = [w for g in _EXCL.findall(t) for w in _words(g)]
    excl += [m for m in _FREE.findall(t) if m in TAG_WORDS]
    excl += [w for w in ("vegetarian", "vegan") if re.search(rf"\b{w}\b", t)]
    rem = [w for g in re.findall(r"(?:^|\b(?:actually|now)\s+)([a-z ,&'-]+?)\s+(?:is|are)\s+(?:fine|ok|okay|allowed)\b"
                                 r"|\ballow\s+([a-z ,&'-]+?)(?:\.|,|\?|!|$| again)", t) for x in g for w in _words(x)]
    prefs = [p for p, rx in (("use_most", r"as many as possible|use as many|most of (?:my|these|them)"),
                             ("fewest_extra", r"fewest (?:additional|extra|other|more|new)|least (?:additional|extra)"),
                             ("fewest_steps", r"fewest steps|quickest|simplest"),
                             ("no_staples", r"(?:no|without|don't assume|do not assume) (?:pantry )?staples"))
             if re.search(rx, t)]
    return {"exclude_add": sorted({w for w in excl if w not in TAG_WORDS}),
            "exclude_tags_add": sorted({x for w in excl if w in TAG_WORDS for x in TAG_WORDS[w]}),
            "exclude_remove": [w for w in rem if w not in TAG_WORDS],
            "exclude_tags_remove": sorted({x for w in rem if w in TAG_WORDS for x in TAG_WORDS[w]}),
            "max_steps": _max_steps(t), "prefs_add": prefs}


def target(t: str) -> dict | None:
    """'the second one' / 'number 2' -> result_index; 'this recipe' / 'that one' / 'it' -> selected."""
    m = re.search(r"\b(?:the\s+)?(" + "|".join(ORDINALS) + r"|last|\d+(?:st|nd|rd|th))\s+(?:one|recipe|result)\b", t) \
        or re.search(r"(?:\bnumber|#|\bno\.)\s*(\d+)\b", t)
    if m:
        v = m.group(1)
        return {"kind": "result_index", "value": "-1" if v == "last" else str(ORDINALS.get(v) or int(v[:-2] if
                                                                                     v[-2:].isalpha() else v))}
    if re.search(r"\b(?:this|that|the same)\s+(?:one|recipe|dish)\b|\bit\b", t):
        return {"kind": "selected", "value": ""}
    return None


def rule_plan(text: str) -> dict:
    """Plan from regexes (PRD 5.2 shape, missing keys filled by planner.finish)."""
    t = " ".join(text.lower().replace("’", "'").split())
    contain = r"(?:contain|containing|have|having|has|use|using|with|include|including)s?"
    m = re.search(r"\bi\s+(?:have|'ve got|have got|got)\s+(.+?)(?:[.?!]|$)", t)
    if m:  # T2: the have-list stops at the first restriction or request word
        items = re.split(r",?\s*\b(?:no|without|at most|suggest|exclude|but|under|using|use|what|which|can)\b", m.group(1))[0]
        r = _restrictions(t)
        return {"intent": "match", "state_patch": {"mode": "new", "have_set": _words(items), **r,
                                                   "limit": _limit(t[m.end():], 0) or None}}
    tg = target(t)
    if tg and re.search(r"\b(?:steps|instructions|ingredients|details|recipe|show|open|view|directions|method)\b", t):
        return {"intent": "recipe_detail", "target": tg}
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
    op = "percentage" if re.search(r"percent|%|share|proportion|fraction", t) else "count"
    m = re.search(r"(?:how many|percent(?:age)?|share|proportion|fraction)\b.*?\brecipes\s+(?:are|is)\s+([a-z ]+?)[- ]free\b", t)
    if m and m.group(1) in TAG_WORDS:
        return _stats(op, tags=TAG_WORDS[m.group(1)], tag_mode="free")
    m = re.search(rf"how\s+many\s+(?:of\s+the\s+)?recipes\s+(?:\w+\s+)?{contain}\s+([a-z ,&'-]+?)(?:\?|$|\.)", t) \
        or re.search(rf"(?:percent(?:age)?|share|proportion|fraction)\s+of\s+(?:all\s+)?(?:the\s+)?(?:recipes|dataset)"
                     rf"\s+(?:\w+\s+)?{contain}\s+([a-z ,&'-]+?)(?:\?|$|\.)", t)
    if m:
        words = _words(m.group(1))
        if len(words) == 1 and words[0] in TAG_WORDS:
            return _stats(op, tags=TAG_WORDS[words[0]], tag_mode="contains")
        return _stats(op, all_of=words)
    r = _restrictions(t)
    m = re.search(r"\b(?:find|show|give|search|suggest|want|need|looking for)\b(?:\s+me)?(?:\s+(?:for|a|an|some))*\s+"
                  r"([a-z ' -]+?)\s+recipes?\b", t)
    if m or any(r[k] for k in r if k != "prefs_add"):
        q = m.group(1).strip() if m else None
        if q:  # 'dairy-free pasta' -> query 'pasta' + exclude_tags dairy (already in r)
            q = " ".join(w for w in _FREE.sub(" ", q).split() if w not in ("vegetarian", "vegan")) or None
        return {"intent": "search", "state_patch": {"mode": "new" if q else "refine", "query_text": q, **r}}
    return {"intent": "clarify"}
