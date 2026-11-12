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

from . import compose, guard, llm, match, search, stats, subflow, talk
from . import normalize as nz
from .db import Dataset
from .planner import PlanInfo, finish, plan as make_plan
from .rules import DIETS, TAG_LABEL, TAG_WORDS, diets_in, rule_plan, target as rule_target
from .state import SessionState  # noqa: F401 (re-exported)

HELP = ("I can answer, for example: 'How many recipes contain garlic and onion?', 'Among recipes containing "
        "tomato, which five have the fewest steps?', 'Find a penne pasta recipe', 'I cannot have dairy', "
        "'I have eggs, onions and rice', 'show me the steps for the second one'.")


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
        if self.plan.get("keyword"):
            src = f"LLM unavailable ({self.info.reason}), ran as keyword search"
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
        self.ref_id: str | None = None  # recipe an unsupported-attribute / "why" question referred to
        self.last_res = None  # last search/match/rank result, for "why did you pick this one?"
        self.extra_calls: list = []  # LLM calls made inside the executor (cuisine dish names)
        self.conflict: tuple | None = None  # (tag, dish word) when the request contradicts a restriction

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
        t0, self.notes, self.ref_id, self.extra_calls, self.conflict = time.perf_counter(), [], None, [], None
        attr = guard.check(text)
        if attr:
            p = finish({"intent": "cuisine"} if attr == "cuisine" else
                       {"intent": "unsupported", "unsupported": {"attribute": attr}})
            info = PlanInfo("guard")
        else:
            known = lambda w: w.lower() in TAG_WORDS or (_key(w) or ("",))[0] in self.ds.vocab
            p, info = make_plan(text, self.state, self.use_llm, known)
        try:
            reply, res = self._run(text, p)
        except stats.UnknownIngredient as e:
            reply, res = f"I don't recognise '{e}' as an ingredient in this dataset. {HELP}", None
        info.calls += self.extra_calls
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

    def _apply(self, d: dict, text: str = "") -> list[str]:
        """Merge a state_patch into the sticky state; returns notes for the reply. Diet presets named in the
        plan or the text (rules.diets_in) add their tags, and the reply states each expansion once."""
        s, notes = self.state, []
        if d["mode"] == "new" and (d["query_text"] or d["have_set"] or d.get("reset")):
            kept = s.exclude_tags + s.exclude + ([f"max {s.max_steps} steps"] if s.max_steps is not None else [])
            if kept and not s.kept_note:
                notes.append(f"Kept your restrictions ({', '.join(kept)}): they're about you, not the dish. Say e.g. "
                             "'dairy is fine now' to drop one.")
                s.kept_note = True
            s.query_text, s.include, s.query_any, s.query_label = None, [], [], None
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
        for name in dict.fromkeys([*d.get("diets_add", []), *diets_in(text)]):
            tags = DIETS[name]["tags"]
            if set(tags) & set(rm_tags):  # 'vegan is fine now'
                continue
            s.exclude_tags += [t for t in tags if t not in s.exclude_tags]
            if name not in s.diets:
                notes.append(f"{name[0].upper() + name[1:]} → " + (f"no {', '.join(TAG_LABEL.get(t, t) for t in tags)}."
                             if tags else "no filter.") + (f" {DIETS[name]['note']}" if DIETS[name].get("note") else ""))
                s.diets += [name] if tags else []
        s.diets = [n for n in s.diets if set(DIETS[n]["tags"]) <= set(s.exclude_tags)]  # a removed tag ends the preset
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
        if intent == "smalltalk":
            return talk.smalltalk(p["talk"], ds.valid), None
        if intent == "offtopic":
            return talk.OFFTOPIC, None
        if intent == "clarify" and p["question"]:
            return talk.clarify(p["question"]), None
        if intent == "explain":
            tg = p["target"] if p["target"]["kind"] != "none" else rule_target(text.lower())
            rid = self._resolve(tg or {"kind": "result_index", "value": "1"}, text) or \
                (s.last_results[0] if s.last_results else None)
            why = talk.explain(self.last_res, rid, s.query_text) if rid else None
            self.ref_id = rid if why else None
            return why or "I can only explain recipes from the latest results: ask e.g. 'why the second one?'", None
        if intent == "unsupported":
            attr = p["unsupported"]["attribute"]
            if attr in ("none", "other"):
                return "That isn't a field in this dataset (it has titles, ingredient lines and instructions).", None
            self.ref_id = self._resolve(p["target"], text)  # the recipe the question is about (for the UI card)
            return guard.answer(con, ds, attr, text, self.ref_id)
        if intent == "stats":
            res = stats.execute(con, ds, p)
            if getattr(res, "op", "") == "rank":  # ranked recipes can be opened / explained like search results
                self.last_res, s.last_results, s.titles = res, [r[0] for r in res.rows], {r[0]: r[1] for r in res.rows}
            return compose.stats_reply(res, ds, p), res
        if intent == "recipe_detail":
            rid = self._resolve(p["target"], text)
            if not rid:
                return "Which recipe? Say e.g. 'the second one' after a search, or search first.", None
            s.selected_recipe_id = rid
            terms = lambda ws: [stats.term(w, ds) for w in ws]
            ev = search.evidence(con, rid, terms(s.include), terms(s.exclude), s.exclude_tags, s.max_steps)
            return compose.detail_reply(con, rid, ev), rid
        d, pre = p["state_patch"], []
        if intent == "cuisine":  # no cuisine field: labelled title-keyword proxy, with the session's restrictions
            c = guard.cuisine_of(text)
            base, extra, self.extra_calls = guard.cuisine_keywords(c, self.use_llm)
            rp = finish(rule_plan(text))["state_patch"]  # 'italian recipes without meat': keep the restriction
            pre = self._apply({**rp, "mode": "new", "query_text": "_", "have_set": []}, text)  # new dish, keeps restrictions
            d = finish({})["state_patch"]  # already applied
            s.query_text, s.query_any, s.query_label, intent = None, base + extra, f"{c} (title keywords)", "search"
            s.active_task = "search"
            pre.append(f"There's no cuisine field in this dataset, so '{c}' is approximated by recipe titles "
                       f"containing: {', '.join(base)}" + (f"; plus dish names suggested by the LLM: {', '.join(extra)}"
                                                            if extra else "") + ". Dishes not named that way are missed.")
        if intent == "substitute":
            self.notes = self._apply(p["state_patch"], text)
            return subflow.handle(self, text, p, self.notes)
        if intent not in ("search", "match"):
            return HELP, None
        if not d["query_text"] and not d["have_set"] and s.active_task and not p["keyword"] and not d.get("reset"):
            intent = s.active_task  # a bare restriction re-runs the current task
        notes = self.notes = pre + self._apply(d, text)
        if intent == "substitute":  # 'I'm also allergic to tree nuts' re-grades the current substitution
            return subflow.handle(self, text, finish({"intent": "substitute"}), notes)
        if p["keyword"]:
            notes.append(f"I couldn't use the language model, so I ran your message as a keyword search for "
                         f"'{d['query_text']}' in titles and ingredients.")
        terms = lambda ws: [stats.term(w, ds) for w in ws]
        s.active_task = intent
        self.conflict = self._conflict() if intent == "search" else None
        if self.conflict:  # 'vegan chicken curry': ask one short question instead of guessing
            tag, word = self.conflict
            return (f"“{s.query_text}” clashes with your restriction “no {tag}” ({word} contains {tag}). Should I "
                    f"look for a version without {word}, or drop the “no {tag}” restriction?"), None
        if intent == "match":
            if not s.have:
                return "Tell me which ingredients you have, e.g. 'I have eggs, rice and onions'.", None
            res = match.match(con, ds, s.have, terms(s.exclude), s.exclude_tags, s.max_steps, s.strict_may_contain,
                              s.prefs, s.limit or 5, () if "no_staples" in s.prefs else match.STAPLES)
            rows = res.rows + res.more  # display order: fully verified first
            reply = compose.match_reply(res, ds)
        else:
            run = lambda q: search.search(con, q or "", terms(s.include), terms(s.exclude), s.exclude_tags,
                                          s.max_steps, s.strict_may_contain, s.limit or 10, s.query_any)
            res = run(s.query_text)
            fixed = search.correct(s.query_text, ds.vocab) if not res.total and s.query_text and not p["keyword"] else None
            if fixed and fixed != s.query_text and (res2 := run(fixed)).total:
                notes.append(f"No recipes match '{s.query_text}', so I'm showing results for '{fixed}' "
                             "(spelling corrected).")
                s.query_text, res = fixed, res2
            elif p["keyword"] and not res.total:
                notes.append("No recipe matches those words, and without the language model I can't tell what you "
                             "meant. I can only help with recipes: try 'find a pasta recipe' or 'I have eggs and rice'.")
            rows = res.hits + res.more  # display order: fully verified first
            reply = compose.search_reply(res, ds)
        self.last_res, s.last_results, s.titles = res, [r.id for r in rows], {r.id: r.title for r in rows}
        return "\n".join(notes + [reply]), res

    def _conflict(self) -> tuple[str, str] | None:
        """('meat and poultry', word) when a dish word is an animal product the restrictions exclude ('vegan chicken
        curry'). Only animal tags: 'gluten-free pasta' or 'dairy-free cheese' are real products, not contradictions."""
        s = self.state
        for w in (s.query_text or "").split():
            tags = [t for t, lv in nz.tags_for(w) if lv == "contains" and t in s.exclude_tags
                    and t in ("meat", "pork", "poultry", "fish", "shellfish")]
            if tags:
                return " and ".join(tags), w
        return None


def respond(con: sqlite3.Connection, ds: Dataset, text: str, use_llm: bool = True) -> tuple[str, dict, object]:
    """(reply, plan, result) for a single message in a fresh session (used by eval/oracle.py)."""
    t = Session(con, ds, use_llm).respond(text)
    return t.reply, t.plan, t.result
