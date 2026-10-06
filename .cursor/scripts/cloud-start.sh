#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"
export SEMANTICA_ALLOW_ANONYMOUS=true

GRAPH="/workspace/.cursor/fixtures/sample_graph.json"
HOST="${SEMANTICA_EXPLORER_HOST:-0.0.0.0}"
PORT="${SEMANTICA_EXPLORER_PORT:-8000}"

mkdir -p "$(dirname "$GRAPH")"

if [[ ! -f "$GRAPH" ]]; then
  python3 - <<'PY'
from pathlib import Path

from semantica.context import ContextGraph

graph = ContextGraph()
graph.add_node("python", "language", content="Python programming language")
graph.add_node("fastapi", "framework", content="FastAPI web framework")
graph.add_edge("python", "fastapi", "enables")

out = Path("/workspace/.cursor/fixtures/sample_graph.json")
graph.save_to_file(str(out))
print(f"Seeded sample graph at {out}")
PY
fi

if curl -sf "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
  echo "Explorer already healthy on port ${PORT}"
  exit 0
fi

for _ in $(seq 1 30); do
  if python3 -c "import semantica" 2>/dev/null; then
    break
  fi
  sleep 1
done

echo "Starting Semantica Explorer on ${HOST}:${PORT} (anonymous dev mode)"
exec semantica-explorer --graph "$GRAPH" --host "$HOST" --port "$PORT" --no-browser
