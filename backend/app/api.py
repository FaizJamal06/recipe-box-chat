"""FastAPI app (PRD 7): chat, recipe, session state/reset, health; serves the built UI from frontend/dist.

Sessions live in memory (dict + 30 min TTL, oldest evicted past MAX_SESSIONS) with a per-session rate limit
of RATE messages per minute to protect the free LLM key. One worker shares one read-only SQLite connection,
so engine calls run under a single lock. llm.warm() starts at startup on a pool thread: /api/health answers
at once and the first chat turn doesn't pay google-genai's ~6 s import + connect.
Run: python -m uvicorn app.api:app --app-dir backend --port 8000
"""
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import llm, talk, voice, web
from .config import DB, ROOT
from .db import connect, fingerprint, load_dataset
from .session import Session, SessionState

TTL_S, MAX_SESSIONS, RATE = 30 * 60, 500, 10
DIST = ROOT / "frontend" / "dist"
ENGINE = Lock()  # ponytail: one lock for the shared connection; per-session connections if traffic grows
APP: dict = {}  # con, ds, health, warm (set at startup)


@dataclass
class Entry:
    session: Session
    last: float = field(default_factory=time.time)
    times: deque = field(default_factory=deque)  # message timestamps in the last minute
    prev_total: int | None = None  # eligible count of the previous search/match, for the trace


