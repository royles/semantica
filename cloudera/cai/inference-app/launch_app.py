#!/usr/bin/env python3
"""
Cloudera AI Inference application entrypoint for Semantica Knowledge Explorer.

Listens on APP_PORT (CAI sets this to 8080). See cloudera/cai/inference-app/README.md.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


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


def main() -> None:
    host, port, graph_path = _configure_cai_environment()

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

    session = GraphSession.from_file(str(graph_path))
    app = create_app(session=session)

    service_domain = os.environ.get("SERVICE_DOMAIN", "")
    app_url = os.environ.get("APP_URL", "")
    print(f"Semantica Knowledge Explorer starting on {host}:{port}")
    if app_url:
        print(f"External URL (CAI): {app_url}")
    if service_domain:
        print(f"SERVICE_DOMAIN: {service_domain}")
    print(f"Graph: {graph_path} ({session.get_stats().get('node_count', 0)} nodes)")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
