#!/usr/bin/env bash
set -euo pipefail

cd /workspace

export PATH="${HOME}/.local/bin:${PATH}"

python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev,explorer]"

cd explorer
npm ci
npm run build

echo "Semantica cloud install complete (Python dev+explorer, Explorer UI built)."
