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
- **Run with the engine’s system Python** (e.g. `python` / `python3` on `PATH`). Do **not** create a project venv for the application process unless your site standard requires it.
- **Application command** (preferred — not a notebook cell):

  ```bash
  python deploy/cloudera/inference-app/launch_app.py
  ```

  If CAI runs code inside a **notebook kernel**, `__file__` is undefined unless you use `%run` on the script path above. Optional: set `SEMANTICA_INFERENCE_APP_DIR` to the absolute path of `deploy/cloudera/inference-app`.
- **Requirements:** repository root [`requirements.txt`](../../../requirements.txt) (`semantica[explorer]` from PyPI), or [`inference-app/requirements.txt`](requirements.txt) (same pin)

**Git clone without Docker:** CAI Python engines usually **do not include npm**. The React bundle is not in git (`semantica/static/` is build output). Use one of:

1. **Recommended for CAI:** install the PyPI wheel (includes the UI) — do **not** use `pip install -e .` in the app startup script:
   ```bash
   pip uninstall -y semantica
   pip install --force-reinstall 'semantica[explorer]==0.7.0'
   ```
2. **`launch_app.py` auto-fix:** on first start it can **download the PyPI wheel and extract `semantica/static/`** (needs outbound PyPI access; no npm).
3. **Docker** (`inference-app/Dockerfile`) — multi-stage build with Node.
4. **Dev only** (npm on the engine): `cd explorer && npm ci && npm run build`.

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
| `pip install semantica[explorer]` says satisfied, UI still missing | **`pip install -e .`** is active — use **`pip uninstall -y semantica && pip install --force-reinstall 'semantica[explorer]==0.7.0'`** (CAI has no npm). Or restart after **`launch_app.py`** extracts the UI from PyPI. |
| `npm: command not found` | Expected on CAI — use PyPI **`semantica[explorer]`** or Docker, not `explorer/` npm build |
| Empty dashboard (server up) | `SEMANTICA_ALLOW_ANONYMOUS=true`; do not rely on `SEMANTICA_API_KEY` alone for the browser |
| App never opens in CAI grid | Set **`CDSW_APP_POLLING_ENDPOINT=/healthcheck`**; confirm **`curl http://127.0.0.1:$CDSW_APP_PORT/healthcheck`** inside the pod |
| Proxy 502 | Confirm **`127.0.0.1`** + **`CDSW_APP_PORT`**, not `0.0.0.0` or a different env var for the frontend |
| No link in browser | Open the app from the **CAI grid icon** (session/job) or the Inference **`APP_URL`**, not your laptop `localhost` |
