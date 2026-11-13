"""One substitution turn inside a Session: resolve the target recipe, keep the substitution in the sticky state,
and re-run it when restrictions change.

Target: the selected recipe, always (when it matches the named dish, or no dish is named) -> else a search for the
named dish that must contain the removed item, preferring a recipe whose other lines all pass the final safety gate
(a from-scratch banana bread over a cake-mix one); the reply says which id was picked and why -> else one question.
The substitution persists in state.sub: "I'm also allergic to tree nuts" re-grades it, "use the second option"
switches the candidate, "adapt it anyway" forces a caveated adaptation, "replace butter with oil" starts a new pair.
"""
import re

from . import evidence, safety, search, stats, substitute, subview
from . import normalize as nz
from .planner import finish


def _target(ses, sub: dict) -> tuple[str | None, str]:
    """(recipe id, note on how it was picked) or (None, question)."""
    st, con, items, spec = ses.state, ses.con, sub["removes"], None
    sel = st.selected_recipe_id or (st.last_results[0] if len(st.last_results) == 1 else None)
    dish = sub["dish"]
    if sel and (not dish or all(w in " ".join(_title(con, sel)).lower() for w in dish.split())):
        return sel, ""
    if not dish:
        return None, "Which recipe should I change? Open one first (e.g. 'show me the first one'), or name the dish."
    include = []
    for w in items[:1]:
        try:
            include, spec = [stats.term(w, ses.ds)], substitute.spec_for(w, ses.ds)
        except stats.UnknownIngredient:
            pass
    hits = search.search(con, dish, include=include, limit=20).hits or search.search(con, dish, limit=20).hits
    head = re.compile(rf"\b{re.escape(dish)}(?:\s+[ivx\d]+)?$", re.I)  # 'Banana Bread II', not 'Banana Bread French Toast'
    heads = [h for h in hits if head.search(evidence.head(h.title))] or hits
    item = re.compile(rf"\b{re.escape(nz.singular(items[0].lower())[:5])}", re.I) if items else None  # cream -> creamy
    heads = [h for h in heads if item and item.search(h.title)] or heads  # the item matters in this dish
    ctx = evidence.contexts(con)
    usual = max(set(c := [ctx.get(h.id) for h in heads]), key=c.count) if heads else None  # the dish's usual context
    pool = [h for h in heads if ctx.get(h.id) == usual]
    if not pool:
        return None, f"I couldn't find a {dish} recipe. Which recipe do you mean?"
    tags = list(dict.fromkeys([*st.exclude_tags, *([spec.tag] if spec and spec.tag else [])]))
    hit = next((h for h in pool if _clean(ses, h.id, spec, tags)), None) if spec and tags else None
    note = f"I picked `{(hit or pool[0]).id}` '{(hit or pool[0]).title.strip()}', the top match for '{dish}'" + (
        f" that contains {items[0]}" if include else "")
    if hit:
        note += (f"; apart from the lines being replaced, every line is verified free of {' and '.join(tags)}, so the "
                 "adapted recipe can pass the safety check")
    elif tags:
        note += f"; every match has another line that isn't verified free of {' and '.join(tags)}"
    return (hit or pool[0]).id, note + ". Open another recipe to switch."


def _clean(ses, rid: str, spec, tags: list[str]) -> bool:
    """Apart from the lines being replaced, every ingredient line passes the final gate for these tags."""
    gone = {n for n, _ in substitute.affected(ses.con, rid, spec)}
    rest = [raw for n, raw in ses.con.execute("SELECT DISTINCT line_no, raw FROM ingredient_lines WHERE recipe_id = ? "
                                              "AND is_header = 0 AND is_not_food = 0", (rid,)) if n not in gone]
    return bool(gone) and not safety.check_lines(rest, tags, ses.ds.vocab)


def _title(con, rid: str) -> tuple[str, str]:
    """(title, ingredients_raw): 'this pasta recipe' still means the selected 'Penne in Cream Sauce'."""
    return con.execute("SELECT title, ingredients_raw FROM recipes WHERE id = ?", (rid,)).fetchone() or ("", "")


def handle(ses, text: str, p: dict, notes: list[str]) -> tuple[str, object]:
    """Run (or re-run) the substitution for this turn; returns (reply text, substitute.Result or None)."""
    st, sb, prev = ses.state, p["substitution"], ses.state.sub or {}
    new = bool(sb["remove"] or sb["remove_tags"] or (sb["replace_with"] and not prev))
    if not new and not prev:  # no substitution going: 'use the second one' is a result, 'yes' answers nothing here
        if sb["option"]:
            return ses._run(text, finish({"intent": "recipe_detail",
                                          "target": {"kind": "result_index", "value": str(sb["option"])}}))
        return ses._run(text, finish({"intent": "clarify"}))
    if sb["remove_tags"] and not sb["remove"] and not prev and not st.selected_recipe_id and \
            st.active_task in ("search", "match"):  # 'make it vegetarian' after a search: a filter on that search
        ses.drop_conflicts = True  # (restrictions already applied); 'chicken biryani' -> 'biryani', said in the reply
        return ses._run(text, finish({"intent": st.active_task}))
    if new:
        sub = {"removes": sb["remove"], "remove_tags": sb["remove_tags"], "replace_with": sb["replace_with"] or None,
               "dish": sb["dish"], "dataset_only": sb["dataset_only"], "option": sb["option"] or 1, "force": sb["force"],
               "rid": None}
        if prev.get("rid") and re.search(r"\b(?:too|also|as well)\b", text.lower()):  # 'remove the parmesan too'
            sub |= {"removes": list(dict.fromkeys(prev["removes"] + sb["remove"])), "rid": prev["rid"],
                    "remove_tags": list(dict.fromkeys(prev["remove_tags"] + sb["remove_tags"]))}
    else:
        sub = dict(prev, option=sb["option"] or prev["option"], force=sb["force"] or prev["force"])
        if sb["replace_with"]:
            sub["replace_with"] = sb["replace_with"]
    rid, how = (sub["rid"], "") if sub.get("rid") else _target(ses, sub)
    if not rid:
        return how, None
    res = substitute.run(ses.con, ses.ds, rid, sub["removes"], restrictions=st.exclude_tags, exclude=st.exclude,
                         replace_with=sub["replace_with"], option=sub["option"], dataset_only=sub["dataset_only"],
                         force=sub["force"], use_llm=ses.use_llm, remove_tags=sub["remove_tags"])
    ses.extra_calls += getattr(res.adaptation, "calls", [])
    st.sub = dict(sub, rid=rid)
    st.active_task, st.selected_recipe_id = "substitute", rid
    res.picked = how
    return "\n".join(notes + subview.markdown(res)), res
