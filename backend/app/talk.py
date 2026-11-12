"""Conversation glue that needs no LLM and states no new facts: small talk, "why this one?" (from the score
breakdown / ranking evidence of the last results), clarifying questions, and follow-up suggestion chips
generated from the current state (each one is a message the rule parser understands).
"""
import re

from .match import MatchResult
from .rules import ORDINALS
from .search import SearchResult
from .stats import Result

ORD = list(ORDINALS)
OFFTOPIC = ("I can only help with the recipes in this collection, so I'll leave that one. Try something like "
            "'find a quick pasta recipe' or 'I have eggs and spinach'.")
ASK = "Could you tell me a bit more: a dish you'd like, ingredients you have, or something you can't eat?"


def smalltalk(kind: str, valid: int) -> str:
    """Friendly fixed replies; the only number is the dataset size from the DB."""
    return {"greeting": "Hi! I can find recipes, filter them by what you can't eat, rank them by the ingredients "
                        "you have, and count things across the collection. What are you in the mood for?",
            "thanks": "You're welcome! Want me to refine those results, or look for something else?",
            "bye": "Happy cooking! Come back any time.",
            }.get(kind, f"I work only from this collection of {valid:,} valid recipes. I can find dishes "
                        "('penne pasta, no dairy'), suggest recipes for what you have ('I have eggs and rice'), "
                        "explain why a recipe ranked where it did, and answer counts and rankings ('how many "
                        "recipes are dairy-free?'), always with the calculation shown.")


def clarify(question: str) -> str:
    """The planner's one short question, if it is short, a question, and carries no numbers or ids."""
    q = " ".join(question.split())
    return q if q and len(q) <= 160 and q.endswith("?") and not re.search(r"\d|(?:ar|epi|fn):", q) else ASK


def explain(res, rid: str, query: str | None) -> str | None:
    """Why `rid` ranked where it did in the last results (match score, search ranking, or stats rank)."""
    if isinstance(res, MatchResult):
        for i, r in enumerate(res.rows + res.more, 1):
            if r.id == rid and r in res.more:
                return (f"**{r.title.strip()}** `{rid}` is #{i}, after every fully verified recipe: it has an "
                        f"ingredient I couldn't verify for your restrictions ({'; '.join(r.warnings)}). Its score is "
                        f"{r.score:.2f}.")
            if r.id == rid:
                parts = ", ".join(f"{k} {v:+.1f}" for k, v in r.parts.items())
                return (f"**{r.title.strip()}** `{rid}` is #{i} because it uses {len(r.matched)} of your "
                        f"{len(res.have)} ingredients ({', '.join(r.matched) or 'none'}), needs {len(r.extra)} more "
                        f"({', '.join(r.extra) or 'none'}) and has {r.n_steps} steps. Score {r.score:.2f} = {parts}. "
                        "Ties go to more matched, then fewer extra, fewer steps, and recipe id.")
    if isinstance(res, SearchResult):
        for i, h in enumerate(res.hits + res.more, 1):
            if h.id == rid and h in res.more:
                return (f"**{h.title.strip()}** `{rid}` is #{i}, after every fully verified match: it has an "
                        f"ingredient I couldn't verify for your restrictions ({'; '.join(h.evidence)}).")
            if h.id == rid:
                phrase = bool(query) and " ".join(query.lower().split()) in h.title.lower()
                why = ("its title contains the exact phrase, and those rank first" if phrase else
                       "it matched your words, ranked by BM25 relevance (title words count 3x)")
                checks = f" Checks: {'; '.join(h.evidence)}." if h.evidence else ""
                return (f"**{h.title.strip()}** `{rid}` is #{i} of {res.total:,} matches ({res.filters}): {why}; "
                        f"ties go to recipe id.{checks}")
    if isinstance(res, Result) and res.op == "rank":
        for i, row in enumerate(res.rows, 1):
            if row[0] == rid:
                return (f"**{row[1].strip()}** `{rid}` is #{i}: {row[2]} by the ranking field; ties go to the "
                        f"other field ({row[6]}), then recipe id. {res.method}")
    return None


