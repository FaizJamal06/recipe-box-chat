"""Rule parser for substitution requests (T3), used by rules.rule_plan before anything else.

"remove the eggs", "take out the butter and milk", "no eggs in this", "replace butter with oil", "substitute oil for
butter", "use oil instead of butter", "make it vegan", "isme ande nahi chahiye", "use the second option",
"adapt it anyway". Returns a plan with intent 'substitute' (restrictions in the same message go to state_patch), or
None when the message isn't about changing a recipe ("find a pasta recipe without dairy" stays a search).
"""
import re

ORD = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "other": 2, "next": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4}
HINGLISH = {"ande": "eggs", "anda": "eggs", "andey": "eggs", "anday": "eggs", "doodh": "milk", "makhan": "butter",
            "malai": "cream", "cheeni": "sugar", "pyaz": "onion", "pyaaz": "onion", "lehsun": "garlic",
            "dahi": "yogurt", "shahad": "honey", "maida": "flour", "chini": "sugar"}
_END = r"(?=\s+(?:from|in|out of|of)\s+(?:this|the|my|that|it)\b|[.?!;]|$|,|\s+(?:and\s+)?(?:use|keep|make|but|what|" \
       r"which|how|please|with)\b)"
_OPTION = re.compile(r"\b(?:use|try|go with|pick|choose|switch to)\s+(?:me\s+)?(?:the\s+)?(" + "|".join(ORD) +
                     r"|\d)\s+(?:option|one|candidate|substitute|suggestion|choice|replacement)\b")
_OPTION2 = re.compile(r"\b(" + "|".join(ORD) + r")\s+(?:option|candidate|substitute|suggestion|choice|replacement)\b")
_SWAP = re.compile(r"\b(?:replace|swap|switch)\s+(?:out\s+)?(?:the\s+)?([a-z][a-z ' -]*?)\s+(?:with|for|by)\s+"
                   r"(?:some\s+)?([a-z][a-z ' -]*?)(?=[.?!,]|$|\s+(?:in|and|but|please|instead)\b)")
_SUBFOR = re.compile(r"\b(?:substitute|sub)\s+([a-z][a-z ' -]*?)\s+for\s+(?:the\s+)?([a-z][a-z ' -]*?)(?=[.?!,]|$|\s+in\b)")
_INSTEAD = re.compile(r"\buse\s+([a-z][a-z ' -]*?)\s+instead\s+of\s+(?:the\s+)?([a-z][a-z ' -]*?)(?=[.?!,]|$|\s+in\b)")
_REMOVE = re.compile(r"\b(?:remove|take out|leave out|omit|skip|drop|get rid of|cut out|swap out|replace|substitute|"
                     r"substitue|subsitute|substitude|remvoe|repalce|replase)\s+"  # common typos
                     r"(?:the\s+|all\s+(?:the\s+)?|any\s+)?([a-z][a-z ,&' -]*?)" + _END)
_NO_IN_THIS = re.compile(r"\b(?:no|without)\s+([a-z][a-z ' -]*?)\s+(?:in|from)\s+(?:this|it|that)\b")
_MAKE = re.compile(r"\bmake\s+(?:it|this|that)(?:\s+recipe)?\s+(vegan|vegetarian|pescatarian|halal|jain|"
                   r"[a-z]+[- ]free)\b")
_HINGLISH = re.compile(r"\b(?:isme|ismein|is mein|is me)\b.*?\b([a-z]+)\s+(?:nahi|nahin|mat|na)\b")
_FORCE = re.compile(r"\badapt it anyway\b|\b(?:do it|go ahead|continue|proceed) anyway\b|^(?:yes|yeah|yep|sure|ok(?:ay)?|"
                    r"go ahead|continue|proceed|do it)\b[\s,!.]*(?:please|anyway|continue|go ahead|do it)?[\s!.]*$")
_DISH = (re.compile(r"\bthis\s+([a-z][a-z ' -]*?)\s+(?:recipe|dish)\b"),
         re.compile(r"\b(?:from|in|of)\s+(?:this|my|the|that)\s+([a-z][a-z ' -]*?)(?=\s*(?:/|[.?!,]|$|\s+(?:and|but|recipe|"
                    r"without|with|please)\b))"))
_ASKS_RECIPES = re.compile(r"^(?:which|what|find|show(?: me)?|list|are there|any|search)\b.*\brecipes\b")
_NOT_DISH = {"recipe", "one", "dish", "it", "this", "that", "dataset", "database", "pls", "plz", "please", "too",
             "thing"}


def dish_of(t: str) -> str | None:
    for rx in _DISH:
        m = rx.search(t)
        if m and m.group(1).strip() not in _NOT_DISH:
            return m.group(1).strip()
    return None


def parse(t: str) -> dict | None:
    """Substitution plan for a lower-cased message, or None."""
    from .rules import DIETS, TAG_WORDS, _restrictions, _words  # rules imports this module lazily
    if _ASKS_RECIPES.search(t):  # 'which banana breads use applesauce instead of eggs?' is a search, not an edit
        return None
    sub = {"remove": [], "replace_with": "", "dish": dish_of(t) or "", "remove_tags": [], "option": 0, "force": False,
           "dataset_only": not re.search(r"\b(?:outside|beyond|not only|any) (?:the )?(?:dataset|database)\b|"
                                         r"\bexternal\b", t)}
    if m := (_OPTION.search(t) or _OPTION2.search(t)):
        sub["option"] = int(m.group(1)) if m.group(1).isdigit() else ORD[m.group(1)]
    elif _FORCE.search(t):
        sub["force"] = True
    elif m := (_SWAP.search(t) or _SUBFOR.search(t) or _INSTEAD.search(t)):
        old, new = (m.group(2), m.group(1)) if m.re is not _SWAP else (m.group(1), m.group(2))
        sub["remove"], sub["replace_with"] = _words(old), new.strip()
    elif m := _MAKE.search(t):
        word = m.group(1).replace(" free", "-free")
        tags = DIETS[word]["tags"] if word in DIETS else TAG_WORDS.get(word.split("-")[0], [])
        if not tags:
            return None
        sub["remove_tags"] = list(tags)
    elif m := (_REMOVE.search(t) or _NO_IN_THIS.search(t)):
        sub["remove"] = [w for w in _words(m.group(1)) if w not in _NOT_DISH]
    elif (m := _HINGLISH.search(t)) and m.group(1) in HINGLISH:
        sub["remove"] = [HINGLISH[m.group(1)]]
    else:
        return None
    if sub["dish"] and sub["remove"]:  # 'remove eggs from this banana bread': the dish isn't an ingredient
        sub["remove"] = [w for w in sub["remove"] if w != sub["dish"]]
    patch = _restrictions(t)  # 'without dairy' is about the person; 'no eggs in this' is about the recipe
    patch["exclude_add"] = [w for w in patch["exclude_add"] if not any(r in w for r in sub["remove"])]
    if sub["remove_tags"]:
        patch["exclude_tags_add"] = sorted(set(patch["exclude_tags_add"]) | set(sub["remove_tags"]))
    return {"intent": "substitute", "substitution": sub, "state_patch": patch}
