"""Rule (regex) planner: the fallback when the LLM is unavailable (PRD 5.2). Same plan shape as the LLM.

Covers the demo conversations plus generic phrasings: "how many recipes contain X and Y", "fewest steps",
"how many recipes are dairy-free", "I have ...", "no X" / "exclude X too", "X is fine now", "the second one".
Ingredient words stay plain; the executor canonicalizes them with normalize(). Anything else -> 'clarify'.
"""
import re
from pathlib import Path

import yaml

NUMBERS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten".split())}
ORDINALS = {w: i for i, w in enumerate("first second third fourth fifth sixth seventh eighth ninth tenth".split(), 1)}
# words people use for a restriction -> recipe_tags tags (anything else is treated as an ingredient)
TAG_WORDS = {"dairy": ["dairy"], "milk products": ["dairy"], "eggs": ["egg"], "egg": ["egg"], "gluten": ["gluten"],
             "peanuts": ["peanut"], "peanut": ["peanut"], "tree nuts": ["tree_nut"], "tree nut": ["tree_nut"],
             "meat": ["meat"], "pork": ["pork"], "fish": ["fish"], "shellfish": ["shellfish"],
             "seafood": ["fish", "shellfish"], "poultry": ["poultry"], "soy": ["soy"], "soya": ["soy"],
             "sesame": ["sesame"], "honey": ["honey"], "gelatin": ["gelatin"], "gelatine": ["gelatin"],
             "alcohol": ["alcohol"], "booze": ["alcohol"], "root vegetables": ["root_veg"]}
TAG_LABEL = {"tree_nut": "tree nuts", "root_veg": "onion, garlic or root vegetables", "egg": "eggs"}
# diet / allergy presets (lexicon/diets.yaml): compositions of tags, shown as one chip with their expansion
DIETS = yaml.safe_load((Path(__file__).resolve().parent / "lexicon" / "diets.yaml").read_text(encoding="utf-8"))
for _name, _d in DIETS.items():
    for _w in [*_d.get("say", []), *_d.get("after_no", [])]:
        TAG_WORDS.setdefault(_w, list(_d["tags"]))
_SAY = {w: n for n, d in DIETS.items() for w in d.get("say", [])}
_AFTER = {w: n for n, d in DIETS.items() for w in d.get("after_no", [])}
_DIET_SAY = re.compile(r"\b(" + "|".join(sorted(map(re.escape, _SAY), key=len, reverse=True)) + r")\b(?![- ]salt)")
NUM = r"(\d+|" + "|".join(NUMBERS) + r")"
_SPLIT = re.compile(r"\s*(?:,|\band\b|&)\s*")
_FILLER = re.compile(r"^(?:both|the|a|an|some|any|also|my)\s+|"
                     r"\s+(?:in them|in it|each|too|as well|either|please|pls|plz|thanks|thx|tho|though)$")
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


_ALLERGY = re.compile(r"\b([a-z]+(?: [a-z]+)?)[- ](?:allergy|allergies|intolerance|intolerant|sensitivity)\b")
_ALIAS = {"milk": "dairy", "nut": "nuts", "tree nut": "tree nuts", "shell fish": "shellfish"}


def _allergies(t: str) -> list[str]:
    """'I have a wheat allergy' -> ['wheat'], 'lactose intolerant' -> ['lactose'], 'celiac' -> ['gluten']."""
    out = [re.sub(r"^(?:a|an|my|the|bad|severe|mild|serious)\s+", "", w) for w in _ALLERGY.findall(t)]
    out = [_ALIAS.get(w, w) for w in out]
    return out + (["gluten"] if re.search(r"\b(?:celiac|coeliac)\b", t) else [])


def diets_in(t: str, excl: list[str] | None = None) -> list[str]:
    """Diet / allergy presets a message names: 'I'm vegan' -> ['vegan'], 'no nuts' -> ['nut allergy'],
    'allergic to wheat' -> ['celiac / wheat']. 'kosher salt' is an ingredient, not a diet."""
    t = " ".join(t.lower().replace("’", "'").split())
    if excl is None:
        excl = [_ALIAS.get(w, w) for g in _EXCL.findall(t) for w in _words(g)] + _allergies(t) + _FREE.findall(t)
    found = [_SAY[m] for m in _DIET_SAY.findall(t)] + [_AFTER[w] for w in excl if w in _AFTER]
    return list(dict.fromkeys(found))


