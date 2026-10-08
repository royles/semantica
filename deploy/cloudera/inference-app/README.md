# Knowledge Explorer — Cloudera AI Inference application

Deploy Semantica **Knowledge Explorer** on [Cloudera AI Inference application serving](https://docs.cloudera.com/machine-learning/cloud/ai-inference/topics/ml-caii-application-deploy.html).

Index: [`deploy/cloudera/README.md`](../README.md).

## CAI requirements

- Process listens on **`APP_PORT`** (**8080**).
- Use a **new** Inference service instance created for Applications.
- **Git entrypoint:** `deploy/cloudera/inference-app/launch_app.py`

## Git deploy

1. Cloudera console → **Cloudera AI** → **Applications** → **Deploy Application**.
2. Source **Git** — repo URL, branch, entrypoint **`deploy/cloudera/inference-app/launch_app.py`**.
3. Ensure CAI can install deps from **`requirements.txt`** (copy [`requirements.txt`](requirements.txt) to the repo root on your deploy branch if the platform only reads root).
4. Auth type **SSO** for the web UI (CAI protects the URL at the edge).

| Variable | Notes |
|----------|--------|
| `SEMANTICA_ALLOW_ANONYMOUS` | Set to **`true`** for SSO web apps (default when `APP_URL` is set and no API key). The Explorer **browser UI does not send `X-API-Key`**; if you only set `SEMANTICA_API_KEY`, the UI loads but graph API calls fail and the dashboard looks **empty**. |
| `SEMANTICA_API_KEY` | Optional on CAI; use for programmatic API access with `X-API-Key`, not for the bundled UI alone. |
| `SEMANTICA_GRAPH_PATH` | Optional; default seeds `fixtures/sample_graph.json` |
| `ALLOWED_ORIGINS` | Optional; defaults from CAI `APP_URL` |

### “I run launch_app.py and see nothing”

1. **Logs** — The process is a **foreground server**; after startup you should see `Uvicorn running on http://0.0.0.0:8080`. Open **`APP_URL`** from the CAI app details page (not localhost on your laptop unless port-forwarding).
2. **Port** — CAI requires **8080** (`APP_PORT`). Do not use 8000 on the platform.
3. **Empty UI** — Usually missing `SEMANTICA_ALLOW_ANONYMOUS=true` while `SEMANTICA_API_KEY` is set. Fix env vars above, redeploy, hard-refresh the browser.
4. **Missing UI assets** — Install `semantica[explorer]` (Git `requirements.txt`) or use the Docker image; check logs for “UI bundle missing”.

## Docker deploy

```bash
docker build -f deploy/cloudera/inference-app/Dockerfile -t <registry>/semantica-knowledge-explorer-cai:<tag> .
docker push <registry>/semantica-knowledge-explorer-cai:<tag>
```

## Local smoke test

```bash
pip install -e ".[explorer]"
export APP_PORT=8080 APP_URL=http://127.0.0.1:8080 SEMANTICA_ALLOW_ANONYMOUS=true
python deploy/cloudera/inference-app/launch_app.py
curl -s http://127.0.0.1:8080/api/health
```
