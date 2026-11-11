# Recipe Box chatbot

Status: **M4 done** (web UI + API: chat, constraint chips, Results / Calculation / Evidence / Trace panel,
recipe drawer; demos 1–6 run in the browser and as CLI sessions, transcripts in `demos/transcripts/`).
Spec: [PRD.md](PRD.md). Data findings: [docs/DATA_PROFILE.md](docs/DATA_PROFILE.md).

## Run it locally

```
python -m backend.app.ingest                      # once: build data/recipes.db (needs data/raw, see make data)
cd frontend; npm ci; npm run build; cd ..         # build the UI into frontend/dist
python -m uvicorn app.api:app --app-dir backend --port 8000
```
Open http://127.0.0.1:8000. The UI talks to `/api/*` on the same server. For UI work with hot reload, keep the
server running and use `cd frontend; npm run dev` (http://localhost:5173, proxies `/api`).
A link like `/?q=Find+a+penne+pasta+recipe&q=I+cannot+have+dairy` replays those messages on load.

## Commands

Each `make` target is one command you can run directly (no `make` needed; PowerShell shown, Python 3.12).

| make target | Run directly | What it does |
|---|---|---|
| `make setup` | `python scripts/setup.py` | create `.venv`, install `requirements.txt` (+ `npm ci` once `frontend/` exists) |
| `make data` | `python scripts/download.py` | download + unzip the dataset into `data/raw/` |
| `make db` | `python -m backend.app.ingest` | build `data/recipes.db` (~3.5 min, peak RSS ~330 MB; prints peak memory) |
| `make test` | `python -m pytest -q -x` | unit tests + a DB build from `backend/tests/fixtures/mini.json` |
| `make coverage` | `python scripts/coverage.py ; python scripts/audit_tags.py` | normalization report (rewrites the coverage section of `docs/DATA_PROFILE.md`) + family-tag consistency audit (members whose tags differ from their family) |
| — | `python scripts/llm_audit.py canonicals \| sample \| report` | offline LLM audit of the allergen rules (cached, resumable); writes `docs/tag_audit.md` |
| — | `python eval/explore.py` | exploratory run of `eval/explore.txt` through the API; transcripts in `eval/explore_transcripts/` |
| `make cli` | `python -m backend.app.cli` (or `--ask "..."`, `--session demos/demo1_refine.txt`, `--no-llm`) | chat in the terminal; one sticky session; prints planner (LLM / rule parser + why), LLM calls and latency per turn |
| `make oracle` | `python eval/oracle.py` | recompute demos 2 and 3 from the raw JSON in pure Python and check the CLI answers (~2.5 min) |
| — | `python scripts/determinism.py` | build the DB twice (different hash seeds) and compare fingerprints (~6 min alone) |
| `make peek` | `python scripts/peek.py --n 3` | print 3 truncated records per file (never open `data/raw/` directly) |
| `make profile` | `python scripts/profile_data.py` | write `docs/DATA_PROFILE.md` |
| `make ui` | `cd frontend; npm ci; npm run build` | build the React UI into `frontend/dist` (served by FastAPI) |
| `make run` | `python -m uvicorn app.api:app --app-dir backend --port 8000` | serve the UI + API on http://127.0.0.1:8000 (`/api/health` for counts, fingerprint, LLM status) |
| `make docker` | `docker build -t recipe-box . ; docker run --rm -p 8000:8000 -e GEMINI_API_KEY=... recipe-box` | the image Railway builds: node stage builds the UI, builder stage builds the DB (listens on `$PORT`, default 8000) |

Activate the venv before `run`: `.\.venv\Scripts\Activate.ps1` (Windows) or `. .venv/bin/activate`.
API: `POST /api/chat {session_id, message}` → `{reply_md, payload, state, trace, planner}`; `GET /api/recipe/{id}`;
`PATCH /api/session/{id}/state {op: remove|set, field, value}` (re-runs the active task); `POST /api/session/{id}/reset`;
`GET /api/health`. Sessions are in memory (30 min TTL), 10 messages/min per session.

Counting rules every answer states: N of the **valid** recipes (title + at least one real ingredient line + instructions; the
record total and invalid breakdown are read from the DB at startup). Steps = effective `n_steps` (newline steps;
sentences when the instructions are one paragraph). Ingredient presence is reported **strict** (the family, e.g.
fresh garlic forms) and **broad** (plus the family's `broad` list in `backend/app/lexicon/families.yaml`).
Rankings break ties by n_steps, then n_ingredients, then id. Tag stats ("how many are dairy-free") report
lenient (only `contains` counts) and strict (`may_contain` and unverified recipes count too).

Allergens and diets. Tags: dairy, egg, peanut, tree_nut, gluten, soy, sesame, meat, pork, poultry, fish,
shellfish, gelatin, honey, alcohol, root_veg (`lexicon/tags.yaml`). Presets are compositions of tags, shown in the
reply and as one chip (`lexicon/diets.yaml`): vegetarian, vegan, pescatarian, halal (pork + alcohol; the
slaughter method can't be verified from text), Jain (no meat/fish/egg/gelatin, onion, garlic or root
vegetables), lactose intolerant → dairy, celiac / wheat → gluten, nut allergy → peanut + tree_nut; kosher is
stated as not verifiable from recipe text and filters nothing.
**Unknown is not safe** (`backend/app/safety.py`): an ingredient counts as verified free of a tag only if its
canonical is known (≥ 5 valid recipes, not via the suffix fallback) or the line scanner explicitly cleared that
tag ("dairy-free", "rice noodles"); an "or" option only counts if it is itself verified. Otherwise the recipe is
shown with ⚠ "1 ingredient couldn't be verified: '…'" and excluded in strict mode. About 30% of valid recipes have
such an ingredient for a given tag (29.1% dairy … 33.6% peanut): that is the price of not guessing.
The rules decide at runtime; an LLM audited them offline (`python scripts/llm_audit.py`, cached): 3,000
canonicals and a fixed sample of 150 recipes. Results, per-tag miss rates and every fix: [docs/tag_audit.md](docs/tag_audit.md).

LLM: Gemini (`GEMINI_MODEL`, default `gemini-3.5-flash-lite`, thinking `minimal`) only turns text into a JSON
plan; at most 2 requests per turn (the 2nd only to retry invalid JSON); responses cached in
`data/llm_cache.sqlite`; prompt/thought tokens are printed per turn. High-confidence phrasings (a have-list,
"the second one", short restriction-only messages like "also no garlic") skip the LLM and use the rule parser
directly. No key, a 429, a network error or no answer within 6 s → the rule parser, flagged in the reply.
The 6 s limit is client-side (the API rejects deadlines under 10 s); google-genai's ~6 s cold import is paid
at startup (`llm.warm()`), not inside a turn.

Voice (LLM call #2, UI only): after the executor runs, the LLM writes a 2–4 sentence friendly reply from the
payload's facts only (counts, titles, IDs, filters, score parts). Every number, number word and recipe ID in it
must appear in those facts, otherwise the templated answer is shown alone (4 s cap, cached, skipped when the
planner used both calls). The templated "exact answer", the cards and the Calculation tab are unchanged.
Conversation: greetings / thanks / "what can you do" / off-topic get short fixed replies; "why that one?" is
answered from the score breakdown or ranking evidence; a contradiction ("vegan chicken curry") gets one short
question; each answer offers 2–3 follow-up chips. Cuisine questions (no cuisine field) run a labelled
title-keyword proxy (`lexicon/cuisines.yaml` + optional LLM dish names), honest count even when zero.
Nutrition, cook time, servings, ratings and categories have no field: the guard answers those without the LLM (category → a labelled
title-keyword proxy; cook time → durations mentioned in the instructions).

Matching (T2): U = your ingredients, P = pantry staples assumed available (salt, black pepper, water; say "no
staples" to turn off), R = the recipe's required ingredients − P. matched = U∩R, unused = U−R, extra = R−U.
Eligible = no excluded ingredient/tag, n_steps ≤ limit, ≥ 1 matched. Score = 2·matched − 1·extra −
0.1·steps − 0.5·(items short on quantity); "as many as possible" → 3·matched, "fewest additional" → 1.5·extra,
"fewest steps" → 0.5·steps. Quantities are compared only within one unit family (volume or mass; counts
with the same unit), never volume↔mass. If nothing is eligible the reply says "No recipe satisfies all hard
constraints" and lists flagged alternatives, each relaxing one named constraint.

## Deploy to Railway

Push the repo to GitHub → Railway → New Project → Deploy from GitHub repo (it detects the `Dockerfile`) →
Settings → Networking → Generate Domain; set the healthcheck path to `/api/health`. Railway injects `$PORT`;
the container honours it (default 8000, one worker). Trial plan = 0.5 GB RAM, so the runtime budget is <400 MB.
The Dockerfile is multi-stage: a builder stage downloads the data and builds `recipes.db`; the final image contains only
the code and `recipes.db` (no raw JSON or zip). `/api/health` returning counts proves it worked.
