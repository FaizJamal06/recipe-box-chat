"""API view of a turn (PRD 7): templated markdown reply, structured payload for the UI panels, trace, and
the post-check that every recipe ID written in the reply exists in the payload.

The markdown is our own small subset, one block per line: '- ' / '1. ' list items, '> ' callouts, plain
lines; inline **bold**, _italic_, `code` (a code span holding a recipe ID becomes a clickable ID in the UI).
Nothing here calls the LLM: every number comes from an executor Result.
"""
import json
import logging
import re
import sqlite3

from . import search, stats
from .db import Dataset
from .match import MatchResult
from .search import SearchResult
from .session import Session, Turn
from .stats import Result

log = logging.getLogger("recipebox")
ID_RX = re.compile(r"`((?:ar|epi|fn):[^`\s]+)`")
SEARCH_METHOD = ("FTS5 match on title + ingredients; titles containing the exact phrase first, then BM25 (title "
                 "weighted 3x), then id. Hard filters run in SQL on the complete set before ranking.")
SEARCH_NORM = ("Included ingredients: strict (the family when the word names one, else the exact canonical). "
               "Excluded ingredients: broad family + any ingredient line mentioning the word. Excluded tags: "
               "'contains' lines (also 'may_contain' in strict mode).")


def recipe(con: sqlite3.Connection, rid: str) -> dict | None:
    """Original recipe + parsed lines + tags, for the drawer and GET /api/recipe/{id}."""
    row = con.execute("SELECT id, source, title, ingredients_raw, instructions_raw, n_ingredients, n_steps, "
                      "is_paragraph_format, valid FROM recipes WHERE id = ?", (rid,)).fetchone()
    if not row:
        return None
    rid, source, title, ing, instr, n_ing, n_steps, para, valid = row
    lines = [s for x in json.loads(ing) if isinstance(x, str) and (s := x.replace("ADVERTISEMENT", "").strip())]
    steps = [instr.strip()] if para else [s.strip() for s in instr.split("\n") if s.strip()]
    parsed = [dict(zip(("line_no", "raw", "canonical", "family", "qty", "unit", "is_alt", "is_header", "is_not_food"), r))
              for r in con.execute("SELECT line_no, raw, canonical, family, qty, unit, is_alt, is_header, is_not_food "
                                   "FROM ingredient_lines WHERE recipe_id = ? ORDER BY line_no, alt_group, is_alt", (rid,))]
    tags = dict(con.execute("SELECT tag, level FROM recipe_tags WHERE recipe_id = ? ORDER BY tag", (rid,)).fetchall())
    return {"id": rid, "source": source, "title": title, "ingredients": lines, "steps": steps, "paragraph": bool(para),
            "n_ingredients": n_ing, "n_steps": n_steps, "valid": bool(valid), "parsed": parsed, "tags": tags}


def _chip(e: str) -> dict:
    """Evidence line -> colored chip (violation red / may-contain warning / satisfied)."""
    kind = ("violation" if e.startswith("VIOLATES") else "may_contain" if "may contain" in e or "alternative" in e
            else "matched" if e.startswith("has ") else "ok")
    return {"kind": kind, "label": e.split(":")[0].replace("VIOLATES ", "✗ ") if ":" in e else e, "detail": e}


def _base(con: sqlite3.Connection, ids: list[str]) -> dict:
    """{id: (title, source, n_ingredients, n_steps)} for cards that only carry ids."""
    q = f"SELECT id, title, source, n_ingredients, n_steps FROM recipes WHERE id IN ({','.join('?' * len(ids))})"
    return {r[0]: r[1:] for r in con.execute(q, ids)} if ids else {}


def _card(rid, title, source, n_ing, n_steps, chips=(), **extra) -> dict:
    return {"id": rid, "title": title, "source": source, "n_ingredients": n_ing, "n_steps": n_steps,
            "chips": list(chips), **extra}


def _md_cards(cards: list[dict], extra=lambda c: "", top: int = 5) -> list[str]:
    """Numbered list of the first `top` cards (the Results panel shows them all)."""
    n = lambda k, word: f"{k} {word}{'' if k == 1 else 's'}"
    out = [f"{i}. **{c['title'].strip()}** `{c['id']}` — {n(c['n_ingredients'], 'ingredient')} · "
           f"{n(c['n_steps'], 'step')}{extra(c)}" for i, c in enumerate(cards[:top], 1)]
    return out + ([f"_… {len(cards) - top} more in the Results panel._"] if len(cards) > top else [])


def _match_card(con, r) -> dict:
    t, src, n_ing, n_steps = _base(con, [r.id])[r.id]
    chips = [{"kind": "matched", "label": x, "detail": "you have it"} for x in r.matched] + \
            [{"kind": "extra", "label": x, "detail": "extra ingredient needed"} for x in r.extra] + \
            [{"kind": "unused", "label": x, "detail": "yours, not used here"} for x in r.unused] + \
            [{"kind": "violation" if "short by" in q else "unused" if "not verified" in q else "ok",
              "label": q.split(" (")[0].split(";")[0], "detail": q} for q in r.qty]
    return _card(r.id, t, src, n_ing, n_steps, chips, score=round(r.score, 2), parts=r.parts, staples=r.staples)


