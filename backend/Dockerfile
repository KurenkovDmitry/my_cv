FROM python:3.13-slim

ARG RELEASE_SHA=dev

LABEL org.opencontainers.image.title="portfolio-api" \
      org.opencontainers.image.revision="${RELEASE_SHA}" \
      org.opencontainers.image.description="Portfolio FastAPI application image."

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/README.md /app/backend/README.md
COPY backend/app /app/backend/app
COPY backend/migrations /app/backend/migrations
COPY scripts /app/scripts

RUN python -m pip install --upgrade pip \
    && python -m pip install /app/backend

EXPOSE 8000

WORKDIR /app/backend

CMD ["uvicorn", "app.main:application", "--host", "0.0.0.0", "--port", "8000"]
