"""One conversation turn: guard -> plan -> sticky state (PRD 5.1) -> executor -> templated reply.

Rules: a new restriction adds to the state and re-runs the active task (search or match); it is removed only
when the user says so ("dairy is fine now"). A new dish or a new have-list resets query/include but keeps the
restrictions (they are about the person, not the dish), said once. "The second one" / "this recipe" resolve
from last_results / selected_recipe_id only, so a recipe id the planner made up is never used.
The CLI, the API and eval/oracle.py all go through Session.respond (respond() = a fresh one-turn session).
"""
import sqlite3
import time
from dataclasses import dataclass, field

from . import compose, guard, llm, match, search, stats
from . import normalize as nz
from .db import Dataset
from .planner import PlanInfo, finish, plan as make_plan
from .rules import TAG_WORDS, target as rule_target

HELP = ("I can answer, for example: 'How many recipes contain garlic and onion?', 'Among recipes containing "
        "tomato, which five have the fewest steps?', 'Find a penne pasta recipe', 'I cannot have dairy', "
        "'I have eggs, onions and rice', 'show me the steps for the second one'.")


@dataclass
class SessionState:
    """Sticky conversation state (PRD 5.1); shown to the user as chips."""
    active_task: str | None = None  # 'search' | 'match' (what a new restriction re-runs)
    query_text: str | None = None
    include: list = field(default_factory=list)
    exclude: list = field(default_factory=list)  # plain words, canonicalized at execution
    exclude_tags: list = field(default_factory=list)
    max_steps: int | None = None
    have: list = field(default_factory=list)  # as typed, quantities included ("2 eggs")
    prefs: list = field(default_factory=list)  # use_most / fewest_extra / fewest_steps / no_staples
    limit: int | None = None
    strict_may_contain: bool = False
    last_results: list = field(default_factory=list)  # recipe ids in displayed order
    titles: dict = field(default_factory=dict)
    selected_recipe_id: str | None = None
    history: list = field(default_factory=list)  # (user text, first reply line), last 6
    kept_note: bool = False

    @property
    def last_titles(self) -> list[tuple[str, str]]:
        return [(i, self.titles.get(i, "")) for i in self.last_results]

    def chips(self) -> str:
        """One-line view of the state."""
        c = [f"task={self.active_task}"] if self.active_task else []
        c += [f"dish='{self.query_text}'"] if self.query_text else []
        c += [f"no {x}" for x in self.exclude_tags + self.exclude]
        c += [f"max {self.max_steps} steps"] if self.max_steps is not None else []
        c += [f"have: {', '.join(self.have)}"] if self.have else []
        c += [f"prefs: {', '.join(self.prefs)}"] if self.prefs else []
        c += [f"selected: {self.selected_recipe_id}"] if self.selected_recipe_id else []
        return " · ".join(c) or "(empty)"


@dataclass
class Turn:
    """Everything one message produced, including how it was planned."""
    reply: str
    plan: dict
    result: object
    info: PlanInfo
    ms: int
    notes: list = field(default_factory=list)  # state notes ("Kept your restrictions ...") shown above the reply

    @property
    def llm_calls(self) -> int:
        return sum(not c.cached for c in self.info.calls)

    def meta(self) -> str:
        """'[planner: ... | LLM calls: n | latency]' (the visible rule-parser flag)."""
        src = {"llm": f"LLM {llm.model()}", "guard": "unsupported-attribute guard (no LLM needed)",
               "rule_direct": "rule parser (high-confidence pattern; LLM skipped)",
               "ui": "state changed in the UI (no planner)",
               "rule": f"rule parser (LLM unavailable: {self.info.reason})"}[self.info.source]
        hits = sum(c.cached for c in self.info.calls)
        llm_ms = sum(c.ms for c in self.info.calls)
        tok = sum(c.prompt_tokens for c in self.info.calls)
        tok = f", prompt {tok} tok, thoughts {sum(c.thought_tokens for c in self.info.calls)} tok" if tok else ""
        return (f"[planner: {src} | LLM calls: {self.llm_calls}{f' + {hits} cache hit' if hits else ''}, "
                f"{llm_ms} ms{tok} | turn {self.ms} ms]")


def _key(w: str) -> tuple:
    return tuple(nz.normalize(w))


