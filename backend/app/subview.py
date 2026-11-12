"""Reply and UI payload for a substitution turn (PRD 6.4, PRD 8 substitution view). No LLM: every count, id and
ratio comes from substitute.Result; the predicted-effects text was already voice-checked in adapt.py.

markdown(res): the full reply (CLI, which has no panel). summary(res): the chat bubble (verdict, chosen because, a
few key lines). view(con, res): (summary, payload) where the payload has the evidence table (one row per candidate,
rejected ones with reasons), the ingredient/step diff, verified vs predicted effects, the final safety gate, and cards
for every recipe id the reply cites (so the post-check keeps them).
"""
from .evidence import MIN_L1, MIN_WITHOUT, fmt_lift

METHOD = ("Evidence tiers: L1 = recipes whose title has the most specific dish phrase with ≥ 10 recipes, ≥ 3 of "
          "them without the removed item ('tomato cream sauce' → 'cream sauce' → 'pasta'); L2 = recipes in the same dish context with ingredient-set Jaccard "
          "≥ 0.35; L3 = the whole dish context. For each candidate and tier: n_with / n_without = recipes with / "
          "without the removed item, support / in_with = those that use the candidate; raw rates support/n_without "
          "and in_with/n_with; lift = their ratio, only when support ≥ 3 and n_with ≥ 20 (else 'too few to "
          "compute'). Strong = more common without than with in L1, and ≥ 3 L1 supporting recipes, or an explicit "
          "variant ('eggless …') plus ≥ 2 in L1 or ≥ 3 in L2; never for a staple (baking soda, salt, …). Moderate = ≥ 3 in L2, more "
          "common without; Weak = any support (adapted, labelled 'Weak evidence: based on n recipes'); None = none. If no "
          "candidate is Strong or Moderate, L1 widens to the next less specific phrase ('cream sauce' → 'pasta'). Co-occurrences without an established role are capped at "
          "Weak. Choice: never a conflicting candidate over a non-conflicting one, then strength, then role coverage, then L1 "
          "evidence for it before against, then support, lift. Every "
          "cited id is re-checked: it lacks the removed item and contains the candidate.")


def _counts(res, item: str, c) -> str:
    """'1/13 'banana bread' recipes without eggs vs 10/178 with (L1, lift too few to compute) · 0 of 9 similar (L2)'."""
    t, a = c.tiers, c.tiers["L1"]
    s = (f"{a.support}/{a.n_without} '{' '.join(res.dish)}' recipes without {item} vs {a.in_with}/{a.n_with} with "
         f"(L1, lift {fmt_lift(a.lift)})")
    if a.support < 3:
        s += f" · {t['L2'].support} of {t['L2'].n_without} similar (L2) · {t['L3'].support:,} of {t['L3'].n_without:,} " \
             f"{res.context} (L3)"
    return s


def because(p) -> str:
    """'Chosen because: Strong, not conflicting, 2/13 L1 recipes without eggs use it; next: applesauce (Strong, 1/13).'"""
    c, i = p.chosen, p.candidates.index(p.chosen)
    if c.kind == "user":
        return "Chosen because you named it."
    if i:
        return f"Chosen because you picked option {i + 1}."
    a = c.tiers["L1"]
    nxt = next((x for x in p.candidates if x is not c), None)
    return (f"Chosen because: {c.strength}, {'conflicting (so is every option)' if c.conflicting else 'not conflicting'}, "
            f"{a.support}/{a.n_without} L1 recipes without {p.item} use it (lift {fmt_lift(a.lift)})" +
            (f"; next: {nxt.name} ({nxt.strength}{', conflicting' if nxt.conflicting else ''}, "
             f"{nxt.tiers['L1'].support}/{a.n_without})." if nxt else "; the only usable option."))


def _l1(res) -> str:
    n, dish, wo = res.tiers.get("L1", 0), " ".join(res.dish), res.l1_without
    why = res.widened or ("the most specific title phrase with ≥ 10 recipes, ≥ 3 of them without it"
                          if n >= MIN_L1 and wo >= MIN_WITHOUT else "no title phrase has ≥ 10 recipes with ≥ 3 without it: the largest")
    return f"L1 = {n:,} recipes titled '{dish}', {wo:,} without the item ({why})"


