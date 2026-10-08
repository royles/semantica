# Cloudera AI (CAI) deployment

**Cloudera-specific** assets for running Semantica on Cloudera AI. Other platforms live alongside this directory under [`deploy/`](../) (Kubernetes, Helm, Render, Azure, etc.).

## Layout

| Path | Purpose |
|------|---------|
| [`inference-app/`](inference-app/) | **Cloudera AI Inference** application — Knowledge Explorer on port **8080** |
| `inference-app/launch_app.py` | CAI Git **entrypoint** (application start script) |
| `inference-app/requirements.txt` | Dependencies for Git-based deploy (copy to repo root if CAI requires it there) |
| `inference-app/Dockerfile` | Container image for Docker-based CAI deploy |

Future additions might include Workbench project files or CDP CLI templates under `deploy/cloudera/`.

## Quick start

See **[`inference-app/README.md`](inference-app/README.md)** for deploy steps (Git vs Docker, env vars, SSO).

**CAI Git entrypoint:** `deploy/cloudera/inference-app/launch_app.py`
