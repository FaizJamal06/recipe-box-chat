"""Merge a plan's state_patch into the sticky state (PRD 5.1). Split from session.py to keep both small.

Person-level restrictions (excluded ingredients and tags, diet presets, strict mode) persist across tasks until the
user drops them ('dairy is fine now', 'I'm not vegan anymore'); 'just no peanuts' replaces them all. Request-level
constraints (dish, include, max_steps, have-list, prefs, limit) belong to one request: a new dish or task clears
them, says so, and keeps a copy for the 'Restore previous filters' chip. Diet and allergy words inside a dish query
are filters, not search words ('vegetarian biryani' -> 'biryani' + the vegetarian preset).
"""
from . import normalize as nz
from .rules import DIETS, TAG_LABEL, TAG_WORDS, diets_in, dish_filters, only

REQUEST = ("include", "max_steps", "have", "prefs", "limit")


def key(w: str) -> tuple:
    return tuple(nz.normalize(w))


def _request(s) -> list[str]:
    """The request-level constraints in words ('at most 5 steps', 'have: eggs, rice')."""
    return ([f"must include {', '.join(s.include)}"] if s.include else []) + \
        ([f"at most {s.max_steps} steps"] if s.max_steps is not None else []) + \
        ([f"have: {', '.join(s.have)}"] if s.have else []) + ([f"prefs: {', '.join(s.prefs)}"] if s.prefs else [])


def _switch(s, d: dict) -> list[str]:
    """A new dish or task: clear the request-level constraints (kept in prev_request for 'restore'), keep the
    restrictions, and say both."""
    notes, gone = [], _request(s)
    if gone:
        s.prev_request, s.offer_restore = {k: getattr(s, k) for k in REQUEST} | {"task": s.active_task}, True
        notes.append(f"New request, so I cleared {'; '.join(gone)}. Say 'restore previous filters' to bring "
                     f"{'it' if len(gone) == 1 else 'them'} back.")
    kept = s.restrictions()
    if kept and (gone or not s.kept_note):
        notes.append(f"Kept your restrictions ({', '.join(kept)}): they're about you, not the dish. Say e.g. "
                     "'dairy is fine now' to drop one.")
        s.kept_note = True
    s.query_text, s.include, s.query_any, s.query_label, s.selected_recipe_id = None, [], [], None, None
    s.max_steps, s.have, s.prefs, s.limit = None, [], [], None
    return notes


def restore(s) -> list[str]:
    """Bring back the request-level constraints the last task switch cleared (have/prefs only for the same task)."""
    prev = s.prev_request
    if not prev:
        return ["There are no earlier filters to restore."]
    s.include, s.max_steps = list(prev["include"]), prev["max_steps"]
    if prev["task"] == s.active_task:
        s.have, s.prefs, s.limit = list(prev["have"]), list(prev["prefs"]), prev["limit"]
    s.prev_request = None
    return [f"Restored: {'; '.join(_request(s)) or 'nothing to restore for this task'}."]


def apply(ses, d: dict, text: str = "") -> list[str]:
    """Merge one state_patch; returns notes for the reply. Diet presets named in the plan or the text
    (rules.diets_in) add their tags, and the reply states each expansion once."""
    s, notes, was = ses.state, [], []
    if d["query_text"]:  # 'vegetarian biryani' -> 'biryani' + vegetarian; 'eggless banana bread' -> no eggs
        q, presets, words = dish_filters(d["query_text"])
        d["query_text"], d["diets_add"] = q, list(dict.fromkeys(d["diets_add"] + presets))
        d["exclude_add"] += [w for w in words if w not in d["exclude_add"]]
        if not q and not d["have_set"] and not d.get("reset"):
            d["mode"] = "refine"
    if d["mode"] == "new" and (d["have_set"] or d.get("reset") or d["query_text"] and d["query_text"] != s.query_text):
        notes += _switch(s, d)
    if d.get("only") or only(text.lower()):  # 'just no peanuts': the new restrictions replace every earlier one
        was, s.exclude, s.exclude_tags, s.diets = s.restrictions(), [], [], []
    if d["query_text"]:
        s.query_text = d["query_text"]
    for k in ("exclude_add", "include_add"):  # executor-side check of the planner's words
        for w in [w for w in d[k] if w.lower() not in TAG_WORDS]:
            if not key(w):
                notes.append(f"I couldn't read '{w}' as an ingredient, so that restriction was NOT added.")
                d[k] = [x for x in d[k] if x != w]
            elif key(w)[0] not in ses.ds.vocab:
                notes.append(f"'{w}' isn't a known ingredient name here; the restriction matches that exact name only.")
    tags = d["exclude_tags_add"] + [t for w in d["exclude_add"] if w.lower() in TAG_WORDS for t in TAG_WORDS[w.lower()]]
    s.exclude += [w for w in d["exclude_add"] if w.lower() not in TAG_WORDS and key(w) not in map(key, s.exclude)]
    s.include += [w for w in d["include_add"] if key(w) not in map(key, s.include)]
    s.exclude_tags += [t for t in tags if t not in s.exclude_tags]
    gone = set(map(key, d["exclude_remove"]))
    rm_diets = [n for n in d.get("diets_remove", []) if n in DIETS]
    still = {t for n in s.diets if n not in rm_diets for t in DIETS[n]["tags"]}  # another preset still needs these
    rm_tags = set(d["exclude_tags_remove"]) | {t for w in d["exclude_remove"] if w.lower() in TAG_WORDS
                                               for t in TAG_WORDS[w.lower()]}
    rm_tags = (rm_tags | {t for n in rm_diets for t in DIETS[n]["tags"]}) - set(tags) - (still if rm_diets else set())
    removed = [n for n in s.diets if n in rm_diets] + [x for x in s.exclude if key(x) in gone] + \
              [TAG_LABEL.get(t, t) for t in s.exclude_tags if t in rm_tags and not any(
                  t in DIETS[n]["tags"] for n in rm_diets)]
    s.exclude = [x for x in s.exclude if key(x) not in gone]
    s.exclude_tags = [t for t in s.exclude_tags if t not in rm_tags]
    s.diets = [n for n in s.diets if n not in rm_diets]
    if removed:
        notes.append(f"Removed restriction(s): {', '.join(removed)}.")
    for name in dict.fromkeys([*d.get("diets_add", []), *diets_in(text)]):
        tags = DIETS[name]["tags"]
        if set(tags) & rm_tags or name in rm_diets:  # 'vegan is fine now'
            continue
        s.exclude_tags += [t for t in tags if t not in s.exclude_tags]
        if name not in s.diets:
            notes.append(f"{name[0].upper() + name[1:]} → " + (f"no {', '.join(TAG_LABEL.get(t, t) for t in tags)}."
                         if tags else "no filter.") + (f" {DIETS[name]['note']}" if DIETS[name].get("note") else ""))
            s.diets += [name] if tags else []
    s.diets = [n for n in s.diets if set(DIETS[n]["tags"]) <= set(s.exclude_tags)]  # a removed tag ends the preset
    if (d.get("only") or only(text.lower())) and was:
        notes.append(f"Your restrictions are now: {', '.join(s.restrictions()) or 'none'} (replacing {', '.join(was)}).")
    if d["max_steps"]:
        s.max_steps = None if d["max_steps"] < 0 else d["max_steps"]
    if d["have_set"]:
        s.have, s.prefs, s.limit = list(d["have_set"]), [], None
    s.prefs += [x for x in d["prefs_add"] if x not in s.prefs]
    if d["limit"]:
        s.limit = d["limit"]
    return notes
