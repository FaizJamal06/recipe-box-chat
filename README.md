# Recipe Box chatbot

Status: **M0 done** (scaffold, data download + profile, `/api/health`). Spec: [PRD.md](PRD.md). Data findings: [docs/DATA_PROFILE.md](docs/DATA_PROFILE.md).

## Commands

Each `make` target is one command you can run directly (no `make` needed; PowerShell shown, Python 3.12).

| make target | Run directly | What it does |
|---|---|---|
| `make setup` | `python scripts/setup.py` | create `.venv`, install `requirements.txt` (+ `npm ci` once `frontend/` exists) |
| `make data` | `python scripts/download.py` | download + unzip the dataset into `data/raw/` |
| `make peek` | `python scripts/peek.py --n 3` | print 3 truncated records per file (never open `data/raw/` directly) |
| `make profile` | `python scripts/profile_data.py` | write `docs/DATA_PROFILE.md` |
| `make run` | `python -m uvicorn app.api:app --app-dir backend --port 8000 --reload` | serve the API; try http://127.0.0.1:8000/api/health |
| `make docker` | `docker build -t recipe-box . ; docker run --rm -p 8000:8000 recipe-box` | the image Koyeb builds (listens on `$PORT`, default 8000) |

Activate the venv before `run`: `.\.venv\Scripts\Activate.ps1` (Windows) or `. .venv/bin/activate`.
More targets (db, test, cli, eval) arrive with their milestones.

## Deploy to Koyeb

Push the repo to GitHub → Koyeb → Create Service → GitHub → Builder **Dockerfile** → exposed port **8000** (HTTP),
health check path `/api/health`. Koyeb sets `$PORT`; the container honours it (default 8000, one worker).
The image build downloads the dataset and writes `data/counts.json`; `/api/health` returning record counts proves it worked.
Dataset parsing needs RAM (M1+): pick an instance with more than 512 MB if the build/runtime gets OOM-killed.
