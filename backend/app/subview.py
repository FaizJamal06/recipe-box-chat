"""Reply and UI payload for a substitution turn (PRD 6.4, PRD 8 substitution view). No LLM: every count, id and
ratio comes from substitute.Result; the predicted-effects text was already voice-checked in adapt.py.

markdown(res): the reply (CLI text and chat bubble). view(con, res): (markdown, payload) where the payload has the
evidence table (one row per candidate, rejected ones with reasons), the ingredient/step diff, verified vs predicted
effects, the final safety gate, and cards for every recipe id the reply cites (so the post-check keeps them).
"""
METHOD = ("Evidence tiers: L1 = recipes whose title has the dish words; L2 = recipes in the same dish context with "
          "ingredient-set Jaccard ≥ 0.35; L3 = the whole dish context. For each candidate and tier: n_with / n_without "
          "= recipes with / without the removed item, support = WITHOUT recipes that use the candidate, lift = "
          "((support+1)/(n_without+2)) / ((in_with+1)/(n_with+2)). Strong = an explicit-variant L1 title "
          "('eggless …') using it while it is rarer in recipes WITH the item, or support ≥ 3 in L1 with lift > 1; "
          "Moderate = support ≥ 3 in L2 with lift > 1; Weak = L3 only or < 3; None = no support. Co-occurrences "
          "without an established role are capped at Weak. Every cited id is re-checked: it lacks the removed item "
          "and contains the candidate.")


def _counts(res, item: str, c) -> str:
    """'3 of 5 'banana bread' recipes without eggs (L1, lift 2.4) · 4 of 9 similar (L2)'."""
    t, dish = c.tiers, " ".join(res.dish)
    s = f"{t['L1'].support} of {t['L1'].n_without} '{dish}' recipes without {item} (L1, lift {t['L1'].lift:.1f})"
    if t["L1"].support < 3:
        s += f" · {t['L2'].support} of {t['L2'].n_without} similar (L2) · {t['L3'].support:,} of {t['L3'].n_without:,} " \
             f"{res.context} (L3)"
    return s


def _name(line: str) -> str:
    """'1/8 cup freshly grated Parmesan cheese' -> 'parmesan cheese' (for the 'remove X too' hint)."""
    from .adapt import nz_words
    return nz_words(line) or line


def markdown(res) -> list[str]:
    """The substitution reply, one markdown block per line."""
    md = [f"> {res.picked}"] if getattr(res, "picked", "") else []
    md.append(f"**{res.title}** `{res.rid}` · dish: _{' '.join(res.dish)}_ ({res.context}) · compared with "
              f"{res.tiers.get('L1', 0):,} title matches (L1), {res.tiers.get('L2', 0):,} similar recipes (L2), "
              f"{res.tiers.get('L3', 0):,} {res.context} recipes (L3).")
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
            md.append("No usable replacement: every candidate was rejected.")
        if p.rejected:
            md.append("_Rejected: " + "; ".join(f"{n} ({why})" for n, why in p.rejected[:4])
                      + (f"; … {len(p.rejected) - 4} more in the Evidence tab" if len(p.rejected) > 4 else "") + "_")
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
        md.append(f"_Steps {'rewritten by the model and validated' if a.source == 'model' else 'swapped deterministically'}"
                  + (f"; {a.predicted_status}" if a.predicted_status else "") + "._")
        md += [f"> ⚠ {a.caveat}"] if a.caveat else []
        md += ["**Verified from dataset:**"] + [f"- {v}" for v in a.verified]
        md += ["**Predicted (not verifiable from recipe text):**", a.predicted] if a.predicted else []
        if a.gate:
            md.append("> ✗ **Not safe for your restrictions:** " + "; ".join(f"{w}: {why}" for w, why in a.gate)
                      + ". Say e.g. 'remove the " + _name(a.gate[0][0]) + " too' to replace it as well.")
        elif res.restrictions:
            md.append(f"> ✓ Every adapted ingredient was verified free of: {', '.join(res.restrictions)}.")
        md += [f"> {a.safety_line}"] if a.safety_line else []
    md += [f"> {n}" for n in res.notes]
    return md


def _cand(c) -> dict:
    return {"name": c.name, "kind": c.kind, "label": c.label, "roles": c.roles, "strength": c.strength,
            "conflicting": c.conflicting, "explicit": c.explicit, "ids": c.ids, "quantity": c.quantity,
            "snippets": [{"id": r, "text": t} for r, t in c.snippets],
            "tiers": {k: {"n_with": t.n_with, "in_with": t.in_with, "n_without": t.n_without, "support": t.support,
                          "lift": round(t.lift, 2)}
                      for k, t in c.tiers.items()}}


def view(con, res) -> tuple[list[str], dict]:
    """(markdown lines, payload) for the web UI."""
    from .web import _base, _card  # web imports the session, which imports this module's caller
    ids = list(dict.fromkeys([res.rid] + [r for p in res.parts for c in p.candidates for r in c.explicit + c.ids]))
    base = _base(con, ids)
    a = res.adaptation
    payload = {"type": "substitute", "target": {"id": res.rid, "title": res.title}, "context": res.context,
               "dish": " ".join(res.dish), "tiers": res.tiers, "restrictions": res.restrictions, "question": res.question,
               "notes": res.notes,
               "cards": [_card(i, *base[i]) for i in ids if i in base],
               "parts": [{"item": p.item, "affected": [r for _, r in p.affected], "roles": p.roles,
                          "target_qty": p.target_qty, "conflicting": p.conflicting,
                          "strength": p.strength, "chosen": p.chosen.name if p.chosen else None,
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
    return markdown(res), payload
