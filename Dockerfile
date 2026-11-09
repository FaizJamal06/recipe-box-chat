# ---- builder: download raw data, build the DB. Discarded after the build (no raw JSON/zip in the final image).
FROM python:3.12-slim AS builder
WORKDIR /app
# download first so code edits don't re-download ~200 MB
COPY scripts/download.py scripts/download.py
RUN python scripts/download.py
COPY backend/app/ingest.py backend/app/ingest.py
RUN python backend/app/ingest.py

# ---- runtime: deps + code + recipes.db only. Targets Railway Trial (0.5 GB), budget <400 MB.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY --from=builder /app/data/recipes.db data/recipes.db
# Railway injects $PORT; default 8000. Shell form so it expands. One worker.
CMD ["sh", "-c", "uvicorn app.api:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
