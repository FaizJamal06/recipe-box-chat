"""LLM call #2, the "voice": a short, friendly reply written from the payload only, validated before display.

The executor's payload and the session's restrictions become a plain-English FACTS block (no internal keys, field
names, tag codes or ids). The LLM writes 2-4 sentences from it. Before display (check()): every number and number word
in the text must appear in FACTS, every recipe id too, and no internal token may appear ("dish set to", "active
filter", "may_contain", "unverified", underscores, raw tag names, key=value); otherwise the templated reply is shown
instead. One request, 4 s cap, cached like the planner; skipped when the turn's LLM budget is used or the LLM is down.
The cards, the templated answer and the Calculation tab are unchanged: the voice text only sits above them.
"""
import json
import re

from . import llm

TIMEOUT_MS = 4000
SCHEMA = {"type": "object", "properties": {"reply": {"type": "string"}}, "required": ["reply"]}
SYSTEM = """You are the friendly voice of a recipe-database assistant. Reply to the user in 2-4 short sentences,
like a helpful person, using ONLY the FACTS. Never add a number, recipe id, ingredient, cooking time, nutrition
claim or taste opinion that is not in FACTS. Refer to recipes by title. Mention their restrictions when they matter
and keep the meaning of what they were already told. With no results, say so plainly and suggest relaxing one
listed constraint. Plain everyday sentences: no lists, no markdown, no technical or database words."""
ID = re.compile(r"\b(?:ar|epi|fn):[A-Za-z0-9./_-]{6,}")
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
# words a person would never say: state labels, field names, tag codes (the leak this guards against: "With the
# active filter dish set to penne pasta ...")
INTERNAL = re.compile(r"dish set to|active filters?|may_contain|unverified|tree_nut|root_veg|_|\b[a-z]+\s*=\s*\S",
                      re.I)  # underscores also catch query_text, exclude_tags and every other field name
TAGS = {"tree_nut": "tree nuts", "root_veg": "onion, garlic or root vegetables", "may_contain": "may contain"}
MODE = {"strict": "counting only the ingredient itself", "broad": "also counting processed forms like powders"}


def plain_filters(f: str) -> str:
    """Executor filter string -> words: 'contains garlic AND contains onion' -> 'recipes that contain garlic and onion'."""
    if f in ("", "all valid recipes"):
        return "all recipes"
    if f.endswith("recipes"):
        return f
    f = f.replace(" AND contains ", " and ").replace(" AND no ", " but no ").replace(" AND ", " and ")
    f = re.sub(r"^contains ", "contain ", f).replace("title contains", "have a title containing")
    return f"recipes {'with' if f.startswith('no ') else 'that'} {f}"


def _words(s: str) -> str:
    """Tag codes and leftover underscores in evidence lines -> words ('no tree_nut: ...' -> 'no tree nuts: ...')."""
    for code, word in TAGS.items():
        s = s.replace(code, word)
    return s.replace("_", " ")


def _cards(cards: list) -> list[str]:
    """Top 5 recipes as sentences: title, counts, what they use and need, the restriction checks."""
    out = []
    for i, c in enumerate(cards[:5], 1):
        line = f"{i}. {c['title'].strip()}: {c['n_ingredients']} ingredients, {c['n_steps']} steps"
        if "score" in c:
            used = [x["label"] for x in c["chips"] if x["kind"] == "matched"]
            extra = [x["label"] for x in c["chips"] if x["kind"] == "extra"]
            line += f"; uses {', '.join(used) or 'none of theirs'}; also needs {', '.join(extra) or 'nothing else'}"
        checks = [_words(x["detail"]) for x in c["chips"] if x["kind"] in ("ok", "may_contain", "violation")]
        out.append(line + (f" (checks: {'; '.join(checks)})" if checks else ""))
    return out


