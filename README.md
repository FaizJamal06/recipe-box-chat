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
| `make run` | `python -m uvicorn app.api:app --app-dir backend --port 7860 --reload` | serve the API; try http://127.0.0.1:7860/api/health |
| `make docker` | `docker build -t recipe-box . ; docker run --rm -p 7860:7860 recipe-box` | the image Hugging Face builds |

Activate the venv before `run`: `.\.venv\Scripts\Activate.ps1` (Windows) or `. .venv/bin/activate`.
More targets (db, test, cli, eval) arrive with their milestones.

## Deploy to Hugging Face

New Space → SDK **Docker** → `git remote add space https://huggingface.co/spaces/<you>/recipe-box-chat` → `git push space main`.
The build downloads the dataset; `/api/health` returning record counts proves it worked.
Hugging Face needs this YAML at the top of the Space's README (add it to the copy you push, or here):

```
---
title: Recipe Box
sdk: docker
app_port: 7860
---
```
