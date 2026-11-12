"""The adapted recipe for a substitution (PRD 6.4 steps 8-10).

Ingredients: a deterministic diff (remove the affected lines, keep the other items of a compound line, add one line
per substitute with an observed median amount or a labelled estimate scaled to the removed amount). Steps: one LLM
call (12 s cap) returns JSON {steps: [{n, text, changed, reason}], predicted_effects, roles}; the validator demands
that unchanged steps are byte-identical, changed steps are marked, no step still mentions a removed item, the
substitute appears wherever the removed item was, and no ingredient appears that isn't in the adapted list. If the
call fails or the output is invalid: a deterministic fallback that swaps the mentions. Final gate: the adapted ingredient list is checked against every active restriction with
safety.py; anything that contains, may contain or can't be verified is listed and the result is not called safe.
Effects: "Verified from dataset" (counts, ids, ratios, deterministic) and "Predicted (not verifiable from recipe
text)" (LLM, run through the voice validator: no number or recipe id that isn't in the facts).
"""
import json
import re
import sqlite3
from dataclasses import dataclass, field

from . import amounts, llm, safety, voice
from . import normalize as nz
from .evidence import fmt_lift
from .search import SAFE

STAPLE_WORDS = {"salt", "water", "pepper", "black", "ice"}
SYSTEM = """You adapt a recipe's method after an ingredient substitution. Return JSON with:
steps: every original step, same n. Copy a step's text exactly and set changed=false unless the substitution
affects it; then rewrite only what is needed, set changed=true and give a short reason. Never mention a removed
ingredient. Mention the substitute wherever the removed ingredient was. Never add an ingredient that is not in
INGREDIENTS. predicted_effects: 2-3 plain sentences on how taste, texture or preparation may change, from the roles
and FACTS only (do not invent numbers or recipe ids). roles: what the removed ingredient did in this dish (short
words), only if ROLES says "unknown", else []."""
I, S, B = {"type": "integer"}, {"type": "string"}, {"type": "boolean"}
SCHEMA = {"type": "object", "properties": {
    "steps": {"type": "array", "items": {"type": "object", "properties": {"n": I, "text": S, "changed": B, "reason": S},
                                         "required": ["n", "text", "changed", "reason"]}},
    "predicted_effects": S, "roles": {"type": "array", "items": S}}, "required": ["steps", "predicted_effects", "roles"]}
ALLERGY_LINE = ("Allergy note: recipe text can't establish medical safety. Check every label for the allergen and for "
                "cross-contamination.")


@dataclass
class Adaptation:
    ingredients: list  # [{"op": keep | remove | add, "text": ...}]
    steps: list  # [{"n", "old", "text", "changed", "reason"}]
    prep: list = field(default_factory=list)
    source: str = "fallback"  # "model" when the LLM rewrite passed the validator
    gate: list = field(default_factory=list)  # [(line or substitute, reason)] that fail a restriction
    verified: list = field(default_factory=list)
    predicted: str | None = None
    predicted_status: str = ""
    safety_line: str | None = None
    caveat: str = ""
    model_roles: list = field(default_factory=list)
    calls: list = field(default_factory=list)  # llm.Call per request, for the turn's trace


def removed_rx(words: list[str]) -> re.Pattern:
    """Whole-word regex for the removed items and their plurals ('egg' -> egg, eggs; 'egg white' -> egg whites)."""
    alts = sorted({re.escape(w.lower()).replace(r"\ ", r"\s+") for w in words if w}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(alts) + r")(?:e?s)?\b", re.I)


def _mask(text: str) -> str:
    """Hide phrases that contain a removed word but are something else ('cream of tartar')."""
    for phrases in SAFE.values():
        for ph in phrases:
            text = re.sub(re.escape(ph), " ", text, flags=re.I)
    return text


def _ngrams(text: str) -> set[str]:
    w = re.findall(r"[a-z]+(?:-[a-z]+)?", text.lower())
    return {" ".join(w[i:i + n]) for n in (1, 2, 3) for i in range(len(w) - n + 1)}


def validate_steps(orig: list[str], new: list[dict], rx: re.Pattern, subs: list[str], allowed: set,
                   vocab) -> list[dict]:
    """The LLM's steps if they pass every rule (see module doc); ValueError naming the first failure otherwise."""
    if sorted(s["n"] for s in new) != list(range(1, len(orig) + 1)):
        raise ValueError("steps must keep the original numbering")
    sub_rx = re.compile(r"\b(?:" + "|".join(re.escape(s.split()[-1]) for s in subs) + r")", re.I)
    out = []
    for s in sorted(new, key=lambda x: x["n"]):
        old = orig[s["n"] - 1]
        if s["text"] != old and not s["changed"]:
            raise ValueError(f"step {s['n']} was changed but not marked as changed")
        if rx.search(_mask(s["text"])):
            raise ValueError(f"step {s['n']} still mentions a removed ingredient")
        if rx.search(_mask(old)) and not sub_rx.search(s["text"]):
            raise ValueError(f"step {s['n']} doesn't mention the substitute where the removed ingredient was")
        if s["text"] != old:
            ok = allowed | {w for g in _ngrams(old) for w in g.split()} | STAPLE_WORDS
            for g in _ngrams(s["text"]) - _ngrams(old):
                if g in vocab and not set(g.split()) <= ok:
                    raise ValueError(f"step {s['n']} adds a new ingredient: {g}")
        out.append({"n": s["n"], "old": old, "text": s["text"], "changed": s["text"] != old,
                    "reason": s["reason"] if s["text"] != old else ""})
    return out