SESSIONS: dict[str, Entry] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Open the DB and load counts once; start warming the LLM client in the background."""
    if DB.exists():
        APP["con"] = con = connect(DB)
        APP["ds"] = load_dataset(con)
        rows = con.execute("SELECT source, COUNT(*), SUM(valid) FROM recipes GROUP BY source ORDER BY source")
        APP["health"] = {"sources": {s: {"records": n, "valid": v} for s, n, v in rows}, "fingerprint": fingerprint(con)}
    APP["warm"] = llm.warm()
    yield
    if "con" in APP:
        APP["con"].close()


app = FastAPI(title="Recipe Box", lifespan=lifespan)


class ChatIn(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=1000)


class StateIn(BaseModel):
    op: str  # 'remove' | 'set'
    field: str
    value: Any = None


def _entry(sid: str | None, create: bool = True) -> tuple[str, Entry]:
    """Session by id (expired ones are dropped); a new one when missing and create=True."""
    if "con" not in APP:
        raise HTTPException(503, "recipes.db not found; build it with: python -m backend.app.ingest")
    now = time.time()
    for k in [k for k, e in SESSIONS.items() if now - e.last > TTL_S]:
        del SESSIONS[k]
    if sid in SESSIONS:
        SESSIONS[sid].last = now
        return sid, SESSIONS[sid]
    if not create:
        raise HTTPException(404, "session expired or unknown; start a new chat")
    if len(SESSIONS) >= MAX_SESSIONS:
        del SESSIONS[min(SESSIONS, key=lambda k: SESSIONS[k].last)]
    sid = sid or uuid.uuid4().hex
    SESSIONS[sid] = Entry(Session(APP["con"], APP["ds"]))
    return sid, SESSIONS[sid]


def _state(s: SessionState) -> dict:
    return {"active_task": s.active_task, "query_text": s.query_text or s.query_label, "include": s.include,
            "exclude": s.exclude,
            "exclude_tags": s.exclude_tags, "max_steps": s.max_steps, "have": s.have, "prefs": s.prefs,
            "staples": "no_staples" not in s.prefs, "strict_may_contain": s.strict_may_contain,
            "selected_recipe_id": s.selected_recipe_id, "last_results": s.last_results}


def _label(turn) -> str:
    """The planner badge text (shown whenever the LLM did not plan the turn)."""
    i = turn.info
    if turn.plan.get("keyword"):
        return "LLM unavailable, ran as keyword search"
    if i.source == "rule":
        kind = llm.error_kind(i.reason) if i.calls else ("off" if i.reason == "LLM disabled" else "no key")
        return "LLM quota reached · rule parser" if kind == "quota" else f"rule parser · LLM {kind}"
    return {"llm": f"LLM · {llm.model()}", "rule_direct": "rule parser · high-confidence pattern",
            "guard": "guard · no LLM needed", "ui": "chip change"}[i.source]


def _response(sid: str, e: Entry, turn, text: str = "") -> dict:
    """The chat response shape (also returned by PATCH state): template, payload, optional voice, suggestions."""
    s = e.session
    md, payload = web.view(turn, s)
    voice_text, vcalls, vstatus = None, [], "template (LLM not used this turn)"
    used = sum(not c.cached for c in turn.info.calls)
    llm_ok = s.use_llm and llm.available() and turn.info.source != "rule" and not any(c.error for c in turn.info.calls)
    if llm_ok and used < 2 and text:  # <= 2 LLM calls per turn, planner (+cuisine) first
        voice_text, vcalls, vstatus = voice.speak(text, payload, s.state.chips(), turn.notes)
    elif llm_ok and text:
        vstatus = "template (LLM call budget used)"
    tr = web.trace(turn, s, payload, e.prev_total, vcalls, vstatus)
    if payload["type"] in ("search", "match"):
        e.prev_total = payload["total"]
    i = turn.info
    kind = {"llm": "llm", "guard": "guard", "ui": "ui"}.get(i.source, "rule")
    calls = [*i.calls, *vcalls]
    return {"session_id": sid, "reply_md": md, "voice": voice_text, "payload": payload, "state": _state(s.state),
            "trace": tr, "suggestions": talk.suggestions(s.state, payload, turn.plan, s.conflict),
            "planner": {"kind": kind, "detail": i.source, "label": _label(turn), "reason": i.reason,
                        "calls": sum(not c.cached for c in calls), "cache_hits": sum(c.cached for c in calls),
                        "ms": sum(c.ms for c in calls), "prompt_tokens": sum(c.prompt_tokens for c in calls),
                        "errors": [c.error for c in calls if c.error], "turn_ms": turn.ms,
                        "model": llm.model() if any(not c.error for c in calls) and calls else None}}


@app.post("/api/chat")
def chat(body: ChatIn):
    """One user message -> templated reply, payload, state and trace."""
    sid, e = _entry(body.session_id)
    now = time.time()
    while e.times and now - e.times[0] > 60:
        e.times.popleft()
    if len(e.times) >= RATE:
        return JSONResponse({"error": f"Slow down: at most {RATE} messages per minute per session."}, 429)
    e.times.append(now)
    with ENGINE:
        turn = e.session.respond(body.message.strip())
        return _response(sid, e, turn, body.message.strip())


@app.get("/api/recipe/{rid:path}")
def get_recipe(rid: str):
    """Original recipe, parsed lines and tags (no session needed)."""
    if "con" not in APP:
        raise HTTPException(503, "recipes.db not found")
    with ENGINE:
        r = web.recipe(APP["con"], rid)
    if not r:
        raise HTTPException(404, f"no recipe with id {rid}")
    return r


@app.patch("/api/session/{sid}/state")
def patch_state(sid: str, body: StateIn):
    """Chip removal / toggles; then the active task re-runs and the full chat response is returned."""
    sid, e = _entry(sid, create=False)
    s = e.session.state
    lists = {"exclude": s.exclude, "exclude_tags": s.exclude_tags, "have": s.have, "prefs": s.prefs,
             "include": s.include}
    if body.op == "remove" and body.field in lists:
        lst = lists[body.field]
        if body.value not in lst:
            raise HTTPException(400, f"{body.value!r} is not in {body.field}")
        lst.remove(body.value)
    elif body.op == "remove" and body.field in ("max_steps", "query_text"):
        setattr(s, body.field, None)
        if body.field == "query_text":
            s.query_any, s.query_label = [], None
    elif body.op == "set" and body.field == "strict_may_contain":
        s.strict_may_contain = bool(body.value)
    elif body.op == "set" and body.field == "staples":
        s.prefs = [p for p in s.prefs if p != "no_staples"] + ([] if body.value else ["no_staples"])
    else:
        raise HTTPException(400, f"unsupported change: {body.op} {body.field}")
    with ENGINE:
        return _response(sid, e, e.session.rerun())


@app.post("/api/session/{sid}/reset")
def reset(sid: str):
    """Forget the conversation and every restriction."""
    sid, e = _entry(sid)
    e.session.state, e.prev_total = SessionState(), None
    return {"session_id": sid, "state": _state(e.session.state)}


@app.get("/api/health")
def health() -> dict:
    """DB counts + build fingerprint + LLM status; answers immediately (LLM warm-up runs in the background)."""
    h, w = APP.get("health", {}), APP.get("warm")
    status = ("not configured" if w is None else "warming up" if not w.done() else
              "ready" if not w.exception() else f"unreachable ({type(w.exception()).__name__})")
    src = h.get("sources", {})
    return {"status": "ok" if h else "error", "sources": src, "total": sum(x["records"] for x in src.values()),
            "valid": sum(x["valid"] for x in src.values()), "fingerprint": h.get("fingerprint", {}),
            "llm": {"model": llm.model() if w else None, "status": status}, "sessions": len(SESSIONS)}


if DIST.exists():  # the built UI; API routes above take precedence
    app.mount("/", StaticFiles(directory=DIST, html=True), name="ui")