def _calc(r: Result) -> dict:
    return {"label": r.mode if r.op in ("count", "percentage") else r.op.replace("_", " "), "value": r.value, "filters": r.filters, "n_analyzed": r.n_analyzed,
            "denominator": r.denominator, "method": r.method, "sql": r.sql, "normalization_note": r.normalization_note,
            "notes": r.notes}


def _stats(con, ds: Dataset, res, plan: dict) -> tuple[list[str], dict]:
    """Markdown + payload for any stats Result(s)."""
    results = res if isinstance(res, list) else [res]
    r0, md = results[0], []
    payload = {"type": "stats", "op": r0.op, "calc": [_calc(r) for r in results], "cards": [], "rows": []}
    if isinstance(res, list):
        md.append(f"Recipes where: _{r0.filters}_")
        md += [f"- **{r.mode}**: **{r.value:,}** of {ds.valid:,} valid recipes = **{100 * r.value / r.denominator:.2f}%**"
               for r in results]
        md.append(f"_{ds.header(r0.value)}_")
    elif r0.op == "rank":
        base = _base(con, r0.value)
        payload["cards"] = [_card(rid, *base[rid]) for rid in r0.value]
        md.append(f"**{len(r0.value)} recipes** ({r0.filters}), {plan['stats']['field'].replace('n_', '')} "
                  f"{'ascending' if plan['stats']['order'] == 'asc' else 'descending'}:")
        md += _md_cards(payload["cards"])
        md.append(f"_Analyzed: {ds.header(r0.n_analyzed)}_")
    elif r0.op == "top_ingredients":
        payload["rows"] = [{"name": c, "recipes": n} for c, n in r0.rows]
        md += [f"Top {len(r0.rows)} ingredients by recipe count ({r0.filters}):"]
        md += [f"{i}. **{c}** — {n:,} recipes" for i, (c, n) in enumerate(r0.rows, 1)]
        md.append(f"_Analyzed: {ds.header(r0.n_analyzed)}_")
    else:
        md.append(f"{r0.op.capitalize()} number of {plan['stats']['field'].replace('n_', '')} ({r0.filters}): "
                  f"**{r0.value}**")
        md.append(f"_Analyzed: {ds.header(r0.n_analyzed)}_")
    if r0.normalization_note:
        md.append(f"Normalization: {r0.normalization_note}")
    md += [f"> Note: {n}" for n in r0.notes] + [f"Method: {r0.method}", "_SQL: see the Calculation tab._"]
    return md, payload


