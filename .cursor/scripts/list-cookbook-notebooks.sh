#!/usr/bin/env bash
# Print introduction + advanced notebooks in suggested order.
set -euo pipefail
ROOT="/workspace/cookbook"
echo "=== introduction (run in numeric order) ==="
find "$ROOT/introduction" -name '*.ipynb' | sort
echo ""
echo "=== advanced ==="
find "$ROOT/advanced" -name '*.ipynb' | sort
echo ""
echo "=== integrations ==="
find "$ROOT/integrations" -name '*.ipynb' 2>/dev/null | sort || true