def _restrictions(t: str) -> dict:
    """exclude_add / exclude_tags_add / *_remove / max_steps / prefs found anywhere in the message."""
    excl = [w for g in _EXCL.findall(t) for w in _words(g)] + _allergies(t)
    excl = [_ALIAS.get(w, w) for w in excl]
    excl += [m for m in _FREE.findall(t) if m in TAG_WORDS]
    rem =[w for g in re.findall(r"(?:^|\b(?:actually|now)\s+)([a-z ,&'-]+?)\s+(?:is|are)\s+(?:fine|ok|okay|allowed)\b"
                                 r"|\ballow\s+([a-z ,&'-]+?)(?:\.|,|\?|!|$| again)", t) for x in g for w in _words(x)]
    prefs = [p for p, rx in (("use_most", r"as many as possible|use as many|most of (?:my|these|them)"),
                             ("fewest_extra", r"fewest (?:additional|extra|other|more|new)|least (?:additional|extra)|"
                                              r"(?:fewer|less) (?:additional |extra )?ingredients"),
                             ("fewest_steps", r"fewest steps|quickest|simplest"),
                             ("no_staples", r"(?:no|without|don't assume|do not assume) (?:pantry )?staples"))
             if re.search(rx, t)]
    diets = [n for n in diets_in(t, excl)  # 'vegan is fine now' removes the preset, never re-adds it
             if not set(rem) & {*DIETS[n].get("say", []), *DIETS[n].get("after_no", [])}]
    rm_tags = {x for w in rem if w in TAG_WORDS for x in TAG_WORDS[w]}
    return {"exclude_add": sorted({w for w in excl if w not in TAG_WORDS}),
            "exclude_tags_add": sorted(({x for w in excl if w in TAG_WORDS for x in TAG_WORDS[w]}
                                        | {x for n in diets for x in DIETS[n]["tags"]}) - rm_tags),
            "diets_add": diets, "exclude_remove": [w for w in rem if w not in TAG_WORDS],
            "exclude_tags_remove": sorted(rm_tags),
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


def confident(text: str, plan: dict, known=lambda w: True) -> bool:
    """Rule plans trusted without asking the LLM (the faster, deterministic path):
    a have-list ('I have ...'); 'the Nth one' with a detail word; a short message (<= 8 words, no question)
    that only adds/removes restrictions ('I cannot have dairy', 'also no garlic', 'exclude eggs too',
    'dairy is fine now', 'at most 1 step') whose words are all tags or known ingredients (`known`)."""
    intent = plan.get("intent")
    if intent in ("match", "smalltalk", "explain") or (intent == "clarify" and plan.get("question")):
        return True
    if intent == "recipe_detail":
        return plan["target"]["kind"] == "result_index"
    p = plan.get("state_patch") or {}
    if intent != "search" or p.get("query_text") or "?" in text:
        return False
    words = p.get("exclude_add", []) + p.get("exclude_remove", [])
    return len(re.findall(r"[a-z']+", text.lower())) <= 8 and all(known(w) for w in words)


_TALK = (("greeting", r"^(?:hi+|hello+|hey+|hiya|yo|namaste|hola|good (?:morning|afternoon|evening))\b[\s!.,?a-z']{0,22}$"),
         ("thanks", r"^(?:ok(?:ay)?,? )?(?:thanks|thank you|thank u|thx|ty|cheers|awesome|perfect|great|nice|cool)\b.{0,25}$"),
         ("bye", r"^(?:bye|goodbye|see you|good night|cya)\b"),
         ("capabilities", r"\bw(?:h)?at (?:can|cn) (?:you|u) do|what do (?:you|u) do|how do(?:es)? (?:this|you|u) work|"
                          r"who are (?:you|u)|what are (?:you|u)\b|^help\b"))
_FOODISH = re.compile(r"recipe|find|show|cook|make|have|how many|ingredient|dish|food|eat|meal|step")
STOP = set("a an the and or of for to in on with without me my i im i'm you u your please pls plz some any recipe "
           "recipes dish dishes food make cook cooking want need give show find get something anything can could "
           "would like ki koi batao hai ka ke ko mujhe chahiye what whats how which is are do does there that this it "
           "good nice best also too either just really dinner lunch breakfast tonight today meal meals quick easy "
           "fast simple ideas idea suggest suggestion steps step most least have has got had fewer more less "
           "ingredient ingredients intolerant intolerance allergic allergy allergies diet please".split())
_DIET = re.compile(r"\b(?:vegan|vegetarian|[a-z]+[- ]free|no [a-z]+|without [a-z]+|allergic to [a-z ]+|"
                   r"[a-z]+ allerg(?:y|ies)|at most \w+ steps?)\b")
_REF = re.compile(r"^(?:(?:show|open|give)(?: me)? )?(?:the )?(" + "|".join(ORDINALS) + r"|last|\d+(?:st|nd|rd|th))"
                  r" (?:one|recipe|result)[.!?]*$")


def leftover(t: str) -> str:
    """Dish words left after removing restriction phrases and filler: 'vegan chicken curry' -> 'chicken curry',
    'I cannot have dairy' / 'dairy is fine now' -> ''."""
    t = _DIET_SAY.sub(" ", _EXCL.sub(" ", t))
    t = re.sub(r"[a-z ,&'-]+?\s+(?:is|are)\s+(?:fine|ok|okay|allowed)\b.*|\ballow\s+.*", " ", t)
    t = re.sub(r"as many as possible|use as many|fewest \w+|least \w+|(?:no|without) (?:pantry )?staples", " ", t)
    return " ".join(w for w in re.findall(r"[a-z]+", _DIET.sub(" ", t))
                    if w not in STOP and w not in TAG_WORDS and len(w) > 2 and w not in ("cannot", "cant"))


def keyword_plan(text: str) -> dict:
    """Last resort when the LLM is unavailable and no pattern matched: a keyword search on title + ingredients
    ('paneer ki koi recipe batao' -> 'paneer'). Flagged so the reply says it ran as a keyword search."""
    words = [w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2][:4]
    return {"intent": "search", "keyword": True, "state_patch": {"mode": "new", "query_text": " ".join(words)}} \
        if words else {"intent": "clarify"}


def rule_plan(text: str) -> dict:
    """Plan from regexes (PRD 5.2 shape, missing keys filled by planner.finish)."""
    t = " ".join(text.lower().replace("’", "'").split())
    contain = r"(?:contain|containing|have|having|has|use|using|with|include|including)s?"
    for kind, rx in _TALK:
        if re.search(rx, t) and (kind == "capabilities" or not _FOODISH.search(t)):
            return {"intent": "smalltalk", "talk": kind}
    if _REF.match(t):  # 'the second one' on its own
        return {"intent": "recipe_detail", "target": target(t)}
    if re.search(r"\b(?:quick|fast|easy|simple|speedy)\b", t) and not leftover(t) and "i have" not in t:
        return {"intent": "clarify", "question": "There's no cook-time field, but I can keep it short: want recipes "
                                                 "with at most four steps, or do you have a dish in mind?"}
    if re.search(r"^(?:and |so |but |ok |okay )?why\b", t) and \
            re.search(r"\b(?:this|that|it|one|pick|picked|chose|choose|chosen|rank|ranked|top|first|second|third|"
                      r"number|#\d|recommend|suggest)", t):
        return {"intent": "explain", "target": target(t) or {"kind": "none", "value": ""}}
    m = re.search(r"\bi\s+(?:have|'ve got|have got|got)\s+(.+?)(?:[.?!]|$)", t)
    if m and re.search(r"allerg|intoleran|celiac|coeliac|sensitiv", m.group(1)):
        m = None  # 'I have a wheat allergy' is a restriction, not a pantry
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
        yes, *nos = re.split(r"\s+(?:but\s+)?(?:no|not|without|excluding)\s+", m.group(1))  # 'garlic but no onion'
        words, none_of = _words(yes), [w for x in nos for w in _words(x)]
        if len(words) == 1 and words[0] in TAG_WORDS and not none_of:
            return _stats(op, tags=TAG_WORDS[words[0]], tag_mode="contains")
        return _stats(op, all_of=words, none_of=none_of)
    r = _restrictions(t)
    m = re.search(r"\b(?:find|show|give|search|suggest|want|need|looking for)\b(?:\s+me)?(?:\s+(?:for|a|an|some))*\s+"
                  r"([a-z ' -]+?)\s+recipes?\b", t)
    if m or any(r.values()):  # a dish request, or restrictions (+ dish words: 'gluten free pasta recipes')
        q = m.group(1).strip() if m else (leftover(t) or None)
        if q:  # 'dairy-free pasta' -> query 'pasta' + exclude_tags dairy (already in r)
            q = " ".join(w for w in _FREE.sub(" ", q).split() if w not in ("vegetarian", "vegan")) or None
        fresh = not q and bool(re.search(r"\b(?:something|anything|ideas?|suggest|recommend)\b", t))
        return {"intent": "search", "state_patch": {"mode": "new" if q or fresh else "refine", "query_text": q,
                                                    "reset": fresh, **r}}
    return {"intent": "clarify"}
