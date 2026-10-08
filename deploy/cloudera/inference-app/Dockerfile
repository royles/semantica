# Cloudera AI — Docker application image.
# Build from repository root:
#   docker build -f deploy/cloudera/inference-app/Dockerfile -t semantica-knowledge-explorer-cai:latest .
#
# At runtime the platform sets CDSW_APP_PORT; the frontend must listen on
# 127.0.0.1:CDSW_APP_PORT (see launch_app.py).

# syntax=docker/dockerfile:1
FROM node:26-alpine@sha256:2d984a15c9b54fd0aeb608b8e0d0d83529eb34d2966db27a1fb4f1edc3d298a3 AS frontend-builder

WORKDIR /app
COPY explorer/package*.json ./explorer/
WORKDIR /app/explorer
RUN npm ci
COPY explorer/ ./
RUN mkdir -p /app/semantica && npm run build

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SEMANTICA_HOST=127.0.0.1

WORKDIR /app

RUN groupadd --system semantica \
    && useradd --system --gid semantica --home-dir /app --shell /usr/sbin/nologin semantica

COPY pyproject.toml README.md LICENSE MANIFEST.in \
     .github/requirements/explorer-extra-py313.txt .github/requirements/pep517-build.txt ./
COPY semantica/ ./semantica/
COPY integrations/ ./integrations/
COPY deploy/cloudera/inference-app/ ./deploy/cloudera/inference-app/
COPY --from=frontend-builder /app/semantica/static ./semantica/static

RUN pip install --no-cache-dir -r explorer-extra-py313.txt -r pep517-build.txt --require-hashes \
    && pip install --no-cache-dir --no-deps --no-build-isolation . \
    && rm -f explorer-extra-py313.txt pep517-build.txt \
    && chown -R semantica:semantica /app

USER semantica

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import json, os, sys, urllib.request; p=os.environ.get('CDSW_APP_PORT'); \
if not p: sys.exit(1); \
data=json.load(urllib.request.urlopen(f'http://127.0.0.1:{p}/api/health', timeout=3)); \
raise SystemExit(0 if data.get('status') == 'ok' else 1)"

CMD ["python", "deploy/cloudera/inference-app/launch_app.py"]
