"""LLM call #2, the "voice": a short, friendly reply written from the payload only, validated before display.

The executor's payload (counts, titles, IDs, filters, score components) is reduced to a small JSON of FACTS.
The LLM writes 2-4 sentences from it. Before display every number and recipe ID in the text must appear in
FACTS (number words like "five" too); otherwise the templated reply is shown instead. One request, 4 s cap,
cached like the planner; skipped when the planner already used both calls or the LLM is down. The structured
cards, the templated answer and the Calculation tab are unchanged: the voice text only sits above them.
"""
import json
import re

from . import llm

TIMEOUT_MS = 4000
SCHEMA = {"type": "object", "properties": {"reply": {"type": "string"}}, "required": ["reply"]}
SYSTEM = """You are the friendly voice of a recipe-database assistant. Reply to the user in 2-4 short sentences,
like a helpful person, using ONLY the FACTS JSON. Never add a number, recipe id, ingredient, cooking time,
nutrition claim or taste opinion that is not in FACTS. Refer to recipes by title. Mention active filters when
they matter and keep the meaning of any notes. With no results, say so plainly and suggest relaxing one listed
constraint. Plain sentences, no lists, no markdown."""
ID = re.compile(r"\b(?:ar|epi|fn):[A-Za-z0-9./_-]{6,}")
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}


def _cards(cards: list) -> list[dict]:
    """Top 5 cards as facts (rank, title, id, counts, score parts and chips)."""
    out = []
    for i, c in enumerate(cards[:5], 1):
        f = {"rank": i, "title": c["title"].strip(), "id": c["id"], "ingredients": c["n_ingredients"],
             "steps": c["n_steps"]}
        if "score" in c:
            f |= {"score": c["score"], "score_parts": c["parts"],
                  "matched": [x["label"] for x in c["chips"] if x["kind"] == "matched"],
                  "extra": [x["label"] for x in c["chips"] if x["kind"] == "extra"]}
        checks = [x["detail"] for x in c["chips"] if x["kind"] in ("ok", "may_contain", "violation")]
        out.append(f | ({"checks": checks} if checks else {}))
    return out


def facts(user_text: str, payload: dict, filters: str, notes: list) -> dict | None:
    """The only things the voice may say. None for answer types that keep the template (guard, help)."""
    t, f = payload["type"], {"user_said": user_text, "active_filters": filters, "notes": notes}
    if t == "search":
        return f | {"kind": "search", "fully_verified_matches": payload["total"] - payload.get("n_unverified", 0),
                    "more_matches_with_an_unverified_ingredient": payload.get("n_unverified", 0),
                    "top": _cards(payload["cards"])}
    if t == "match":
        return f | {"kind": "match", "fully_verified_eligible": payload["total"] - payload.get("n_unverified", 0),
                    "more_eligible_with_an_unverified_ingredient": payload.get("n_unverified", 0),
                    "your_ingredients": payload["have"], "no_match": not payload["total"], "top": _cards(payload["cards"]),
                    "alternatives_not_matches": [{"violates": a["violates"], "titles": [c["title"].strip() for c in
                                                  a["cards"]]} for a in payload.get("alternatives", [])]}
    if t == "stats":
        res = []
        for c in payload["calc"]:
            r = {"label": c["label"], "filters": c["filters"], "denominator_valid_recipes": c["denominator"],
                 "analyzed": c["n_analyzed"]}
            if isinstance(c["value"], (int, float)):
                r["value"] = c["value"]
                if payload["op"] in ("count", "percentage"):
                    pct = 100 * c["value"] / c["denominator"]
                    r |= {"percent": round(pct, 2), "percent_rounded": round(pct)}
            res.append(r)
        return f | {"kind": "stats", "op": payload["op"], "results": res, "top": _cards(payload["cards"]),
                    "top_ingredients": payload.get("rows", [])[:5]}
    if t == "recipe":
        return f | {"kind": "recipe", "recipe": _cards(payload["cards"])[0]}
    return None


def check(text: str, f: dict) -> str:
    """The voice text if every number / number word / recipe id in it is in FACTS; else ValueError."""
    text = " ".join(str(text).split())
    if not 10 <= len(text) <= 700:
        raise ValueError("length")
    blob = json.dumps(f)
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


def speak(user_text: str, payload: dict, filters: str, notes: list) -> tuple[str | None, list, str]:
    """(voice text or None, llm calls, status) where status says why the template was used instead."""
    f = facts(user_text, payload, filters, notes)
    if f is None:
        return None, [], "template (answer type keeps the template)"
    try:
        text, calls = llm.generate_json(SYSTEM, "FACTS: " + json.dumps(f, sort_keys=True), SCHEMA,
                                        lambda d: check(d["reply"], f), timeout_ms=TIMEOUT_MS, attempts=1,
                                        label="voice")
    except llm.LLMError as e:
        return None, e.calls, f"template ({llm.error_kind(str(e))})"
    return text, calls, "ok"
