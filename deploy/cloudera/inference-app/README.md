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
4. Auth type **SSO** for the web UI.
5. Set **`SEMANTICA_API_KEY`** in application environment variables.

| Variable | Notes |
|----------|--------|
| `SEMANTICA_API_KEY` | Required for protected API routes in production |
| `SEMANTICA_GRAPH_PATH` | Optional; default seeds `fixtures/sample_graph.json` |
| `ALLOWED_ORIGINS` | Optional; defaults from CAI `APP_URL` |

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
