FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# download before copying the rest so code edits don't re-download ~200 MB
COPY scripts/download.py scripts/download.py
RUN python scripts/download.py
COPY . .
# Koyeb injects $PORT; default 8000. Shell form so it expands. One worker: each worker would hold its own copy of the data.
CMD ["sh", "-c", "uvicorn app.api:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