def _gate(res) -> list[str]:
    a = res.adaptation
    if a.gate:
        return ["> ✗ **Not safe for your restrictions:** " + "; ".join(f"{w}: {why}" for w, why in a.gate)
                + ". Say e.g. 'remove the " + _name(a.gate[0][0]) + " too' to replace it as well."]
    return [f"> ✓ Every adapted ingredient was verified free of: {', '.join(res.restrictions)}."] if res.restrictions \
        else []


def summary(res) -> list[str]:
    """The chat bubble: one verdict line per removed item (substitute, strength), why it was chosen, the gate result,
    and a pointer to the panel. The evidence table, diff and verified/predicted effects live in the panel only."""
    md = [f"> {res.picked}"] if getattr(res, "picked", "") else []
    for p in res.parts:
        if not p.chosen:
            md.append(f"Nothing usable replaces **{p.item}** in **{res.title}**: " + (
                "every candidate was rejected." if p.rejected else "no curated role and no co-occurrence in the data."))
            continue
        add = next((d["text"] for d in (res.adaptation.ingredients if res.adaptation else [])
                    if d["op"] == "add" and not d.get("kept") and p.chosen.name in d["text"]), p.chosen.name)
        md.append(f"**{p.item.capitalize()} → {add}** in **{res.title}** — **{p.chosen.strength}** evidence. "
                  + because(p))
    if res.parts:
        n = sum(len(p.rejected) for p in res.parts)
        md.append(_l1(res) + f" · {n} candidate{'' if n == 1 else 's'} rejected.")
    md += [f"> {res.question}"] if res.question else []
    md += ([f"> ⚠ {res.adaptation.caveat}"] if res.adaptation.caveat else []) + _gate(res) if res.adaptation \
        else [f"> {n}" for n in res.notes]
    return md + ["_Full evidence and diff in the panel._"]


def _name(line: str) -> str:
    """'1/8 cup freshly grated Parmesan cheese' -> 'parmesan cheese' (for the 'remove X too' hint)."""
    from .adapt import nz_words
    return nz_words(line) or line


def markdown(res) -> list[str]:
    """The substitution reply, one markdown block per line."""
    md = [f"> {res.picked}"] if getattr(res, "picked", "") else []
    md.append(f"**{res.title}** `{res.rid}` ({res.context}) · {_l1(res)}; L2 = {res.tiers.get('L2', 0):,} similar "
              f"recipes; L3 = {res.tiers.get('L3', 0):,} {res.context} recipes.")
    for p in res.parts:
        # ponytail: the model guesses a role only inside the adaptation call (one LLM call per turn)
        role = ", ".join(p.roles) if p.roles else "unknown in roles.yaml" + (
            f"; model reasoning, not dataset evidence: {', '.join(res.adaptation.model_roles)}"
            if res.adaptation and res.adaptation.model_roles else "")
        md.append(f"Removing **{p.item}** ({'; '.join(r for _, r in p.affected)}) · role: _{role}_")
        for i, c in enumerate(p.candidates[:3], 1):
            ex = f" · explicit variants: {', '.join(f'`{r}`' for r in c.explicit[:3])}" if c.explicit else ""
            md.append(f"{i}. **{c.name}**{' (chosen)' if c is p.chosen else ''} — **{c.strength}** · "
                      f"{_counts(res, p.item, c)} · {c.label}{ex}")
        if len(p.candidates) > 3:
            md.append(f"_… {len(p.candidates) - 3} more in the Evidence tab._")
        if not p.candidates:
            md.append("No usable replacement: " + ("every candidate was rejected." if p.rejected else
                                                   "no curated role and no co-occurrence in the data."))
        if p.rejected:
            md.append("_Rejected: " + "; ".join(f"{n} ({why})" for n, why in p.rejected[:4])
                      + (f"; … {len(p.rejected) - 4} more in the Evidence tab" if len(p.rejected) > 4 else "") + "_")
        md += [because(p)] if p.chosen else []
        if p.conflicting:
            md.append("> ⚠ Conflicting evidence: the tiers disagree, or a better-supported candidate fails a restriction.")
    if res.question:
        md.append(f"> {res.question}")
    a = res.adaptation
    if a:
        md.append("**Adapted recipe** (side-by-side diff in the Results panel):")
        md += [f"- {'−' if d['op'] == 'remove' else '+'} {d['text']}" for d in a.ingredients if d["op"] != "keep"]
        md += [f"- Prep: {x}" for x in a.prep]
        md += [f"- Step {s['n']} (changed): {s['text']}" for s in a.steps if s["changed"]]
        md.append(f"_Steps {'rewritten by the model and validated' if a.source == 'model' else 'swapped deterministically'}._")
        md += [f"> ⚠ {a.caveat}"] if a.caveat else []
        md += ["**Verified from dataset:**"] + [f"- {v}" for v in a.verified]
        md += ["**Predicted (not verifiable from recipe text):**", a.predicted or a.predicted_status]
        md += _gate(res) + ([f"> {a.safety_line}"] if a.safety_line else [])
    md += [f"> {n}" for n in res.notes]
    return md