def suggestions(st, payload: dict, plan: dict, conflict: tuple | None = None) -> list[dict]:
    """2-3 follow-up chips from the current state; each message is one the rule parser handles."""
    t, cards, out = payload["type"], payload.get("cards", []), []
    if conflict:  # 'vegan chicken curry': offer both ways out
        tag, word = conflict
        rest = " ".join(w for w in (st.query_text or "").split() if w != word)
        out.append((f"Drop “no {tag}”", f"{tag} {'are' if ' and ' in tag else 'is'} fine now"))
        if rest:
            out.append((f"{rest.capitalize()} without {word}", f"find a {rest} recipe"))
    elif t in ("search", "match") and cards:
        out += [("Show steps for #1", "show me the steps for the first one"), ("Why #1?", "why the first one?")]
        tag = next((x for x, tags in (("dairy", ["dairy"]), ("gluten", ["gluten"]), ("nuts", ["tree_nut", "peanut"]))
                    if not set(tags) & set(st.exclude_tags)), None)
        if t == "match" and "fewest_extra" not in st.prefs:
            out.append(("Fewer extra ingredients?", "fewest additional ingredients"))
        elif st.max_steps is None:
            out.append(("At most 5 steps?", "at most 5 steps"))
        elif tag:
            out.append((f"Also no {tag}?", f"also no {tag}"))
    elif t in ("search", "match"):  # nothing qualified: offer to relax one constraint
        for a in payload.get("alternatives", []) or [{"violates": f"no {x}", "cards": [1]} for x in st.exclude]:
            if a["cards"]:
                v = a["violates"]
                out.append((f"Drop “{v}”?", "remove the step limit" if v.startswith("at most")
                            else f"{v[3:].split(' (')[0]} is fine now"))
        if st.max_steps is not None and not payload.get("alternatives"):
            out.append(("No step limit?", "remove the step limit"))
    elif t == "stats":
        ws = plan["stats"]["all_of"]
        if cards:
            out.append(("Show steps for #1", "show me the steps for the first one"))
        if ws:
            among = f"Among recipes containing {' and '.join(ws)}"
            out += [("Fewest steps?", f"{among}, which five have the fewest steps?"),
                    ("Top ingredients?", f"{among}, what are the top 10 ingredients?")]
        else:
            out += [("Dairy-free count?", "How many recipes are dairy-free?"),
                    ("Top ingredients?", "What are the top 10 ingredients?")]
    elif t == "substitute":  # adapt anyway / next option / clear the gate / an allergy that would re-grade
        from . import normalize as nz
        from .rules import TAG_LABEL
        from .subview import _name
        p = payload["parts"][0] if payload["parts"] else None
        nxt = (st.sub or {}).get("option", 1) + 1
        gate = (payload.get("adaptation") or {}).get("gate")
        if payload["question"] or (p and not payload["adaptation"] and p["chosen"]):
            out.append(("Adapt it anyway", "adapt it anyway"))
        if p and len(p["candidates"]) >= nxt <= len(ORD):
            out.append((f"Try option {nxt}", f"use the {ORD[nxt - 1]} option instead"))
        if gate:
            out.append((f"Also remove {_name(gate[0]['what'])}", f"remove the {_name(gate[0]['what'])} too"))
        tag = next((tg for tg, lv in nz.tags_for(p["chosen"]) if lv == "contains" and tg not in st.exclude_tags),
                   None) if p and p["chosen"] else None
        if tag:
            out.append((f"Allergic to {TAG_LABEL.get(tag, tag)}?", f"I'm also allergic to {TAG_LABEL.get(tag, tag)}"))
    elif t == "recipe" and cards:
        out.append(("Why this one?", "why this one?"))
        i = st.last_results.index(cards[0]["id"]) if cards[0]["id"] in st.last_results else -1
        if 0 <= i < min(len(st.last_results), len(ORD)) - 1:
            out.append(("Next recipe", f"show me the steps for the {ORD[i + 1]} one"))
    else:
        out += [("Find a pasta recipe", "Find a penne pasta recipe"), ("Cook with what I have", "I have eggs, rice "
                "and onions"), ("Dairy-free count", "How many recipes are dairy-free?")]
    return [{"label": label, "message": msg} for label, msg in out[:3]]
