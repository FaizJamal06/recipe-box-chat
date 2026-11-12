"""One substitution turn inside a Session: resolve the target recipe, keep the substitution in the sticky state,
and re-run it when restrictions change.

Target: the selected recipe (when it matches the named dish, or no dish is named) -> else a search for the named
dish that must contain the removed item, and the reply says which recipe id was picked -> else one short question.
The substitution persists in state.sub: "I'm also allergic to tree nuts" re-grades it, "use the second option"
switches the candidate, "adapt it anyway" forces a caveated adaptation, "replace butter with oil" starts a new pair.
"""
import re

from . import evidence, search, stats, substitute, subview
from . import normalize as nz
from .planner import finish


def _target(ses, sub: dict) -> tuple[str | None, str]:
    """(recipe id, note on how it was picked) or (None, question)."""
    st, con, items = ses.state, ses.con, sub["removes"]
    sel = st.selected_recipe_id or (st.last_results[0] if len(st.last_results) == 1 else None)
    dish = sub["dish"]
    if sel and (not dish or all(w in " ".join(_title(con, sel)).lower() for w in dish.split())):
        return sel, ""
    if not dish:
        return None, "Which recipe should I change? Open one first (e.g. 'show me the first one'), or name the dish."
    include = []
    for w in items[:1]:
        try:
            include = [stats.term(w, ses.ds)]
        except stats.UnknownIngredient:
            pass
    hits = search.search(con, dish, include=include, limit=20).hits or search.search(con, dish, limit=20).hits
    head = re.compile(rf"\b{re.escape(dish)}(?:\s+[ivx\d]+)?$", re.I)  # 'Banana Bread II', not 'Banana Bread French Toast'
    heads = [h for h in hits if head.search(evidence.head(h.title))] or hits
    item = re.compile(rf"\b{re.escape(nz.singular(items[0].lower())[:5])}", re.I) if items else None  # cream -> creamy
    heads = [h for h in heads if item and item.search(h.title)] or heads  # the item matters in this dish
    ctx = evidence.contexts(con)
    usual = max(set(c := [ctx.get(h.id) for h in heads]), key=c.count) if heads else None  # the dish's usual context
    hit = next((h for h in heads if ctx.get(h.id) == usual), None)
    if not hit:
        return None, f"I couldn't find a {dish} recipe. Which recipe do you mean?"
    return hit.id, (f"I picked `{hit.id}` '{hit.title.strip()}', the top match for '{dish}'"
                    + (f" that contains {items[0]}" if include else "") + ". Open another recipe to switch.")


def _title(con, rid: str) -> tuple[str, str]:
    """(title, ingredients_raw): 'this pasta recipe' still means the selected 'Penne in Cream Sauce'."""
    return con.execute("SELECT title, ingredients_raw FROM recipes WHERE id = ?", (rid,)).fetchone() or ("", "")


def _dish(con, rid: str, dish: str) -> str | None:
    """The user's dish words for L1 only when the title has them (else the title's own head words are more exact)."""
    return dish if dish and all(w in _title(con, rid)[0].lower() for w in dish.split()) else None


def handle(ses, text: str, p: dict, notes: list[str]) -> tuple[str, object]:
    """Run (or re-run) the substitution for this turn; returns (reply text, substitute.Result or None)."""
    st, sb, prev = ses.state, p["substitution"], ses.state.sub or {}
    new = bool(sb["remove"] or sb["remove_tags"] or (sb["replace_with"] and not prev))
    if not new and not prev:  # no substitution going: 'use the second one' is a result, 'yes' answers nothing here
        if sb["option"]:
            return ses._run(text, finish({"intent": "recipe_detail",
                                          "target": {"kind": "result_index", "value": str(sb["option"])}}))
        return ses._run(text, finish({"intent": "clarify"}))
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
                         force=sub["force"], use_llm=ses.use_llm, dish=_dish(ses.con, rid, sub["dish"]),
                         remove_tags=sub["remove_tags"], budget=max(1, 2 - ses.plan_calls))
    ses.extra_calls += getattr(res.adaptation, "calls", [])
    st.sub = dict(sub, rid=rid)
    st.active_task, st.selected_recipe_id = "substitute", rid
    res.picked = how
    return "\n".join(notes + subview.markdown(res)), res
