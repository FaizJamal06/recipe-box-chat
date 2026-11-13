"""Gemini via google-genai: one structured-JSON request, cached in data/llm_cache.sqlite (PRD 5.2).

The LLM only turns user text into a plan; it never produces dataset facts. Structured output uses
generate_content with response_mime_type='application/json' + response_json_schema (google-genai docs,
checked Nov 2026). At most 2 requests per call: the second only if the first is not a valid plan, and at most
MAX_PER_TURN (2) LLM answers per conversation turn across planner, executor and voice (begin_turn / _spend).
Only validated responses are cached, keyed by sha256(model, system, prompt, schema), so eval replays are
reproducible and cost no quota. Any failure (no key, 429, network, > TIMEOUT_MS, invalid twice) raises LLMError.
"""
import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextlib import contextmanager
from dataclasses import dataclass

from .config import LLM_CACHE

DEFAULT_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.5-flash"  # one retry on 503/504 when the call's time budget allows (GEMINI_FALLBACK_MODEL)
FALLBACK_MIN_MS = 2_500  # below this much budget left, a second model can't answer in time: fail fast instead
TIMEOUT_MS = 6_000  # past this the turn falls back to the rule parser (a slow free-tier reply is worse than rules)
log = logging.getLogger("recipebox.llm")
THINKING = "minimal"  # lowest level gemini-3.5-flash-lite supports (it cannot be fully off); docs checked Nov 2026
MAX_PER_TURN = 2  # PRD: at most 2 LLM answers per turn, retries, fallbacks and cache hits included
_turn = threading.local()  # one API request = one thread (planner, executor and voice), so the budget is per turn


@contextmanager
def turn():
    """One conversation turn's LLM budget. Nested use is a no-op, so api.chat's block (planner + executor + voice)
    contains Session.respond's; outside any turn (tests, scripts) nothing is counted."""
    if getattr(_turn, "n", None) is not None:
        yield
        return
    _turn.n = 0
    try:
        yield
    finally:
        _turn.n = None


def _spend(calls: list) -> None:
    """Take one LLM answer from the turn's budget, or raise LLMError when it is used up."""
    n = getattr(_turn, "n", None)
    if n is not None and n >= MAX_PER_TURN:
        raise LLMError(f"turn budget: {MAX_PER_TURN} LLM calls already used", calls)
    if n is not None:
        _turn.n = n + 1


class LLMError(RuntimeError):
    """LLM unavailable or unusable; `calls` holds the requests already made (for the per-turn report)."""

    def __init__(self, msg: str, calls: list | None = None):
        super().__init__(msg)
        self.calls = calls or []


@dataclass
class Call:
    """One request: network latency in ms (0 for a cache hit) and token usage reported by the API."""
    cached: bool
    ms: int
    prompt_tokens: int = 0
    thought_tokens: int = 0
    output_tokens: int = 0
    error: str = ""  # '' ok | timeout | quota (429) | overloaded (503) | invalid | error
    label: str = ""  # planner | voice | cuisine


def model() -> str:
    return os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL


def fallback_model() -> str:
    return os.environ.get("GEMINI_FALLBACK_MODEL", FALLBACK_MODEL)


def available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


_client = None
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=2)  # runs the request so the turn can stop waiting at TIMEOUT_MS


def _get_client():
    """The shared client; importing google-genai + building it takes ~6 s, so warm() does it at startup."""
    global _client
    with _lock:  # warm() and a first request can race; build one client
        if _client is None:
            from google import genai
            from google.genai import types
            # the API rejects deadlines under 10 s (HTTP 400); the 6 s limit is enforced in _remote instead
            _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(
                timeout=10_000, retry_options=types.HttpRetryOptions(attempts=1)))
    return _client


def _request(system: str, prompt: str, schema: dict, model_name: str | None = None):
    from google.genai import types
    return _get_client().models.generate_content(model=model_name or model(), contents=prompt, config=types.GenerateContentConfig(
        system_instruction=system, response_mime_type="application/json", response_json_schema=schema,
        temperature=0, thinking_config=types.ThinkingConfig(thinking_level=THINKING)))


def _warm() -> None:
    """Build the client, then open the HTTPS connection with a metadata call (not a generation request)."""
    _get_client().models.get(model=model())


def warm():
    """Start importing google-genai, building the client and connecting (call at startup); returns the
    Future, or None without a key. Startup waits on it so that cost never lands in a turn's 6 s budget."""
    return _pool.submit(_warm) if available() else None


