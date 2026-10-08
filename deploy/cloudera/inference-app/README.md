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
- **Requirements:** repository root [`requirements.txt`](../../../requirements.txt) (`semantica[explorer]` from PyPI), or [`inference-app/requirements.txt`](requirements.txt) (same pin)

**Git clone without Docker:** if you `pip install -e .` from source, the React bundle is not in git (`semantica/static/` is build output). Either:

1. Let **`launch_app.py` auto-build** on first start (Node.js + npm must be on the engine), or  
2. Run once: `cd explorer && npm ci && npm run build`, or  
3. `pip install 'semantica[explorer]==0.7.0'` from PyPI instead of an editable install.

## Environment variables

| Variable | Notes |
|----------|--------|
| **`CDSW_APP_PORT`** | **Required** — frontend listen port on `127.0.0.1` |
| `CDSW_ENGINE_ID` / `CDSW_DOMAIN` | Infer public URL for CORS when `APP_URL` is unset |
| `APP_URL` | Optional external HTTPS URL (Inference apps) |
| `CDSW_APP_POLLING_ENDPOINT` | Optional; set to `/healthcheck` or `/api/health` if CAI marks the app “not ready” |
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
| Logs stop after “CAI SSO mode…” | Wait 1–2 min for Explorer imports; newer logs show each step. Check stderr for tracebacks. |
| Exits immediately | Set **`CDSW_APP_PORT`** in the job/application environment |
| “Explorer UI not available” page | Install **`semantica[explorer]`** from PyPI, use the **Dockerfile**, or build/auto-build the frontend (see **Deploy** above) |
| `pip install semantica[explorer]` says satisfied, UI still missing | You likely have **`pip install -e .`** — editable installs skip the PyPI UI bundle. Run **`cd explorer && npm ci && npm run build`**, or **`pip uninstall -y semantica && pip install --force-reinstall 'semantica[explorer]==0.7.0'`** |
| Empty dashboard (server up) | `SEMANTICA_ALLOW_ANONYMOUS=true`; do not rely on `SEMANTICA_API_KEY` alone for the browser |
| App never opens in CAI grid | Set **`CDSW_APP_POLLING_ENDPOINT=/healthcheck`**; confirm **`curl http://127.0.0.1:$CDSW_APP_PORT/healthcheck`** inside the pod |
| Proxy 502 | Confirm **`127.0.0.1`** + **`CDSW_APP_PORT`**, not `0.0.0.0` or a different env var for the frontend |
| No link in browser | Open the app from the **CAI grid icon** (session/job) or the Inference **`APP_URL`**, not your laptop `localhost` |
