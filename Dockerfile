# ==============================================================================
# Stage 1 : Builder - Compilation et installation des dépendances Python
# ==============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels-dev -r requirements-dev.txt

# ==============================================================================
# Stage 2 : Test - Exécute pytest, bandit (utilisé par Jenkins : --target test)
# ==============================================================================
FROM python:3.11-slim AS test

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=testing

WORKDIR /app

COPY --from=builder /build/wheels-dev /wheels
COPY --from=builder /build/requirements-dev.txt .
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY app ./app
COPY run.py ./run.py
COPY tests ./tests

RUN pytest tests/ -v && bandit -r app/ -ll -ii

# ==============================================================================
# Stage 3 : Production Runtime - Image légère sécurisée (Gunicorn)
# ==============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=5000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appgroup && useradd -r -g appgroup appuser

COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY app ./app
COPY run.py ./run.py
COPY entrypoint.sh ./entrypoint.sh

RUN chmod +x /app/entrypoint.sh \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