def _remote(system: str, prompt: str, schema: dict, timeout_ms: int | None = None,
            model_name: str | None = None) -> tuple[str, dict]:
    """The network request (patched in tests): (text, token usage). Raises LLMError on API errors / timeout.
    Client setup and request both run in a worker, so nothing waits longer than the timeout (TIMEOUT_MS by
    default); a request still running then finishes in its thread and is discarded."""
    timeout_ms = timeout_ms or TIMEOUT_MS
    fut = _pool.submit(_request, system, prompt, schema, model_name)
    try:
        r = fut.result(timeout=timeout_ms / 1000)
    except FutureTimeout as e:
        raise LLMError(f"timeout > {timeout_ms / 1000:g} s") from e
    except Exception as e:  # google.genai APIError carries .code/.status; anything else is network
        code = getattr(e, "code", None)
        raise LLMError(f"HTTP {code} {getattr(e, 'status', '') or ''}".strip() if isinstance(code, int)
                       else f"{type(e).__name__}: {str(e)[:80]}") from e
    u = r.usage_metadata
    usage = {"prompt_tokens": u.prompt_token_count or 0, "thought_tokens": u.thoughts_token_count or 0,
             "output_tokens": u.candidates_token_count or 0} if u else {}
    return r.text or "", usage


def _db() -> sqlite3.Connection:
    LLM_CACHE.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(LLM_CACHE)
    con.execute("CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, model TEXT, response TEXT)")
    return con


def error_kind(msg: str) -> str:
    """Short error class for logs and the UI badge: timeout / quota (429) / overloaded (503) / other."""
    return ("timeout" if msg.startswith("timeout") else "quota" if "429" in msg else
            "overloaded" if "503" in msg else "invalid" if msg.startswith("invalid") else "error")


def _request_once(system, prompt, schema, budget: int, t0: float, calls: list, label: str) -> tuple[str, dict]:
    """One request, plus one retry on the fallback model after a 503/504 if >= FALLBACK_MIN_MS of the budget is
    left. Appends a Call per request; raises LLMError (with the calls) when nothing answered."""
    for name in (None, fallback_model()):
        t, ms = time.perf_counter(), max(1, round(budget - (time.perf_counter() - t0) * 1000))
        _spend(calls)
        try:
            text, usage = _remote(system, prompt, schema, ms, name) if name else _remote(system, prompt, schema, ms)
        except LLMError as e:
            calls.append(Call(False, round((time.perf_counter() - t) * 1000), error=error_kind(str(e)),
                              label=label + (" (fallback)" if name else "")))
            log.warning("LLM %s call failed: %s (%s)", label, error_kind(str(e)), e)
            left = budget - (time.perf_counter() - t0) * 1000
            if name or not ("503" in str(e) or "504" in str(e)) or left < FALLBACK_MIN_MS or not fallback_model() \
                    or (getattr(_turn, "n", None) or 0) >= MAX_PER_TURN:
                raise LLMError(str(e), calls) from e
            continue
        calls.append(Call(False, round((time.perf_counter() - t) * 1000), label=label + (" (fallback)" if name else ""),
                          **usage))
        return text, usage


def generate_json(system: str, prompt: str, schema: dict, validate, timeout_ms: int | None = None,
                  attempts: int = 2, label: str = "planner") -> tuple[object, list[Call]]:
    """validate(json.loads(text)) for the first valid response: cache first, then up to `attempts` requests
    (the 2nd only when the 1st is invalid). Each failed request is logged with its error kind."""
    if not available():
        raise LLMError("no GEMINI_API_KEY")
    key = hashlib.sha256(json.dumps([model(), system, prompt, schema], sort_keys=True).encode()).hexdigest()
    con = _db()
    try:
        row = con.execute("SELECT response FROM cache WHERE key = ?", (key,)).fetchone()
        if row:
            _spend([])
            return validate(json.loads(row[0])), [Call(True, 0, label=label)]
        if os.environ.get("LLM_REPLAY"):  # eval --replay: cache only, never the network
            raise LLMError("replay: not in the LLM cache")
        calls, budget = [], timeout_ms or TIMEOUT_MS
        for _ in range(attempts):  # each attempt has the full budget; a fallback shares its attempt's budget
            text, usage = _request_once(system, prompt, schema, budget, time.perf_counter(), calls, label)
            try:
                out = validate(json.loads(text))
            except (ValueError, TypeError, KeyError) as e:
                calls[-1].error = "invalid"
                log.warning("LLM %s call returned invalid output: %s", label, e)
                continue
            con.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, model(), text))
            con.commit()
            return out, calls
        raise LLMError(f"invalid {label} output", calls)
    finally:
        con.close()
