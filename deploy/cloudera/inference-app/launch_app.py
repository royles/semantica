#!/usr/bin/env python3
"""
Cloudera AI (CAI / CDSW) application entrypoint for Semantica Knowledge Explorer.

Bind to 127.0.0.1 and CDSW_APP_PORT (platform proxy requirement). See README.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

# CAI and systemd often run without a TTY; flush logs immediately.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except (OSError, ValueError):
        pass
os.environ.setdefault("PYTHONUNBUFFERED", "1")

# Relative to repo root (used when __file__ is unavailable — e.g. CAI notebook kernel).
_INFERENCE_APP_REL = Path("deploy") / "cloudera" / "inference-app"


def _inference_app_dir() -> Path:
    """Directory containing launch_app.py, fixtures/, and requirements.txt."""
    override = (os.environ.get("SEMANTICA_INFERENCE_APP_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()

    try:
        here = Path(__file__).resolve().parent
        if (here / "fixtures").is_dir() or here.name == "inference-app":
            return here
    except NameError:
        pass

    cwd = Path.cwd()
    for candidate in (
        cwd / _INFERENCE_APP_REL,
        cwd / "inference-app",
        cwd,
    ):
        if (candidate / "fixtures").is_dir():
            return candidate.resolve()
        if candidate.name == "inference-app" and (candidate / "launch_app.py").is_file():
            return candidate.resolve()

    for parent in (cwd, *cwd.parents):
        nested = parent / _INFERENCE_APP_REL
        if (nested / "fixtures").is_dir():
            return nested.resolve()

    return cwd.resolve()


def _fixtures_dir() -> Path:
    return _inference_app_dir() / "fixtures"


def _default_graph_path() -> Path:
    return _fixtures_dir() / "ai_capital_graph.json"


def _demo_resources_manifest_path() -> Path:
    return _fixtures_dir() / "demo_resources.json"


def _load_demo_resources_manifest() -> dict | None:
    path = _demo_resources_manifest_path()
    if not path.is_file():
        return None
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log_step(f"WARNING: Could not read demo resources manifest: {exc}")
        return None


def _register_demo_resource_routes(app: object) -> None:
    """Expose default fixture bibliography for Explorer clients."""
    from fastapi.responses import FileResponse, JSONResponse

    fixtures = _fixtures_dir()
    manifest_path = _demo_resources_manifest_path()
    graph_path = _default_graph_path()

    @app.get("/api/demo/resources", include_in_schema=True)
    async def demo_resources():
        payload = _load_demo_resources_manifest()
        if payload is None:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": "Demo resources manifest missing. Run fixtures/seed_ai_capital_graph.py.",
                },
            )
        payload = dict(payload)
        payload["graph_path"] = str(graph_path)
        payload["manifest_path"] = str(manifest_path)
        return payload

    @app.get("/api/demo/graph", include_in_schema=False)
    async def demo_graph_download():
        if not graph_path.is_file():
            return JSONResponse(status_code=404, content={"detail": "Demo graph JSON not found."})
        return FileResponse(
            graph_path,
            media_type="application/json",
            filename=graph_path.name,
        )


def _seed_demo_graph(path: Path) -> None:
    if path.is_file():
        return
    fixtures_dir = _fixtures_dir()
    bundled = fixtures_dir / "ai_capital_graph.json"
    if bundled.is_file() and bundled != path.resolve():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bundled.read_bytes())
        return

    # Generate in-process when the JSON was not shipped (e.g. partial checkout).
    import importlib.util

    seed_script = fixtures_dir / "seed_ai_capital_graph.py"
    if seed_script.is_file():
        spec = importlib.util.spec_from_file_location(
            "seed_ai_capital_graph", seed_script
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.write_ai_capital_graph(path)
            return

    path.parent.mkdir(parents=True, exist_ok=True)
    from semantica.context import ContextGraph

    graph = ContextGraph()
    graph.add_node("nvidia", "company", content="NVIDIA (demo fallback — regenerate fixtures).")
    graph.add_node("openai", "company", content="OpenAI (demo fallback — regenerate fixtures).")
    graph.add_edge("nvidia", "openai", "strategic_investment", content="Demo edge.")
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


def _launch_script_path() -> Path:
    return _inference_app_dir() / "launch_app.py"


def _needs_subprocess_uvicorn() -> bool:
    """True when uvicorn.run() would conflict with Jupyter's asyncio loop."""
    if os.environ.get("SEMANTICA_CAIRUN_SUBPROCESS", "").strip() == "1":
        return False
    if os.environ.get("SEMANTICA_ALLOW_NOTEBOOK_UVICORN", "").strip().lower() == "true":
        return False
    if "ipykernel" in sys.modules or "IPython" in sys.modules:
        return True
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _relaunch_in_subprocess_for_uvicorn() -> None:
    """CAI often starts apps from a notebook kernel; uvicorn needs its own process."""
    script = _launch_script_path()
    if not script.is_file():
        _log_step(
            "WARNING: Notebook/asyncio context detected but launch_app.py was not found "
            f"at {script}. Set SEMANTICA_INFERENCE_APP_DIR or run: "
            "python deploy/cloudera/inference-app/launch_app.py"
        )
        return

    _log_step(
        "Notebook or active asyncio event loop detected — "
        f"re-launching Explorer with {sys.executable} {script} "
        "(SEMANTICA_CAIRUN_SUBPROCESS=1)…"
    )
    env = os.environ.copy()
    env["SEMANTICA_CAIRUN_SUBPROCESS"] = "1"
    code = subprocess.call([sys.executable, str(script)], env=env)
    raise SystemExit(code)


