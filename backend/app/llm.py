"""Gemini via google-genai: one structured-JSON request, cached in data/llm_cache.sqlite (PRD 5.2).

The LLM only turns user text into a plan; it never produces dataset facts. Structured output uses
generate_content with response_mime_type='application/json' + response_json_schema (google-genai docs,
checked Nov 2026). At most 2 requests per call: the second only if the first is not a valid plan.
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
from dataclasses import dataclass

from .config import LLM_CACHE

DEFAULT_MODEL = "gemini-3.5-flash-lite"
TIMEOUT_MS = 6_000  # past this the turn falls back to the rule parser (a slow free-tier reply is worse than rules)
log = logging.getLogger("recipebox.llm")
THINKING = "minimal"  # lowest level gemini-3.5-flash-lite supports (it cannot be fully off); docs checked Nov 2026


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


def _request(system: str, prompt: str, schema: dict):
    from google.genai import types
    return _get_client().models.generate_content(model=model(), contents=prompt, config=types.GenerateContentConfig(
        system_instruction=system, response_mime_type="application/json", response_json_schema=schema,
        temperature=0, thinking_config=types.ThinkingConfig(thinking_level=THINKING)))


def _warm() -> None:
    """Build the client, then open the HTTPS connection with a metadata call (not a generation request)."""
    _get_client().models.get(model=model())


def warm():
    """Start importing google-genai, building the client and connecting (call at startup); returns the
    Future, or None without a key. Startup waits on it so that cost never lands in a turn's 6 s budget."""
    return _pool.submit(_warm) if available() else None


def _remote(system: str, prompt: str, schema: dict, timeout_ms: int | None = None) -> tuple[str, dict]:
    """The network request (patched in tests): (text, token usage). Raises LLMError on API errors / timeout.
    Client setup and request both run in a worker, so nothing waits longer than the timeout (TIMEOUT_MS by
    default); a request still running then finishes in its thread and is discarded."""
    timeout_ms = timeout_ms or TIMEOUT_MS
    fut = _pool.submit(_request, system, prompt, schema)
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
            return validate(json.loads(row[0])), [Call(True, 0, label=label)]
        calls = []
        for _ in range(attempts):
            t = time.perf_counter()
            try:
                text, usage = _remote(system, prompt, schema, timeout_ms)
            except LLMError as e:
                calls.append(Call(False, round((time.perf_counter() - t) * 1000), error=error_kind(str(e)), label=label))
                log.warning("LLM %s call failed: %s (%s)", label, error_kind(str(e)), e)
                raise LLMError(str(e), calls) from e
            calls.append(Call(False, round((time.perf_counter() - t) * 1000), label=label, **usage))
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
