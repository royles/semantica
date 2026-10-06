#!/usr/bin/env bash
set -euo pipefail

cd /workspace

export PATH="${HOME}/.local/bin:${PATH}"

python3 -m pip install --upgrade pip
# Cookbook notebooks need FAISS, parsers, and local embeddings (no LLM key required).
python3 -m pip install -e ".[dev,explorer,viz,vectorstore-faiss,documents,parse-pdf,embeddings-local,ingest-git,nlp-spacy]"
python3 -m spacy download en_core_web_sm
# Used by cookbook/introduction/02_Data_Ingestion.ipynb (DB ingest demos).
python3 -m pip install "sqlalchemy>=2.0.0"

cd explorer
npm ci
npm run build

echo "Semantica cloud install complete (Python dev+explorer, Explorer UI built)."
