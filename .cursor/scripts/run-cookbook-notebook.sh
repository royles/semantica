#!/usr/bin/env bash
# Execute a cookbook notebook headlessly and print cell outputs to the terminal.
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

ROOT="/workspace"
COOKBOOK="${ROOT}/cookbook"
LOG_DIR="${ROOT}/.cursor/cookbook-runs"
mkdir -p "$LOG_DIR"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <notebook-path-under-cookbook/>" >&2
  echo "Example: $0 introduction/01_Welcome_to_Semantica.ipynb" >&2
  exit 1
fi

REL="$1"
NB="${COOKBOOK}/${REL}"
if [[ ! -f "$NB" ]]; then
  echo "Notebook not found: $NB" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BASENAME="$(basename "$REL" .ipynb)"
OUT="${LOG_DIR}/${BASENAME}-${STAMP}.ipynb"
LOG="${LOG_DIR}/${BASENAME}-${STAMP}.log"

echo "Running ${REL} ..."
cd "$(dirname "$NB")"
ALLOW_ERRORS="${COOKBOOK_ALLOW_ERRORS:-0}"
EXTRA=()
if [[ "$ALLOW_ERRORS" == "1" ]]; then
  EXTRA+=(--allow-errors)
fi

python3 -m jupyter nbconvert \
  --execute \
  --to notebook \
  "${EXTRA[@]}" \
  --ExecutePreprocessor.timeout=900 \
  --output "$OUT" \
  "$(basename "$NB")" 2>&1 | tee "$LOG"

echo ""
echo "Done. Executed notebook: $OUT"
echo "Log: $LOG"