def facts(user_text: str, payload: dict, st, notes: list) -> str | None:
    """The only things the voice may say, as plain English lines. None for answer types that keep the template."""
    t = payload["type"]
    if t not in ("search", "match", "stats", "recipe"):
        return None
    r = st.restrictions() + ([f"at most {st.max_steps} steps"] if st.max_steps is not None else [])
    lines = [f'The user said: "{user_text}"', f"Their restrictions: {', '.join(r) or 'none'}"]
    lines += [f"The dish they asked for: {st.query_text or st.query_label}"] if st.query_text or st.query_label else []
    lines += [f"Already told them: {_words(n)}" for n in notes]
    n_unv = payload.get("n_unverified", 0)
    more = (f" {n_unv} more also match but have an ingredient that couldn't be checked against their restrictions; "
            "those are listed after the others." if n_unv else "")
    if t == "search":
        lines.append(f"Result: {payload['total'] - n_unv} recipes match and pass every restriction.{more}")
    elif t == "match":
        lines.append(f"Their ingredients: {', '.join(payload['have'])}")
        lines += [f"Not used: {d['item']}, because '{_words(d['why'])}' excludes it" for d in payload.get("dropped", [])]
        if not payload["total"]:
            lines.append("Result: no recipe meets every constraint.")
            lines += [f"Closest alternative, NOT a match, breaks '{_words(a['violates'])}': "
                      f"{', '.join(c['title'].strip() for c in a['cards']) or 'none'}" for a in payload.get("alternatives", [])]
        else:
            lines.append(f"Result: {payload['total'] - n_unv} recipes use some of their ingredients and pass every "
                         f"restriction.{more}")
    elif t == "stats":
        for c in payload["calc"]:
            what = plain_filters(c["filters"])
            if isinstance(c["value"], (int, float)) and payload["op"] in ("count", "percentage"):
                pct = 100 * c["value"] / c["denominator"]
                lines.append(f"{what[0].upper() + what[1:]}: {c['value']} of {c['denominator']} recipes ({pct:.2f}%, "
                             f"about {round(pct)}%)" + (f", {MODE[c['label']]}" if c["label"] in MODE else ""))
            elif isinstance(c["value"], (int, float)):
                lines.append(f"The {c['label']} is {c['value']}, over {c['n_analyzed']} {what}.")
            else:
                lines.append(f"Ranked {c['n_analyzed']} {what}; the top ones are listed below.")
        lines += [f"{x['name']}: in {x['recipes']} recipes" for x in payload.get("rows", [])[:5]]
    lines += ["Top recipes:", *_cards(payload["cards"])] if payload["cards"] and t != "recipe" else []
    lines += [f"The recipe they opened: {_cards(payload['cards'])[0][3:]}"] if t == "recipe" else []
    return "\n".join(lines)


def check(text: str, f: dict | str) -> str:
    """The voice text if every number / number word / recipe id in it is in FACTS and it has no internal token;
    else ValueError (the caller shows the template)."""
    text = " ".join(str(text).split())
    if not 10 <= len(text) <= 700:
        raise ValueError("length")
    if m := INTERNAL.search(ID.sub(" ", text)):  # ids may contain '_': mask them first
        raise ValueError(f"internal token {m.group(0)!r}")
    blob = f if isinstance(f, str) else json.dumps(f)
    nums = {n.replace(",", "") for n in NUM.findall(ID.sub(" ", blob))}  # ids contain digits: mask them
    nums |= {str(round(float(n))) for n in nums}
    for n in NUM.findall(ID.sub(" ", text)):
        if n.replace(",", "") not in nums:
            raise ValueError(f"number {n} not in facts")
    for w in re.findall(r"[a-z]+", text.lower()):
        if w in WORDS and w != "one" and str(WORDS[w]) not in nums:  # 'one' is mostly a pronoun
            raise ValueError(f"number word {w} not in facts")
    ids = set(ID.findall(blob))
    for i in ID.findall(text):
        if i not in ids:
            raise ValueError(f"id {i} not in facts")
    return text


def speak(user_text: str, payload: dict, st, notes: list) -> tuple[str | None, list, str]:
    """(voice text or None, llm calls, status) where status says why the template was used instead."""
    f = facts(user_text, payload, st, notes)
    if f is None:
        return None, [], "template (answer type keeps the template)"
    try:
        text, calls = llm.generate_json(SYSTEM, "FACTS:\n" + f, SCHEMA, lambda d: check(d["reply"], f),
                                        timeout_ms=TIMEOUT_MS, attempts=1, label="voice")
    except llm.LLMError as e:
        return None, e.calls, f"template ({llm.error_kind(str(e))})"
    return text, calls, "ok"
