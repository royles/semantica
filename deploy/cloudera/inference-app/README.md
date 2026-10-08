# Knowledge Explorer — Cloudera AI application

Deploy Semantica **Knowledge Explorer** on Cloudera AI (Workbench, Inference applications, embedded web apps).

Index: [`deploy/cloudera/README.md`](../README.md).

## Frontend port (required)

The **application frontend** (Explorer UI + API served by `launch_app.py`) must:

1. Bind **`127.0.0.1`**
2. Listen on **`CDSW_APP_PORT`** only — the platform sets this variable; **do not hard-code a port number** in code or docs.

If `CDSW_APP_PORT` is unset, `launch_app.py` exits with an error.

**Other services** (workers, MCP, sidecars, debug tools) may listen on **other ports inside the container** (typically also on loopback). Only the main web entrypoint uses `CDSW_APP_PORT`.

References:

- [Embedded web applications](https://docs.cloudera.com/machine-learning/cloud/projects/topics/ml-embedded-web-apps.html)
- [Engine environment variables](https://docs.cloudera.com/cdsw/1.10.5/environment-variables/topics/cdsw-engine-environment-variables-1.html)

Read-only UIs may use `CDSW_READONLY_PORT`; Explorer needs read/write graph APIs → **`CDSW_APP_PORT`**.

## Deploy

- **Entrypoint:** `deploy/cloudera/inference-app/launch_app.py`
- **Requirements:** [`requirements.txt`](requirements.txt) (copy to repo root if the platform only installs root `requirements.txt`)

## Environment variables

| Variable | Notes |
|----------|--------|
| **`CDSW_APP_PORT`** | **Required** — frontend listen port on `127.0.0.1` |
| `CDSW_ENGINE_ID` / `CDSW_DOMAIN` | Infer public URL for CORS when `APP_URL` is unset |
| `APP_URL` | Optional external HTTPS URL (Inference apps) |
| `SEMANTICA_ALLOW_ANONYMOUS` | **`true`** for SSO web apps; browser UI does not send `X-API-Key` |
| `SEMANTICA_GRAPH_PATH` | Optional ContextGraph JSON |

## Authentication (empty UI)

If `SEMANTICA_API_KEY` is set without `SEMANTICA_ALLOW_ANONYMOUS=true`, graph API routes fail and the dashboard looks blank. For CAI SSO, use **`SEMANTICA_ALLOW_ANONYMOUS=true`**.

## Docker

```bash
docker build -f deploy/cloudera/inference-app/Dockerfile -t <registry>/semantica-knowledge-explorer-cai:<tag> .
```

Run with **`CDSW_APP_PORT`** supplied by the platform at runtime (not baked into the image).

## Local smoke test (simulate platform)

Pick any free port locally — only the **name** `CDSW_APP_PORT` matters:

```bash
pip install -e ".[explorer]"
export CDSW_APP_PORT=9090
export SEMANTICA_ALLOW_ANONYMOUS=true
python deploy/cloudera/inference-app/launch_app.py
curl -s "http://127.0.0.1:${CDSW_APP_PORT}/api/health"
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Exits immediately | Set **`CDSW_APP_PORT`** in the job/application environment |
| Empty UI | `SEMANTICA_ALLOW_ANONYMOUS=true` for browser access |
| Proxy 502 | Confirm **`127.0.0.1`** + **`CDSW_APP_PORT`**, not `0.0.0.0` or a different env var for the frontend |