class Session:
    """One user's conversation over a read-only DB connection."""

    def __init__(self, con: sqlite3.Connection, ds: Dataset, use_llm: bool = True):
        self.con, self.ds, self.use_llm, self.state = con, ds, use_llm, SessionState()
        self.notes: list[str] = []
        self.ref_id: str | None = None  # recipe an unsupported-attribute question referred to

    def rerun(self) -> Turn:
        """Re-run the active task on the current state (after a chip removal / toggle in the UI)."""
        t0, self.notes = time.perf_counter(), []
        p = finish({"intent": self.state.active_task or "clarify"})
        try:
            reply, res = self._run("", p)
        except stats.UnknownIngredient as e:
            reply, res = f"I don't recognise '{e}' as an ingredient in this dataset.", None
        return Turn(reply, p, res, PlanInfo("ui"), round((time.perf_counter() - t0) * 1000), self.notes)

    def respond(self, text: str) -> Turn:
        """Answer one message and update the state."""
        t0, self.notes, self.ref_id = time.perf_counter(), [], None
        attr = guard.check(text)
        if attr:
            p, info = finish({"intent": "unsupported", "unsupported": {"attribute": attr}}), PlanInfo("guard")
        else:
            known = lambda w: w.lower() in TAG_WORDS or (_key(w) or ("",))[0] in self.ds.vocab
            p, info = make_plan(text, self.state, self.use_llm, known)
        try:
            reply, res = self._run(text, p)
        except stats.UnknownIngredient as e:
            reply, res = f"I don't recognise '{e}' as an ingredient in this dataset. {HELP}", None
        self.state.history = (self.state.history + [(text, reply.split("\n")[0][:150])])[-6:]
        return Turn(reply, p, res, info, round((time.perf_counter() - t0) * 1000), self.notes)

    def _resolve(self, tg: dict, text: str) -> str | None:
        """Target -> a recipe id from last_results / selected only (never a planner-invented id)."""
        s = self.state
        if tg["kind"] == "none":
            tg = rule_target(text.lower()) or tg
        kind, v = tg["kind"], tg["value"].strip()
        if kind == "result_index" and v.lstrip("-").isdigit() and s.last_results:
            i = int(v)
            return s.last_results[i - 1] if 1 <= i <= len(s.last_results) else s.last_results[-1] if i == -1 else None
        if kind == "recipe_id":
            return v if v in s.last_results or v == s.selected_recipe_id else None
        if kind == "title":
            return next((i for i, t in s.last_titles if v.lower() in t.lower()), None)
        if kind == "selected":
            return s.selected_recipe_id or (s.last_results[0] if len(s.last_results) == 1 else None)
        return None

    def _apply(self, d: dict) -> list[str]:
        """Merge a state_patch into the sticky state; returns notes for the reply."""
        s, notes = self.state, []
        if d["mode"] == "new" and (d["query_text"] or d["have_set"]):
            kept = s.exclude_tags + s.exclude + ([f"max {s.max_steps} steps"] if s.max_steps is not None else [])
            if kept and not s.kept_note:
                notes.append(f"Kept your restrictions ({', '.join(kept)}): they're about you, not the dish. Say e.g. "
                             "'dairy is fine now' to drop one.")
                s.kept_note = True
            s.query_text, s.include = None, []
        if d["query_text"]:
            s.query_text = d["query_text"]
        for k in ("exclude_add", "include_add"):  # executor-side check of the planner's words
            for w in [w for w in d[k] if w.lower() not in TAG_WORDS]:
                if not _key(w):
                    notes.append(f"I couldn't read '{w}' as an ingredient, so that restriction was NOT added.")
                    d[k] = [x for x in d[k] if x != w]
                elif _key(w)[0] not in self.ds.vocab:
                    notes.append(f"'{w}' isn't a known ingredient name here; the restriction matches that exact "
                                 "name only.")
        tags = d["exclude_tags_add"] + [t for w in d["exclude_add"] if w.lower() in TAG_WORDS for t in TAG_WORDS[w.lower()]]
        s.exclude += [w for w in d["exclude_add"] if w.lower() not in TAG_WORDS and _key(w) not in map(_key, s.exclude)]
        s.include += [w for w in d["include_add"] if _key(w) not in map(_key, s.include)]
        s.exclude_tags += [t for t in tags if t not in s.exclude_tags]
        gone = set(map(_key, d["exclude_remove"]))
        rm_tags = d["exclude_tags_remove"] + [t for w in d["exclude_remove"] if w.lower() in TAG_WORDS
                                              for t in TAG_WORDS[w.lower()]]
        removed = [x for x in s.exclude if _key(x) in gone] + [t for t in s.exclude_tags if t in rm_tags]
        s.exclude = [x for x in s.exclude if _key(x) not in gone]
        s.exclude_tags = [t for t in s.exclude_tags if t not in rm_tags]
        if removed:
            notes.append(f"Removed restriction(s): {', '.join(removed)}.")
        if d["max_steps"]:
            s.max_steps = None if d["max_steps"] < 0 else d["max_steps"]
        if d["have_set"]:
            s.have, s.prefs, s.limit = list(d["have_set"]), [], None
        s.prefs += [x for x in d["prefs_add"] if x not in s.prefs]
        if d["limit"]:
            s.limit = d["limit"]
        return notes

    def _run(self, text: str, p: dict) -> tuple[str, object]:
        """Dispatch one plan; returns (reply, executor result)."""
        s, con, ds, intent = self.state, self.con, self.ds, p["intent"]
        if intent == "unsupported":
            attr = p["unsupported"]["attribute"]
            if attr in ("none", "other"):
                return "That isn't a field in this dataset (it has titles, ingredient lines and instructions).", None
            self.ref_id = self._resolve(p["target"], text)  # the recipe the question is about (for the UI card)
            return guard.answer(con, ds, attr, text, self.ref_id)
        if intent == "stats":
            return compose.stats_reply(res := execute_stats(con, ds, p), ds, p), res
        if intent == "recipe_detail":
            rid = self._resolve(p["target"], text)
            if not rid:
                return "Which recipe? Say e.g. 'the second one' after a search, or search first.", None
            s.selected_recipe_id = rid
            terms = lambda ws: [stats.term(w, ds) for w in ws]
            ev = search.evidence(con, rid, terms(s.include), terms(s.exclude), s.exclude_tags, s.max_steps)
            return compose.detail_reply(con, rid, ev), rid
        if intent not in ("search", "match"):
            return HELP, None
        d = p["state_patch"]
        if not d["query_text"] and not d["have_set"] and s.active_task:
            intent = s.active_task  # a bare restriction re-runs the current task
        notes = self.notes = self._apply(d)
        terms = lambda ws: [stats.term(w, ds) for w in ws]
        s.active_task = intent
        if intent == "match":
            if not s.have:
                return "Tell me which ingredients you have, e.g. 'I have eggs, rice and onions'.", None
            res = match.match(con, ds, s.have, terms(s.exclude), s.exclude_tags, s.max_steps, s.strict_may_contain,
                              s.prefs, s.limit or 5, () if "no_staples" in s.prefs else match.STAPLES)
            rows = res.rows
            reply = compose.match_reply(res, ds)
        else:
            res = search.search(con, s.query_text or "", terms(s.include), terms(s.exclude), s.exclude_tags,
                                s.max_steps, s.strict_may_contain, s.limit or 10)
            rows = res.hits
            reply = compose.search_reply(res, ds)
        s.last_results, s.titles = [r.id for r in rows], {r.id: r.title for r in rows}
        return "\n".join(notes + [reply]), res


def execute_stats(con: sqlite3.Connection, ds: Dataset, plan: dict):
    """Run a stats plan; returns Result(s). Raises stats.UnknownIngredient."""
    s = plan["stats"]
    if s.get("tags"):
        return stats.tag_count(con, ds, s["tags"], s["tag_mode"], "percentage" if s["op"] == "percentage" else "count")
    terms = lambda k: [stats.term(w, ds) for w in s.get(k) or []]
    f = stats.Filters(terms("all_of"), terms("any_of"), terms("none_of"), list(s.get("title_contains") or []))
    if s["op"] in ("count", "percentage"):
        return stats.count(con, ds, f, s["op"])
    if s["op"] == "rank":
        return stats.rank(con, ds, f, s["field"], s["order"], s["limit"])
    if s["op"] in ("mean", "median"):
        return stats.summary(con, ds, f, s["op"], s["field"])
    return stats.top_ingredients(con, ds, f, s["limit"])


def respond(con: sqlite3.Connection, ds: Dataset, text: str, use_llm: bool = True) -> tuple[str, dict, object]:
    """(reply, plan, result) for a single message in a fresh session (used by eval/oracle.py)."""
    t = Session(con, ds, use_llm).respond(text)
    return t.reply, t.plan, t.result
