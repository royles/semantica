#!/usr/bin/env python3
"""
Cloudera AI Inference application entrypoint for Semantica Knowledge Explorer.

Listens on APP_PORT (CAI sets this to 8080). See deploy/cloudera/inference-app/README.md.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# CAI and systemd often run without a TTY; flush logs immediately.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except (OSError, ValueError):
        pass
os.environ.setdefault("PYTHONUNBUFFERED", "1")


def _default_graph_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "sample_graph.json"


def _seed_sample_graph(path: Path) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    from semantica.context import ContextGraph

    graph = ContextGraph()
    graph.add_node(
        "python",
        "language",
        content="Python programming language",
    )
    graph.add_node(
        "semantica",
        "framework",
        content="Semantica knowledge graph platform",
    )
    graph.add_node(
        "cloudera_ai",
        "platform",
        content="Cloudera AI Inference application hosting",
    )
    graph.add_edge("python", "semantica", "powers")
    graph.add_edge("semantica", "cloudera_ai", "deployed_on")
    graph.save_to_file(str(path))


def _configure_cai_environment() -> tuple[str, int, Path]:
    port = int(os.environ.get("APP_PORT") or os.environ.get("PORT", "8080"))
    host = os.environ.get("SEMANTICA_HOST", "0.0.0.0")

    app_url = (os.environ.get("APP_URL") or "").strip().rstrip("/")
    if app_url and not os.environ.get("ALLOWED_ORIGINS"):
        os.environ["ALLOWED_ORIGINS"] = app_url

    graph_path = Path(
        os.environ.get("SEMANTICA_GRAPH_PATH", str(_default_graph_path()))
    ).expanduser()
    _seed_sample_graph(graph_path)

    if not graph_path.is_file():
        print(f"Graph file not found: {graph_path}", file=sys.stderr)
        sys.exit(1)

    return host, port, graph_path


def _configure_explorer_auth_for_cai() -> None:
    """Align Explorer auth with CAI SSO + browser UI (no X-API-Key header).

    The bundled React UI calls /api/* without an API key. If SEMANTICA_API_KEY
    is set and SEMANTICA_ALLOW_ANONYMOUS is not true, graph routes return
    503/401 and the dashboard looks empty.
    """
    if os.environ.get("SEMANTICA_ALLOW_ANONYMOUS", "").strip().lower() == "true":
        return
    if os.environ.get("SEMANTICA_ALLOW_ANONYMOUS", "").strip().lower() == "false":
        return

    on_cai = bool(os.environ.get("APP_URL") or os.environ.get("APP_PORT"))
    if on_cai and not os.environ.get("SEMANTICA_API_KEY"):
        os.environ["SEMANTICA_ALLOW_ANONYMOUS"] = "true"
        print(
            "CAI SSO mode: enabled SEMANTICA_ALLOW_ANONYMOUS=true for the "
            "Explorer UI (trust boundary is CAI ingress).",
            flush=True,
        )
        return

    if os.environ.get("SEMANTICA_API_KEY"):
        print(
            "WARNING: SEMANTICA_API_KEY is set but the Explorer browser UI does "
            "not send X-API-Key. The dashboard will look empty unless you also set "
            "SEMANTICA_ALLOW_ANONYMOUS=true (typical for CAI SSO web apps) or use "
            "API clients that pass the key.",
            file=sys.stderr,
            flush=True,
        )


def _warn_if_ui_bundle_missing() -> None:
    import semantica

    static_index = Path(semantica.__file__).resolve().parent / "static" / "index.html"
    if static_index.is_file():
        return
    print(
        "WARNING: Explorer UI bundle missing (semantica/static/index.html). "
        "Install semantica[explorer] from PyPI or build the frontend "
        "(cd explorer && npm ci && npm run build). API /docs will still work.",
        file=sys.stderr,
        flush=True,
    )


def main() -> None:
    print("Semantica CAI launch_app.py — starting setup…", flush=True)
    host, port, graph_path = _configure_cai_environment()
    _configure_explorer_auth_for_cai()

    try:
        import uvicorn
    except ImportError as exc:
        print(
            "uvicorn is required. Install semantica[explorer] (see requirements.txt).",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    from semantica.explorer.app import create_app
    from semantica.explorer.session import GraphSession

    _warn_if_ui_bundle_missing()

    session = GraphSession.from_file(str(graph_path))
    app = create_app(session=session)

    service_domain = os.environ.get("SERVICE_DOMAIN", "")
    app_url = (os.environ.get("APP_URL") or "").strip().rstrip("/")
    local_base = f"http://127.0.0.1:{port}"

    print("", flush=True)
    print("=" * 60, flush=True)
    print("Semantica Knowledge Explorer — server ready to bind", flush=True)
    print(f"  Listen:  http://{host}:{port}/", flush=True)
    if app_url:
        print(f"  CAI URL: {app_url}/  ← open this in your browser", flush=True)
    else:
        print(f"  Local:   {local_base}/  ← open while port-forwarding", flush=True)
    print(f"  Health:  {local_base}/api/health", flush=True)
    print(f"  Swagger: {local_base}/docs", flush=True)
    print(
        f"  Graph:   {graph_path} "
        f"({session.get_stats().get('node_count', 0)} nodes, "
        f"{session.get_stats().get('edge_count', 0)} edges)",
        flush=True,
    )
    if service_domain:
        print(f"  SERVICE_DOMAIN: {service_domain}", flush=True)
    print("=" * 60, flush=True)
    print("Blocking on uvicorn (process stays foreground until exit).", flush=True)
    print("", flush=True)

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