def fallback_steps(orig: list[str], swaps: list[tuple[re.Pattern, str, str]]) -> list[dict]:
    """Deterministic rewrite: each mention of a removed item becomes its substitute."""
    out = []
    for n, old in enumerate(orig, 1):
        text, why = old, []
        for rx, sub, item in swaps:
            masked = _mask(text)
            if rx.search(masked):
                spans = [m.span() for m in rx.finditer(masked)]
                for a, b in reversed(spans):
                    text = text[:a] + sub + text[b:]
                why.append(f"{item} -> {sub}")
        out.append({"n": n, "old": old, "text": text, "changed": text != old, "reason": "; ".join(why)})
    return out


def final_gate(kept: list[str], added: list[str], tags, known, declared=None) -> list[tuple[str, str]]:
    """[(what, reason)] for adapted lines or substitutes that contain, may contain or can't be verified free of a tag."""
    fails = safety.check_lines(kept, tags, known)
    for name in added:
        ok, why = safety.verify_canonical(name, tags, known, declared)
        if not ok:
            fails.append((name, why))
    return fails


def _steps(con: sqlite3.Connection, rid: str) -> list[str]:
    instr, para = con.execute("SELECT instructions_raw, is_paragraph_format FROM recipes WHERE id = ?", (rid,)).fetchone()
    return [instr.strip()] if para else [s.strip() for s in instr.split("\n") if s.strip()]


def facts(res) -> dict:
    """Everything the effects text may cite (for the voice validator)."""
    return {"recipe": res.rid, "dish": " ".join(res.dish), "parts": [{
        "removed": p.item, "substitute": p.chosen.name, "roles": p.roles, "strength": p.chosen.strength,
        "removed_amount_in_similar_recipes": p.target_qty, "substitute_amount": p.chosen.quantity,
        "tiers": {t: {"with": x.n_with, "in_with": x.in_with, "without": x.n_without, "support": x.support,
                      "lift": fmt_lift(x.lift)}
                  for t, x in p.chosen.tiers.items()}, "ids": p.chosen.ids[:6]} for p in res.parts if p.chosen]}


def verified_lines(res) -> list[str]:
    """Counts, ids and ratios straight from the evidence (no model involved)."""
    out = []
    for p in res.parts:
        c, t = p.chosen, p.chosen.tiers
        a = t["L1"]
        out.append(f"{c.name} for {p.item}: used by {a.support} of {a.n_without} '{' '.join(res.dish)}' recipes without "
                   f"{p.item} vs {a.in_with} of {a.n_with} with it (L1, lift {fmt_lift(a.lift)}), {t['L2'].support} of "
                   f"{t['L2'].n_without} similar recipes (L2) and {t['L3'].support:,} of {t['L3'].n_without:,} "
                   f"{res.context} recipes (L3).")
        if c.explicit:
            out.append(f"Explicit variants using it: {', '.join(f'`{r}`' for r in c.explicit[:4])}.")
        if c.quantity:
            out.append(f"Observed amount of {c.name}: {c.quantity}" + (f"; {p.item} in similar recipes that have it: "
                                                                      f"{p.target_qty}." if p.target_qty else "."))
    return out


def _amount(p, est: str | None) -> str:
    """'3/4 cup applesauce (estimate: 1/4 cup per egg; replaces 3 eggs)', or the observed median when there is one."""
    c, q, lines = p.chosen, p.chosen.observed, [raw for _, raw in p.affected]
    n = amounts.scale(est, lines) if est else ""
    if q:
        return f"{q[0]} {c.name} (observed median in {q[1]} recipes without {p.item}" + (
            f"; estimate for {', '.join(lines)}: {n}" + ("" if est.startswith(n) else f", from {est}") + ")" if n else ")")
    what = n if n and c.name.split()[-1] in n else f"{n} {c.name}".strip()
    return (f"{'extra ' if c.kind == 'increase' else ''}{what} (estimate: "
            f"{est or 'not verified; start with the same amount'}; replaces {', '.join(lines)})")


