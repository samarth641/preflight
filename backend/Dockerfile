# Build from repo root: docker build -f backend/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Knowledge loaders resolve backend/../knowledge
COPY knowledge/ /app/knowledge/
COPY backend/ /app/backend/
# pyproject.toml references README.md
COPY README.md /app/backend/README.md

WORKDIR /app/backend

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
