# Commands

Every `make` target is one plain command, so it can also be run directly (shown for PowerShell / bash). Activate
the virtual environment first: `.\.venv\Scripts\Activate.ps1` (Windows) or `. .venv/bin/activate` (macOS/Linux).

## Build and run

| make target | Run directly | What it does |
|---|---|---|
| `make setup` | `python scripts/setup.py` | create `.venv`, install `requirements.txt`, `npm ci` in `frontend/` |
| `make data` | `python scripts/download.py` | download and unzip the dataset into `data/raw/` (~200 MB) |
| `make db` | `python -m backend.app.ingest` | build `data/recipes.db` (~5–7 min, peak RSS ~330 MB, ~1 GB on disk) |
| `make ui` | `cd frontend && npm ci && npm run build` | build the React UI into `frontend/dist` (served by FastAPI) |
| `make run` | `python -m uvicorn app.api:app --app-dir backend --port 8000` | serve the UI and API on http://127.0.0.1:8000 |
| `make cli` | `python -m backend.app.cli` (`--ask "..."`, `--session demos/demo1_refine.txt`, `--no-llm`) | chat in the terminal; prints the planner, LLM calls and latency per turn |
| `make docker` | `docker build -t recipe-box . && docker run --rm -p 8000:8000 recipe-box` | the production image: a node stage builds the UI, a builder stage downloads the data and builds the DB; listens on `$PORT` (default 8000) |

For UI work with hot reload: keep `make run` going and use `cd frontend && npm run dev` (http://localhost:5173,
proxies `/api`). A URL like `/?q=Find+a+penne+pasta+recipe&q=I+cannot+have+dairy` replays those messages on load;
`&dev=1` turns developer view on, `&tab=calc` picks the panel tab.

## Tests and evaluation

| make target | Run directly | What it does |
|---|---|---|
| `make test` | `python -m pytest -q -x` (from `backend/`) | unit tests, including a DB build from `backend/tests/fixtures/mini.json` |
| `make oracle` | `python eval/oracle.py` | recompute demos 2 and 3 from the raw JSON in pure Python and check the app's answers (~3 min, LLM off) |
| `make eval` | `python eval/run.py --replay` | every case in `eval/cases.yaml` through the API with cached LLM answers only; writes `eval/REPORT.md` |
| `make eval-live` | `python eval/run.py` | the same with the live LLM (uses quota; answers are cached for later replays) |
| `make baseline` | `python eval/baseline_oneshot.py` (`--replay`) | the same questions to the raw LLM with no tools, checked against the DB and the oracle |
| `make screenshots` | `node scripts/screenshots.mjs` | desktop screenshots into `docs/screenshots/` (needs `make run`) |
| `make mobile-check` | `node scripts/screenshots.mjs --mobile` | phone screenshots at 360, 390, 430 and 768 px into `docs/screenshots/mobile/`; fails if any view overflows horizontally (needs `make run`) |
| — | `python scripts/determinism.py` | build the DB twice with different hash seeds and compare fingerprints (~6 min) |

## Data and lexicon tools

| make target | Run directly | What it does |
|---|---|---|
| `make peek` | `python scripts/peek.py --n 3` | print 3 truncated records per raw file (never open `data/raw/` directly) |
| `make profile` | `python scripts/profile_data.py` | write `docs/DATA_PROFILE.md` |
| `make coverage` | `python scripts/coverage.py && python scripts/audit_tags.py` | normalization coverage report + family/tag consistency audit |
| — | `python scripts/llm_audit.py canonicals \| sample \| report` | offline LLM audit of the allergen rules (cached, resumable); writes `docs/tag_audit.md` |
| — | `python eval/explore.py` | exploratory conversations from `eval/explore.txt`; transcripts in `eval/explore_transcripts/` |

## API

- `POST /api/chat {session_id, message}` → `{reply_md, voice, payload, state, trace, planner, suggestions}`
- `GET /api/recipe/{id}`: the original recipe, parsed lines and tags
- `PATCH /api/session/{id}/state {op: remove|set, field, value}`: chip changes; re-runs the active task
- `POST /api/session/{id}/reset`
- `GET /api/health`: record counts, build fingerprint, LLM status

Sessions live in memory (30 min TTL), 10 messages per minute per session.

## Environment

| variable | default | meaning |
|---|---|---|
| `GEMINI_API_KEY` | (unset) | optional; without it the rule parser plans every turn and there is no voice reply |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | planner, voice and step-rewrite model |
| `GEMINI_FALLBACK_MODEL` | `gemini-3.5-flash` | one retry on HTTP 503/504 when the turn's time budget allows |
| `LLM_REPLAY` | (unset) | `1` = cached LLM answers only, never the network (eval replays, screenshots) |
| `RECIPES_DB` | `data/recipes.db` | the database file |
| `PORT` | 8000 | the port the Docker image listens on |

Variables can also go in `.env` (see `.env.example`); real environment variables win.
