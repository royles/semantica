# Knowledge Explorer — Cloudera AI application

Deploy Semantica **Knowledge Explorer** on Cloudera AI (Workbench projects, Inference applications, embedded web apps).

Index: [`deploy/cloudera/README.md`](../README.md).

## CDSW / CAI networking (required)

Cloudera documents that HTTP apps must:

1. Bind **`127.0.0.1`** (loopback inside the engine/pod).
2. Listen on **`CDSW_APP_PORT`** (platform sets the port; default is often **8080**).

`launch_app.py` uses `CDSW_APP_PORT` first, then falls back to `APP_PORT` / `PORT` for Inference-style deploys. Override host only with `SEMANTICA_HOST` (default **`127.0.0.1`**).

References:

- [Embedded web applications](https://docs.cloudera.com/machine-learning/cloud/projects/topics/ml-embedded-web-apps.html)
- [Engine environment variables (`CDSW_APP_PORT`)](https://docs.cloudera.com/cdsw/1.10.5/environment-variables/topics/cdsw-engine-environment-variables-1.html)

Read-only UIs may use `CDSW_READONLY_PORT` instead; Explorer needs read/write graph APIs, so use **`CDSW_APP_PORT`**.

## Git / entrypoint deploy

- **Entrypoint:** `deploy/cloudera/inference-app/launch_app.py`
- **Requirements:** [`requirements.txt`](requirements.txt) (copy to repo root if the platform only installs root `requirements.txt`)

## Environment variables

| Variable | Notes |
|----------|--------|
| **`CDSW_APP_PORT`** | **Required** on CDSW/CAI — port uvicorn binds on `127.0.0.1` |
| `CDSW_ENGINE_ID` / `CDSW_DOMAIN` | Used to infer public URL for CORS when `APP_URL` is unset |
| `APP_URL` | Inference applications: external HTTPS URL (also sets `ALLOWED_ORIGINS`) |
| `SEMANTICA_ALLOW_ANONYMOUS` | **`true`** for SSO web apps; browser UI does not send `X-API-Key` |
| `SEMANTICA_GRAPH_PATH` | Optional ContextGraph JSON (default: seeded sample under `fixtures/`) |

## Authentication (empty UI)

If `SEMANTICA_API_KEY` is set without `SEMANTICA_ALLOW_ANONYMOUS=true`, protected `/api/*` routes fail and the dashboard looks blank. For CAI SSO web apps, prefer **`SEMANTICA_ALLOW_ANONYMOUS=true`** and rely on platform auth at the edge.

## Docker deploy

```bash
docker build -f deploy/cloudera/inference-app/Dockerfile -t <registry>/semantica-knowledge-explorer-cai:<tag> .
docker push <registry>/semantica-knowledge-explorer-cai:<tag>
```

Set **`CDSW_APP_PORT=8080`** (or match the platform) in the application env.

## Local smoke test (simulates CAI)

```bash
pip install -e ".[explorer]"
export CDSW_APP_PORT=8080 APP_URL=http://127.0.0.1:8080 SEMANTICA_ALLOW_ANONYMOUS=true
python deploy/cloudera/inference-app/launch_app.py
curl -s http://127.0.0.1:8080/api/health
```

You should see `Uvicorn running on http://127.0.0.1:8080`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Nothing in browser | Open the CAI grid link / `APP_URL`, not your laptop’s localhost |
| Empty graph UI | `SEMANTICA_ALLOW_ANONYMOUS=true`; remove lone `SEMANTICA_API_KEY` for browser use |
| Proxy 502 / no route | Confirm **`127.0.0.1`** + **`CDSW_APP_PORT`**, not `0.0.0.0` or hard-coded 8000 |
