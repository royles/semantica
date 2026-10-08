# Semantica Knowledge Explorer on Cloudera AI Inference

Deploy the **Semantica Knowledge Explorer** (FastAPI + bundled React UI) as a **Cloudera AI Inference application** (CAI “Applications” under **Deployments**).

Official reference: [Deploying an application on Cloudera AI Inference service](https://docs.cloudera.com/machine-learning/cloud/ai-inference/topics/ml-caii-application-deploy.html).

## CAI constraints (must follow)

| Requirement | This repo |
|-------------|-----------|
| Listen on **port 8080** inside the pod | `launch_app.py` reads **`APP_PORT`** (CAI sets `8080`) |
| External HTTPS on 443 | Handled by CAI ingress (`APP_URL`) |
| Git **or** Docker source | Both supported below |
| New Inference instance for Applications | Create a dedicated CAI Inference service for app serving (not reuse an existing inference-only instance) |

Runtime env vars injected by CAI (read-only):

- `APP_PORT` — always `8080`
- `APP_URL` — public URL, e.g. `https://<subdomain>.serving-apps.<domain>`
- `SERVICE_DOMAIN` — inference service domain
- `OWNER_ID` — deploying user

`launch_app.py` maps `APP_URL` → `ALLOWED_ORIGINS` when not set explicitly.

## Option A — Deploy from Git (fastest to try)

1. **Cloudera console** → **Cloudera AI** → **Applications** → **Deploy Application**.
2. Select your **environment** and a **new** Cloudera AI Inference service instance.
3. **Name / subdomain** — e.g. `semantica-explorer` → app at `https://semantica-explorer.serving-apps.<SERVICE_DOMAIN>`.
4. **Source: Git**
   - **Git URL:** `https://github.com/royles/semantica.git` (or your fork)
   - **Branch / tag:** `main` or your release branch
   - **Entrypoint:** `deploy/cloudera-ai/launch_app.py`
   - **Authentication:** PAT or SSH if private
5. **Requirements:** CAI installs dependencies from a repo **`requirements.txt`**. Either:
   - Copy `deploy/cloudera-ai/requirements.txt` to the **repository root** as `requirements.txt` for the deploy branch, **or**
   - Maintain root `requirements.txt` with the same contents as `deploy/cloudera-ai/requirements.txt`.
6. **Authentication type:** **SSO** for the interactive Explorer UI (browser).
7. **Environment variables** (recommended):

   | Key | Value |
   |-----|--------|
   | `SEMANTICA_API_KEY` | Strong secret (Explorer fails closed on protected routes without it) |
   | `SEMANTICA_GRAPH_PATH` | Optional path to a ContextGraph JSON file (default: bundled sample under `deploy/cloudera-ai/fixtures/`) |
   | `ALLOWED_ORIGINS` | Optional; defaults from `APP_URL` |

   Do **not** set `SEMANTICA_ALLOW_ANONYMOUS=true` in production.

8. **Resource profile:** start with **2 CPU / 4–8 GiB RAM**, **0 GPU**, autoscale **1–3** replicas (Explorer is CPU + memory bound; no GPU required for the default UI).

9. **Create Application** → open **`APP_URL`** from the application details page.

### Health check

- `GET /api/health` → `{"status":"ok"}`
- Swagger: `/docs`

## Option B — Deploy from Docker (production)

Build and push an image from the **repository root**:

```bash
docker build -f deploy/cloudera-ai/Dockerfile -t <registry>/semantica-knowledge-explorer-cai:<tag> .
docker push <registry>/semantica-knowledge-explorer-cai:<tag>
```

In CAI **Deploy Application**:

- **Source: Docker**
- **Image URL:** `<registry>/semantica-knowledge-explorer-cai:<tag>`
- Registry credentials if private
- Same env vars and **SSO** as Git deploy

The image **`CMD`** runs `python deploy/cloudera-ai/launch_app.py` on port **8080**.

## Local smoke test (before CAI)

```bash
pip install -e ".[explorer]"
export APP_PORT=8080 APP_URL=http://127.0.0.1:8080 SEMANTICA_ALLOW_ANONYMOUS=true
python deploy/cloudera-ai/launch_app.py
curl -s http://127.0.0.1:8080/api/health
```

## Loading your own graph

1. Store a `ContextGraph` JSON in object storage (CAI grants datalake S3 access to the app service account) or bake it into the image.
2. Set `SEMANTICA_GRAPH_PATH` to the mount path or downloaded file path in the container.
3. Or extend `launch_app.py` to download from S3 on startup using your org’s patterns.

## What this deploys (and what it does not)

| Included | Not included by default |
|----------|-------------------------|
| Knowledge Explorer UI + REST API | FalkorDB / Neo4j sidecars (see `deploy/kubernetes`, Helm) |
| Sample demo graph | LLM keys (set in CAI env if you use LLM-backed features) |
| Static frontend in `semantica/static` | Jupyter / cookbook notebooks (use CAI Workbench separately) |

## Related repo deploy paths

- Root **`Dockerfile`** — generic Explorer image (port **8000**); use **`deploy/cloudera-ai/Dockerfile`** for CAI (**8080**).
- **`deploy/helm/knowledge-explorer`** — Kubernetes / on-prem clusters
- **`deploy/render`**, **`deploy/azure`** — other hosted targets

## CDP CLI (optional)

Generate a serving-app skeleton (names vary by CDP version):

```bash
cdp ml create-ml-serving-app --generate-cli-skeleton > create-serving-app.json
# Edit JSON, then:
cdp ml create-ml-serving-app --cli-input-json file://create-serving-app.json
```

Application creation itself is still done in the **Applications** UI or your platform’s CI pipeline that wraps the same APIs.