def _cand(c) -> dict:
    return {"name": c.name, "kind": c.kind, "label": c.label, "roles": c.roles, "strength": c.strength,
            "conflicting": c.conflicting, "explicit": c.explicit, "ids": c.ids, "quantity": c.quantity,
            "snippets": [{"id": r, "text": t} for r, t in c.snippets],
            "tiers": {k: {"n_with": t.n_with, "in_with": t.in_with, "n_without": t.n_without, "support": t.support,
                          "lift": fmt_lift(t.lift)}
                      for k, t in c.tiers.items()}}


def view(con, res) -> tuple[list[str], dict]:
    """(markdown lines, payload) for the web UI."""
    from .web import _base, _card  # web imports the session, which imports this module's caller
    ids = list(dict.fromkeys([res.rid] + [r for p in res.parts for c in p.candidates for r in c.explicit + c.ids]))
    base = _base(con, ids)
    a = res.adaptation
    payload = {"type": "substitute", "target": {"id": res.rid, "title": res.title}, "context": res.context,
               "dish": " ".join(res.dish), "l1_note": _l1(res), "tiers": res.tiers, "restrictions": res.restrictions, "question": res.question,
               "notes": res.notes,
               "cards": [_card(i, *base[i]) for i in ids if i in base],
               "parts": [{"item": p.item, "affected": [r for _, r in p.affected], "roles": p.roles,
                          "target_qty": p.target_qty, "conflicting": p.conflicting,
                          "strength": p.strength, "chosen": p.chosen.name if p.chosen else None,
                          "because": because(p) if p.chosen else "",
                          "candidates": [_cand(c) for c in p.candidates],
                          "rejected": [{"name": n, "reason": w} for n, w in p.rejected]} for p in res.parts],
               "adaptation": None if not a else {
                   "ingredients": a.ingredients, "steps": a.steps, "prep": a.prep, "source": a.source,
                   "gate": [{"what": w, "reason": r} for w, r in a.gate], "verified": a.verified, "predicted": a.predicted,
                   "predicted_status": a.predicted_status, "safety_line": a.safety_line, "caveat": a.caveat},
               "calc": [{"label": "substitution", "value": sum(len(p.candidates) for p in res.parts),
                         "filters": ", ".join(f"no {t}" for t in res.restrictions) or "none",
                         "n_analyzed": res.tiers.get("L3", 0), "denominator": res.tiers.get("L3", 0), "method": METHOD,
                         "sql": None, "normalization_note": "Candidates: curated (lexicon/candidates.yaml), use-more of "
                         "an ingredient already in the recipe, your pick, and data-discovered co-occurrences (lift ≥ 2, "
                         "support ≥ 3). Unknown is not safe: a candidate must be verified against every restriction.",
                         "notes": res.notes}]}
    return summary(res), payload
