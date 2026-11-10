# ---- web: build the React UI (Vite). Only dist/ reaches the final image.
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- builder: download raw data, build the DB. Discarded after the build (no raw JSON/zip in the final image).
FROM python:3.12-slim AS builder
WORKDIR /app
# download first so code edits don't re-download ~200 MB
COPY scripts/download.py scripts/download.py
RUN python scripts/download.py
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app backend/app
RUN python -m backend.app.ingest

# ---- runtime: deps + code + recipes.db + built UI. Targets Railway Trial (0.5 GB RAM), budget <400 MB.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app backend/app
COPY --from=builder /app/data/recipes.db data/recipes.db
COPY --from=web /web/dist frontend/dist
# Railway injects $PORT; default 8000. Shell form so it expands. One worker (in-memory sessions).
CMD ["sh", "-c", "uvicorn app.api:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