def view(turn: Turn, s: Session) -> tuple[str, dict]:
    """(reply_md, payload) for one turn."""
    con, ds, res, intent = s.con, s.ds, turn.result, turn.plan["intent"]
    md = [f"> {n}" for n in turn.notes]
    if isinstance(res, SearchResult):
        cards = [_card(h.id, h.title, h.source, h.n_ingredients, h.n_steps, map(_chip, h.evidence), evidence=h.evidence)
                 for h in res.hits]
        payload = {"type": "search", "total": res.total, "cards": cards, "calc": [{
            "label": "search", "value": res.total, "filters": res.filters, "n_analyzed": res.total,
            "denominator": ds.valid, "method": SEARCH_METHOD, "sql": res.sql, "normalization_note": SEARCH_NORM,
            "notes": []}]}
        md += [f"**{res.total:,} recipes** match _{res.filters}_; showing {len(cards)}.", f"_{ds.header(res.total)}_"]
        md += _md_cards(cards) or ["No recipe satisfies every restriction; none were relaxed."]
    elif isinstance(res, MatchResult):
        cards = [_match_card(con, r) for r in res.rows]
        alts = [{"violates": label, "cards": [_match_card(con, r) for r in rows]} for label, rows in res.alternatives]
        w = res.weights
        payload = {"type": "match", "total": res.total, "cards": cards, "alternatives": alts,
                   "have": [h.term.text for h in res.have], "unknown": res.unknown, "staples": list(res.staples),
                   "dropped": [{"item": h.term.text, "why": why} for h, why in res.dropped],
                   "calc": [{"label": "match", "value": res.total, "filters": "; ".join(res.constraints),
                             "n_analyzed": res.total, "denominator": ds.valid,
                             "method": f"score = {w['m']:g}·matched − {w['e']:g}·extra − {w['s']:g}·steps − "
                                       f"{w['q']:g}·short-quantity items; ties: more matched, fewer extra, fewer "
                                       "steps, id", "sql": res.sql,
                             "normalization_note": "U = your ingredients (family match), P = pantry staples "
                                                   f"({', '.join(res.staples) or 'off'}), R = recipe's required "
                                                   "ingredients − P. matched = U∩R, unused = U−R, extra = R−U.",
                             "notes": []}]}
        md.append(f"Your ingredients: **{', '.join(payload['have']) or 'none'}**"
                  + (f" · staples assumed: {', '.join(res.staples)}" if res.staples else " · no staples assumed"))
        md += [f"> Not in the dataset vocabulary (ignored): {', '.join(res.unknown)}"] if res.unknown else []
        md += [f"> Removed from your ingredients because '{d['why']}' excludes it: {d['item']}" for d in payload["dropped"]]
        md.append(f"Hard constraints: _{'; '.join(res.constraints)}_")
        if not cards:
            md.append("**No recipe satisfies all hard constraints**")
            if alts:
                md.append("> ⚠ **Closest alternatives — these are NOT matches; each violates the named constraint**")
                for a in alts:
                    md.append(f"_Violates '{a['violates']}':_")
                    md += _md_cards(a["cards"]) or ["- (none even with this relaxed)"]
        else:
            md.append(f"**Top {len(cards)}** of {ds.header(res.total)}")
            md += _md_cards(cards, lambda c: f" · score **{c['score']:.2f}** · matched "
                            f"{sum(x['kind'] == 'matched' for x in c['chips'])}, extra "
                            f"{sum(x['kind'] == 'extra' for x in c['chips'])}")
    elif intent == "stats" and res is not None:
        md2, payload = _stats(con, ds, res, turn.plan)
        md += md2
    elif intent == "recipe_detail" and isinstance(res, str):
        r, st = recipe(con, res), s.state
        terms = lambda ws: [stats.term(w, ds) for w in ws]
        ev = search.evidence(con, res, terms(st.include), terms(st.exclude), st.exclude_tags, st.max_steps)
        payload = {"type": "recipe", "recipe": r, "cards": [_card(r["id"], r["title"], r["source"], r["n_ingredients"],
                                                                  r["n_steps"], map(_chip, ev))]}
        md += [f"**{r['title'].strip()}** `{r['id']}` — {r['n_ingredients']} ingredients · {r['n_steps']} steps "
               "(opened on the right)."] + [f"- {e}" for e in ev]
    else:  # unsupported guard answers, help, errors: the templated text, SQL moved to the Calculation tab
        ref = s.ref_id if intent == "unsupported" else None
        cards = [_card(ref, *_base(con, [ref])[ref])] if ref else []
        payload = {"type": "unsupported" if intent == "unsupported" else "text", "cards": cards,
                   "calc": [_calc(r) for r in (res if isinstance(res, list) else [res])] if isinstance(
                       res, (Result, list)) else []}
        md += [("- " + x.strip()[2:]) if x.strip().startswith("- ") else x.strip()
               for x in turn.reply.split("\n") if x.strip() and not x.startswith("SQL")]
    return postcheck("\n".join(md), payload), payload


def postcheck(md: str, payload: dict) -> str:
    """Every recipe ID in the reply must exist in the payload; strip (and log) any that don't."""
    known = {c["id"] for c in payload.get("cards", [])} | {c["id"] for a in payload.get("alternatives", [])
                                                         for c in a["cards"]}
    bad = [i for i in ID_RX.findall(md) if i not in known]
    for i in bad:
        log.warning("post-check: recipe id %s in reply but not in payload; stripped", i)
        md = md.replace(f"`{i}`", "`[id removed]`")
    payload["postcheck"] = {"ids_in_reply": len(ID_RX.findall(md)), "stripped": bad}
    return md


def trace(turn: Turn, s: Session, payload: dict, prev_total: int | None) -> list[str]:
    """Human-readable pipeline steps for the Trace tab."""
    p, out = turn.plan, [f"Planner: {turn.meta()[10:-1]}"]
    d = {k: v for k, v in p["state_patch"].items() if v and k != "mode"}
    out.append(f"Parsed: intent={p['intent']}" + (f", mode={p['state_patch']['mode']}" if d else "")
               + "".join(f", {k}={v}" for k, v in d.items()))
    out.append(f"State: {s.state.chips()}")
    if payload["type"] in ("search", "match"):
        moved = f"{prev_total:,} → " if prev_total is not None and prev_total != payload["total"] else ""
        out.append(f"Filtered: {moved}{payload['total']:,} eligible of {s.ds.valid:,} valid recipes")
        out.append("Ranked: title phrase, BM25(title×3, ingredients), id" if payload["type"] == "search"
                   else "Ranked: score, then matched desc, extra asc, steps asc, id")
    for c in payload.get("calc", []) if payload["type"] in ("stats", "unsupported") else []:
        out.append(f"Computed ({c['label']}): {c['value'] if not isinstance(c['value'], list) else len(c['value'])}"
                   f" over {c['n_analyzed']:,} recipes")
    pc = payload["postcheck"]
    out.append(f"Post-check: {pc['ids_in_reply']} recipe IDs in the reply, "
               + ("all present in the payload" if not pc["stripped"] else f"{len(pc['stripped'])} stripped"))
    return out
