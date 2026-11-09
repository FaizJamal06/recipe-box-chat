# Recipe Box chatbot

Status: **M2 done** (search, stats, rule planner, CLI; demos 2 and 3 cross-checked by `eval/oracle.py`). Spec: [PRD.md](PRD.md). Data findings: [docs/DATA_PROFILE.md](docs/DATA_PROFILE.md).

## Commands

Each `make` target is one command you can run directly (no `make` needed; PowerShell shown, Python 3.12).

| make target | Run directly | What it does |
|---|---|---|
| `make setup` | `python scripts/setup.py` | create `.venv`, install `requirements.txt` (+ `npm ci` once `frontend/` exists) |
| `make data` | `python scripts/download.py` | download + unzip the dataset into `data/raw/` |
| `make db` | `python -m backend.app.ingest` | build `data/recipes.db` (~3.5 min, peak RSS ~330 MB; prints peak memory) |
| `make test` | `python -m pytest -q -x` | unit tests + a DB build from `backend/tests/fixtures/mini.json` |
| `make coverage` | `python scripts/coverage.py` | normalization report; rewrites the coverage section of `docs/DATA_PROFILE.md` |
| `make cli` | `python -m backend.app.cli` (or `--ask "..."`) | chat in the terminal (rule planner until M3) |
| `make oracle` | `python eval/oracle.py` | recompute demos 2 and 3 from the raw JSON in pure Python and check the CLI answers (~2.5 min) |
| `make peek` | `python scripts/peek.py --n 3` | print 3 truncated records per file (never open `data/raw/` directly) |
| `make profile` | `python scripts/profile_data.py` | write `docs/DATA_PROFILE.md` |
| `make run` | `python -m uvicorn app.api:app --app-dir backend --port 8000 --reload` | serve the API; try http://127.0.0.1:8000/api/health |
| `make docker` | `docker build -t recipe-box . ; docker run --rm -p 8000:8000 recipe-box` | the image Railway builds (listens on `$PORT`, default 8000) |

Activate the venv before `run`: `.\.venv\Scripts\Activate.ps1` (Windows) or `. .venv/bin/activate`.
More targets (eval, ui) arrive with their milestones.

Counting rules every answer states: N of the **valid** recipes (title + at least one real ingredient line + instructions; the
record total and invalid breakdown are read from the DB at startup). Steps = effective `n_steps` (newline steps;
sentences when the instructions are one paragraph). Ingredient presence is reported **strict** (the family, e.g.
fresh garlic forms) and **broad** (plus the family's `broad` list in `backend/app/lexicon/families.yaml`).

## Deploy to Railway

Push the repo to GitHub → Railway → New Project → Deploy from GitHub repo (it detects the `Dockerfile`) →
Settings → Networking → Generate Domain; set the healthcheck path to `/api/health`. Railway injects `$PORT`;
the container honours it (default 8000, one worker). Trial plan = 0.5 GB RAM, so the runtime budget is <400 MB.
The Dockerfile is multi-stage: a builder stage downloads the data and builds `recipes.db`; the final image contains only
the code and `recipes.db` (no raw JSON or zip). `/api/health` returning counts proves it worked.
