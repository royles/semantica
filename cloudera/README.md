# Cloudera AI (CAI) integration

All **Cloudera-specific** assets for running Semantica on Cloudera AI live under this directory. Generic cloud deploy paths remain in [`deploy/`](../deploy/) (Kubernetes, Helm, Render, Azure, etc.).

## Layout

| Path | Purpose |
|------|---------|
| [`cai/inference-app/`](cai/inference-app/) | **Cloudera AI Inference** application — Knowledge Explorer on port **8080** |
| `cai/inference-app/launch_app.py` | CAI Git **entrypoint** (application start script) |
| `cai/inference-app/requirements.txt` | Dependencies for Git-based deploy (copy to repo root if CAI requires it there) |
| `cai/inference-app/Dockerfile` | Container image for Docker-based CAI deploy |

Future additions (not yet in repo) might include Workbench project files, CDP CLI JSON templates, or Agent Studio workflow hooks under `cloudera/cai/` or `cloudera/workbench/`.

## Quick start

See **[`cai/inference-app/README.md`](cai/inference-app/README.md)** for deploy steps (Git vs Docker, env vars, SSO).

**CAI Git entrypoint:** `cloudera/cai/inference-app/launch_app.py`