def _run_uvicorn(app: object, host: str, port: int) -> None:
    import uvicorn

    if _needs_subprocess_uvicorn():
        _relaunch_in_subprocess_for_uvicorn()
    uvicorn.run(app, host=host, port=port, log_level="info")


def _configure_cai_environment() -> tuple[str, int, Path]:
    port = _resolve_frontend_port()
    # CDSW/CAI reverse-proxy expects the app on loopback, not 0.0.0.0.
    host = os.environ.get("SEMANTICA_HOST", "127.0.0.1")

    app_url = _resolve_cai_app_url()
    if not os.environ.get("ALLOWED_ORIGINS"):
        origins = _collect_cai_allowed_origins(app_url, port)
        if origins:
            os.environ["ALLOWED_ORIGINS"] = ",".join(origins)

    default_graph = _default_graph_path()
    os.environ.setdefault("SEMANTICA_DEMO_GRAPH_PATH", str(default_graph))
    graph_path = Path(
        os.environ.get("SEMANTICA_GRAPH_PATH", str(default_graph))
    ).expanduser()
    _seed_demo_graph(graph_path)
    if graph_path.resolve() == default_graph.resolve():
        manifest = _demo_resources_manifest_path()
        if not manifest.is_file():
            seed_script = _fixtures_dir() / "seed_ai_capital_graph.py"
            if seed_script.is_file():
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "seed_ai_capital_graph", seed_script
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    module.write_sources_manifest(_fixtures_dir(), default_graph)

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
                "Fix on CAI (no npm on engine — typical):",
                "  pip uninstall -y semantica",
                "  pip install --force-reinstall 'semantica[explorer]==0.7.0'",
                "  # restart launch_app.py (or let it download semantica/static from PyPI on startup)",
                "",
                "Fix with Node.js (optional, dev engines only):",
                "  cd explorer && npm ci && npm run build",
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
        _inference_app_dir(),
        Path.cwd(),
    ):
        for parent in (start, *start.parents):
            if (parent / "explorer" / "package.json").is_file() and (
                parent / "pyproject.toml"
            ).is_file():
                return parent
    return None


def _semantica_pypi_version() -> str:
    try:
        return version("semantica")
    except PackageNotFoundError:
        return "0.7.0"


def _try_copy_ui_bundle_from_pypi_wheel() -> bool:
    """Extract semantica/static from the PyPI wheel (no Node.js required)."""
    if os.environ.get("SEMANTICA_SKIP_UI_WHEEL_EXTRACT", "").strip().lower() == "true":
        return False

    import semantica

    pkg_dir = Path(semantica.__file__).resolve().parent
    static_dir = pkg_dir / "static"
    release = _semantica_pypi_version()

    _log_step(
        f"Explorer UI bundle missing — downloading PyPI wheel semantica=={release} "
        "to extract semantica/static/ (no npm required)…"
    )

    with tempfile.TemporaryDirectory(prefix="semantica-ui-") as tmp:
        tmp_path = Path(tmp)
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    f"semantica=={release}",
                    "--no-deps",
                    "-d",
                    str(tmp_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            _log_step(
                "Could not download semantica wheel from PyPI "
                f"(need outbound network). pip said: {(exc.stderr or exc.stdout or '').strip()}"
            )
            return False

        wheels = sorted(tmp_path.glob("semantica-*.whl"))
        if not wheels:
            _log_step("PyPI download did not produce a semantica wheel file.")
            return False

        prefix = "semantica/static/"
        extracted = 0
        with zipfile.ZipFile(wheels[0]) as wheel:
            for name in wheel.namelist():
                if not name.startswith(prefix) or name.endswith("/"):
                    continue
                rel = name[len(prefix) :]
                target = static_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(wheel.read(name))
                extracted += 1

        if extracted == 0:
            _log_step(f"No {prefix} files found inside {wheels[0].name}.")
            return False

    return _static_index_path().is_file()


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

    if _try_copy_ui_bundle_from_pypi_wheel():
        _log_step(f"Explorer UI bundle extracted from PyPI: {_static_index_path()}")
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
    if _needs_subprocess_uvicorn():
        _relaunch_in_subprocess_for_uvicorn()

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
    _register_demo_resource_routes(app)
    manifest = _load_demo_resources_manifest()
    if manifest:
        ref_count = len(manifest.get("references") or [])
        _log_step(
            f"Demo resources manifest loaded ({ref_count} references) — "
            f"GET /api/demo/resources"
        )

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

    _run_uvicorn(app, host=host, port=port)


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