def build(con: sqlite3.Connection, ds, res, use_llm: bool = True, caveat: str = "",
          timeout_ms: int = 12_000) -> Adaptation:
    """Diff, steps (model or fallback), gate and effects for a graded substitution."""
    from .substitute import DECLARED, ESTIMATE, PREP, _key
    lines = [(n, raw) for n, raw in con.execute("SELECT DISTINCT line_no, raw FROM ingredient_lines WHERE recipe_id = ? "
                                                "AND is_header = 0 AND is_not_food = 0 ORDER BY line_no", (res.rid,))]
    gone = {n: p for p in res.parts for n, _ in p.affected}
    diff, added = [], []
    for n, raw in lines:
        if n not in gone:
            diff.append({"op": "keep", "text": raw})
            continue
        diff.append({"op": "remove", "text": raw})
        p = gone[n]
        items = [i for i in nz.parse_line(raw) if i.name]  # 'butter and maple syrup' minus butter keeps the syrup
        hit = lambda i: p.spec.line_hits(i.name.canonical, i.name.family, dict(nz.tags_for(i.name.canonical)))
        if len(items) > 1 and any(map(hit, items)):
            diff += [{"op": "add", "text": f"{i.name.clean} (kept from the same line)", "kept": i.name.clean}
                     for i in items if not hit(i)]
        if p.chosen.name in added:
            continue
        diff.append({"op": "add", "text": _amount(p, ESTIMATE.get(_key(p.spec, ESTIMATE) or "", {}).get(p.chosen.name))})
        added.append(p.chosen.name)
    orig, tags = _steps(con, res.rid), list(dict.fromkeys([*res.restrictions, *(p.spec.tag for p in res.parts if p.spec.tag)]))
    words = {p.item: [w for w in {p.spec.canonical, p.spec.family, *p.spec.words,
                                  *(nz_words(raw) for _, raw in p.affected)} if w] for p in res.parts}
    rx = removed_rx([w for ws in words.values() for w in ws])
    swaps = [(removed_rx(words[p.item]), p.chosen.name, p.item) for p in res.parts]
    ad = Adaptation(diff, fallback_steps(orig, swaps), prep=[PREP[a] for a in added if a in PREP])
    allowed = {w for d in diff if d["op"] != "remove" for w in re.findall(r"[a-z]+", d["text"].lower())} | set(added)
    f = facts(res)
    if use_llm and llm.available():
        prompt = (f"ROLES: {json.dumps({p.item: p.roles or 'unknown' for p in res.parts})}\n"
                  f"SUBSTITUTIONS: " + "; ".join(f"remove {', '.join(r for _, r in p.affected)} -> use {p.chosen.name}"
                                                for p in res.parts) +
                  f"\nINGREDIENTS: {json.dumps([d['text'] for d in diff if d['op'] != 'remove'])}\n"
                  f"EXAMPLES: {json.dumps([s for p in res.parts for _, s in p.chosen.snippets])}\n"
                  f"FACTS: {json.dumps(f)}\nSTEPS:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(orig, 1)))
        try:
            def check(d):
                steps = validate_steps(orig, d["steps"], rx, added, allowed, ds.vocab)
                return steps, d.get("predicted_effects", ""), d.get("roles") or []
            (steps, pred, roles), ad.calls = llm.generate_json(SYSTEM, prompt, SCHEMA, check, timeout_ms=timeout_ms,
                                                        attempts=1, label="substitute")
            ad.steps, ad.source, ad.model_roles = steps, "model", roles
            try:
                ad.predicted = voice.check(pred, f) if pred else None
            except ValueError as e:
                ad.predicted_status = f"withheld by the validator ({e})"
        except llm.LLMError as e:
            ad.calls = e.calls
            ad.predicted_status = f"not generated (model {llm.error_kind(str(e))})"
    else:
        ad.predicted_status = "not generated (model not used)"
    kept = [d["text"] if d["op"] == "keep" else d["kept"] for d in diff if d["op"] == "keep" or d.get("kept")]
    ad.gate = final_gate(kept, added, tags, ds.vocab, {a: DECLARED[a] for a in added if a in DECLARED})
    ad.verified = []
    for line in verified_lines(res):
        try:
            ad.verified.append(voice.check(line, f | {"context": res.context}))
        except ValueError:
            pass  # a line the facts can't back is dropped, never shown
    if set(tags) & {"dairy", "egg", "peanut", "tree_nut", "gluten", "soy", "sesame", "fish", "shellfish"}:
        ad.safety_line = ALLERGY_LINE
    ad.caveat = caveat
    return ad


def weak_label(res) -> str:
    """'Weak evidence for coconut milk: based on 1 recipe without cream ('cream sauce' titles).' per Weak part, from
    the first tier with support; '' when nothing is Weak."""
    where = {"L1": f"'{' '.join(res.dish)}' titles", "L2": "similar recipes", "L3": f"{res.context} recipes"}
    out = []
    for p in (p for p in res.parts if p.chosen.strength == "Weak"):
        t = next((k for k in ("L1", "L2", "L3") if p.chosen.tiers[k].support), "L3")
        n = p.chosen.tiers[t].support
        out.append(f"Weak evidence for {p.chosen.name}: based on {n:,} recipe{'' if n == 1 else 's'} without "
                   f"{p.item} ({where[t]}).")
    return " ".join(out)


def nz_words(raw: str) -> str:
    """The canonical of a removed line ('2 large eggs' -> 'egg'), for the leftover-mention regex."""
    items = nz.parse_line(raw)
    return items[0].name.canonical if items and items[0].name else ""
