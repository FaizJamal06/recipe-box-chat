# CLAUDE.md — Recipe Box chatbot

Spec: `PRD.md`. Work one milestone (PRD §10) per session. Read PRD §0–§3 once, then only the sections
the current milestone names. Don't re-read the whole PRD.

## Non-negotiables
- The LLM never produces dataset facts. Counts, IDs, ingredient claims come from code (PRD §0).
- Never silently relax a hard constraint. Never invent recipe IDs.
- Keep modules small and readable (<300 lines). No LangChain/LlamaIndex. Faiz has to explain and change
  this code live in an interview, so pick clear code over clever code.
- P0 scope in the PRD is required. Ponytail decides *how little code*, not *whether* a P0 item exists.

## Token discipline
- NEVER `cat`/Read anything in `data/raw/` or `data/*.db`. Use `python scripts/peek.py --n 3` or a SQL
  query with `LIMIT 5`.
- Run tests as `pytest -q -x` and eval as `make eval | tail -40`. Don't paste long logs. Summarize them.
- Before large edits, show a short plan (≤10 lines). Don't restate the PRD back to me.
- End each milestone with: what's done, what's skipped (`shortcut:` comments), how to verify (1–3 commands).

## Git
- Small, conventional commits (`feat(match): …`, `fix(normalize): …`). Commit at the end of each milestone,
  and mid-milestone when tests are green.

## Commands
`make setup` · `make data` · `make db` · `make test` · `make cli` · `make run` · `make eval` · `make docker`

## Stack
Python 3.11, FastAPI, sqlite3 (FTS5), google-genai, pyyaml, pytest · Vite + React + TS + Tailwind ·
Docker (multi-stage, DB built in builder) → Railway Trial (0.5 GB RAM, listens on `$PORT`; runtime <400 MB). Env: `GEMINI_API_KEY`, `GEMINI_MODEL`, `EXTERNAL_SEARCH=off`.
