#!/usr/bin/env python3
"""
Cloudera AI (CAI / CDSW) application entrypoint for Semantica Knowledge Explorer.

Bind to 127.0.0.1 and CDSW_APP_PORT (platform proxy requirement). See README.
"""

from __future__ import annotations

import os
import shutil
import subprocess
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


def _resolve_frontend_port() -> int:
    """Explorer UI/API must bind only to CDSW_APP_PORT (set by the platform)."""
    raw = os.environ.get("CDSW_APP_PORT")
    if raw is None or str(raw).strip() == "":
        print(
            "ERROR: CDSW_APP_PORT is not set. The Knowledge Explorer frontend must "
            "listen on the port provided in CDSW_APP_PORT (bind 127.0.0.1). "
            "Other auxiliary services may use different ports inside the container.",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
    return int(raw)


def _resolve_cai_app_url() -> str:
    explicit = (os.environ.get("APP_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    engine_id = os.environ.get("CDSW_ENGINE_ID", "").strip()
    domain = os.environ.get("CDSW_DOMAIN", "").strip()
    if engine_id and domain:
        return f"https://{engine_id}.{domain}"
    return ""


def _collect_cai_allowed_origins(app_url: str, port: int) -> list[str]:
    """Browser Origin values for CORS / WebSocket allowlists on CAI."""
    origins: list[str] = []
    for raw in (
        app_url,
        (os.environ.get("SERVICE_DOMAIN") or "").strip().rstrip("/"),
        (os.environ.get("CDSW_APP_URL") or "").strip().rstrip("/"),
    ):
        if raw and raw not in origins:
            origins.append(raw)
    engine_id = os.environ.get("CDSW_ENGINE_ID", "").strip()
    domain = os.environ.get("CDSW_DOMAIN", "").strip()
    if engine_id and domain:
        for scheme in ("https", "http"):
            candidate = f"{scheme}://{engine_id}.{domain}"
            if candidate not in origins:
                origins.append(candidate)
    # Loopback is used by some CAI health probes and port-forward smoke tests.
    for host in ("127.0.0.1", "localhost"):
        candidate = f"http://{host}:{port}"
        if candidate not in origins:
            origins.append(candidate)
    return origins


def _log_step(message: str) -> None:
    print(message, flush=True)


def _configure_cai_environment() -> tuple[str, int, Path]:
    port = _resolve_frontend_port()
    # CDSW/CAI reverse-proxy expects the app on loopback, not 0.0.0.0.
    host = os.environ.get("SEMANTICA_HOST", "127.0.0.1")

    app_url = _resolve_cai_app_url()
    if not os.environ.get("ALLOWED_ORIGINS"):
        origins = _collect_cai_allowed_origins(app_url, port)
        if origins:
            os.environ["ALLOWED_ORIGINS"] = ",".join(origins)

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

    on_cai = bool(
        os.environ.get("CDSW_APP_PORT")
        or os.environ.get("CDSW_DOMAIN")
        or os.environ.get("APP_URL")
    )
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


def _static_index_path() -> Path:
    import semantica

    return Path(semantica.__file__).resolve().parent / "static" / "index.html"


def _editable_install_root() -> Path | None:
    """Return the git checkout path when semantica is installed editable (-e)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "semantica"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Editable project location:"):
            raw = line.split(":", 1)[1].strip()
            if raw:
                return Path(raw).resolve()
    return None


def _explain_missing_ui_when_pip_satisfied() -> str:
    pkg_root = Path(__file__).resolve().parent
    static = _static_index_path()
    editable = _editable_install_root()
    lines = [
        f"Python loads semantica from: {static.parent.parent}",
        f"Expected UI file: {static} (exists={static.is_file()})",
    ]
    if editable is not None:
        lines.extend(
            [
                "",
                "pip reports semantica[explorer] as installed because this is an "
                f"EDITABLE install (-e) of the git checkout at:",
                f"  {editable}",
                "",
                "Editable installs do NOT copy the PyPI wheel's pre-built UI. "
                "The React bundle must exist under semantica/static/ in that checkout.",
                "",
                "Fix (stay on git checkout):",
                "  cd explorer && npm ci && npm run build",
                "  # then restart launch_app.py",
                "",
                "Fix (use PyPI bundle instead of -e):",
                "  pip uninstall -y semantica",
                "  pip install --force-reinstall 'semantica[explorer]==0.7.0'",
                "",
                "Do not run `pip install semantica[explorer]` alone while -e is active; "
                "pip will skip reinstalling and the UI will stay missing.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Reinstall the wheel that includes semantica/static/:",
                "  pip install --force-reinstall 'semantica[explorer]==0.7.0'",
            ]
        )
    return "\n".join(lines)


def _find_semantica_repo_root() -> Path | None:
    """Locate a git checkout that includes the Explorer frontend sources."""
    explicit = (os.environ.get("SEMANTICA_REPO_ROOT") or "").strip()
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if (candidate / "explorer" / "package.json").is_file():
            return candidate

    for start in (
        Path(__file__).resolve().parent,
        Path.cwd(),
    ):
        for parent in (start, *start.parents):
            if (parent / "explorer" / "package.json").is_file() and (
                parent / "pyproject.toml"
            ).is_file():
                return parent
    return None


def _try_build_explorer_ui_from_source() -> bool:
    """Build ../semantica/static when deploying from a git checkout without a wheel bundle."""
    if os.environ.get("SEMANTICA_SKIP_UI_BUILD", "").strip().lower() == "true":
        return False

    repo_root = _find_semantica_repo_root()
    if repo_root is None:
        return False

    explorer_dir = repo_root / "explorer"
    if not explorer_dir.is_dir():
        return False

    npm = shutil.which("npm")
    if not npm:
        _log_step(
            "Explorer UI bundle missing and npm is not installed — "
            "cannot build from explorer/. "
            "Use pip install semantica[explorer] from PyPI or the Docker image."
        )
        return False

    _log_step(
        f"Explorer UI bundle missing — building from {explorer_dir} "
        "(npm ci && npm run build; may take several minutes on first run)…"
    )
    env = os.environ.copy()
    env.setdefault("CI", "true")
    try:
        subprocess.run(
            [npm, "ci"],
            cwd=explorer_dir,
            env=env,
            check=True,
        )
        subprocess.run(
            [npm, "run", "build"],
            cwd=explorer_dir,
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError:
        print(
            "ERROR: Explorer frontend build failed (see npm output above).",
            file=sys.stderr,
            flush=True,
        )
        return False

    return _static_index_path().is_file()


def _ensure_explorer_ui_bundle() -> None:
    static_index = _static_index_path()
    if static_index.is_file():
        _log_step(f"Explorer UI bundle found: {static_index}")
        return

    if _try_build_explorer_ui_from_source():
        _log_step(f"Explorer UI bundle built: {_static_index_path()}")
        return

    diagnosis = _explain_missing_ui_when_pip_satisfied()
    on_cai = bool(os.environ.get("CDSW_APP_PORT"))
    if on_cai:
        print("ERROR: Explorer UI bundle missing.\n", file=sys.stderr, flush=True)
        print(diagnosis, file=sys.stderr, flush=True)
        raise SystemExit(1)
    print(
        f"WARNING: Explorer UI bundle missing.\n{diagnosis}\nAPI /docs will still work.",
        file=sys.stderr,
        flush=True,
    )


def main() -> None:
    _log_step("Semantica CAI launch_app.py — starting setup…")
    host, port, graph_path = _configure_cai_environment()
    _log_step(
        f"Environment OK: host={host} port={port} graph={graph_path} "
        f"ALLOWED_ORIGINS={os.environ.get('ALLOWED_ORIGINS', '(default)')}"
    )
    _configure_explorer_auth_for_cai()

    _log_step("Importing uvicorn…")
    try:
        import uvicorn
    except ImportError as exc:
        print(
            "uvicorn is required. Install semantica[explorer] (see requirements.txt).",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    _log_step("Importing Semantica Explorer (first run can take 1–2 minutes)…")
    try:
        from semantica.explorer.app import create_app
        from semantica.explorer.session import GraphSession
    except Exception:
        print("ERROR: Failed to import semantica.explorer:", file=sys.stderr, flush=True)
        import traceback

        traceback.print_exc()
        raise SystemExit(1) from None

    _ensure_explorer_ui_bundle()

    _log_step(f"Loading graph from {graph_path}…")
    try:
        session = GraphSession.from_file(str(graph_path))
    except Exception:
        print("ERROR: Failed to load graph session:", file=sys.stderr, flush=True)
        import traceback

        traceback.print_exc()
        raise SystemExit(1) from None

    _log_step("Creating FastAPI application…")
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
    print(f"  Health:  {local_base}/api/health  (or /healthcheck for CAI polling)", flush=True)
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
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        print("ERROR: launch_app.py failed:", file=sys.stderr, flush=True)
        import traceback

        traceback.print_exc()
        raise SystemExit(1) from None
