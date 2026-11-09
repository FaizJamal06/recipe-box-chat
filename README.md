# Recipe Box chatbot

Status: **M0 done** (scaffold, data download + profile, `/api/health`). Spec: [PRD.md](PRD.md). Data findings: [docs/DATA_PROFILE.md](docs/DATA_PROFILE.md).

## Commands

Each `make` target is one command you can run directly (no `make` needed; PowerShell shown, Python 3.12).

| make target | Run directly | What it does |
|---|---|---|
| `make setup` | `python scripts/setup.py` | create `.venv`, install `requirements.txt` (+ `npm ci` once `frontend/` exists) |
| `make data` | `python scripts/download.py` | download + unzip the dataset into `data/raw/` |
| `make db` | `python backend/app/ingest.py` | build `data/recipes.db` (~25 s, peak RSS ~260 MB; prints peak memory) |
| `make peek` | `python scripts/peek.py --n 3` | print 3 truncated records per file (never open `data/raw/` directly) |
| `make profile` | `python scripts/profile_data.py` | write `docs/DATA_PROFILE.md` |
| `make run` | `python -m uvicorn app.api:app --app-dir backend --port 8000 --reload` | serve the API; try http://127.0.0.1:8000/api/health |
| `make docker` | `docker build -t recipe-box . ; docker run --rm -p 8000:8000 recipe-box` | the image Railway builds (listens on `$PORT`, default 8000) |

Activate the venv before `run`: `.\.venv\Scripts\Activate.ps1` (Windows) or `. .venv/bin/activate`.
More targets (db, test, cli, eval) arrive with their milestones.

## Deploy to Railway

Push the repo to GitHub → Railway → New Project → Deploy from GitHub repo (it detects the `Dockerfile`) →
Settings → Networking → Generate Domain; set the healthcheck path to `/api/health`. Railway injects `$PORT`;
the container honours it (default 8000, one worker). Trial plan = 0.5 GB RAM, so the runtime budget is <400 MB.
The Dockerfile is multi-stage: a builder stage downloads the data and builds `recipes.db`; the final image contains only
the code and `recipes.db` (no raw JSON or zip). `/api/health` returning counts proves it worked.
