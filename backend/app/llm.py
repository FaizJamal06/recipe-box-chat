"""Gemini via google-genai: one structured-JSON request, cached in data/llm_cache.sqlite (PRD 5.2).

The LLM only turns user text into a plan; it never produces dataset facts. Structured output uses
generate_content with response_mime_type='application/json' + response_json_schema (google-genai docs,
checked Nov 2026). At most 2 requests per call: the second only if the first is not a valid plan.
Only validated responses are cached, keyed by sha256(model, system, prompt, schema), so eval replays are
reproducible and cost no quota. Any failure (no key, 429, network, invalid twice) raises LLMError.
"""
import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass

from .config import LLM_CACHE

DEFAULT_MODEL = "gemini-3.5-flash-lite"
TIMEOUT_MS = 20_000


class LLMError(RuntimeError):
    """LLM unavailable or unusable; `calls` holds the requests already made (for the per-turn report)."""

    def __init__(self, msg: str, calls: list | None = None):
        super().__init__(msg)
        self.calls = calls or []


@dataclass
class Call:
    """One request: network latency in ms (0 for a cache hit)."""
    cached: bool
    ms: int


def model() -> str:
    return os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL


def available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


_client = None


def _remote(system: str, prompt: str, schema: dict) -> str:
    """The network request (patched in tests). Raises LLMError with the HTTP code on API errors."""
    global _client
    from google import genai
    from google.genai import errors, types
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                               http_options=types.HttpOptions(timeout=TIMEOUT_MS,
                                                              retry_options=types.HttpRetryOptions(attempts=1)))
    try:
        r = _client.models.generate_content(model=model(), contents=prompt, config=types.GenerateContentConfig(
            system_instruction=system, response_mime_type="application/json", response_json_schema=schema,
            temperature=0))
    except errors.APIError as e:
        raise LLMError(f"HTTP {e.code} {e.status or ''}".strip()) from e
    except Exception as e:  # network/timeout: the caller falls back to the rule planner
        raise LLMError(type(e).__name__) from e
    return r.text or ""


def _db() -> sqlite3.Connection:
    LLM_CACHE.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(LLM_CACHE)
    con.execute("CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, model TEXT, response TEXT)")
    return con


def generate_json(system: str, prompt: str, schema: dict, validate) -> tuple[object, list[Call]]:
    """validate(json.loads(text)) for the first valid response (cache, then up to 2 requests)."""
    if not available():
        raise LLMError("no GEMINI_API_KEY")
    key = hashlib.sha256(json.dumps([model(), system, prompt, schema], sort_keys=True).encode()).hexdigest()
    con = _db()
    try:
        row = con.execute("SELECT response FROM cache WHERE key = ?", (key,)).fetchone()
        if row:
            return validate(json.loads(row[0])), [Call(True, 0)]
        calls = []
        for _ in range(2):
            t = time.perf_counter()
            try:
                text = _remote(system, prompt, schema)
            except LLMError as e:
                calls.append(Call(False, round((time.perf_counter() - t) * 1000)))
                raise LLMError(str(e), calls) from e
            calls.append(Call(False, round((time.perf_counter() - t) * 1000)))
            try:
                out = validate(json.loads(text))
            except (ValueError, TypeError, KeyError):
                continue
            con.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, model(), text))
            con.commit()
            return out, calls
        raise LLMError("invalid plan JSON twice", calls)
    finally:
        con.close()
