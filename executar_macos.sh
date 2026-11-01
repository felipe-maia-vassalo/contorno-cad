#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

# Prefer a dedicated prepared environment. The fallback is available only
# in the original development workspace; it is not part of the source archive.
if [ -x .venv/bin/python ]; then
  CAD_PYTHON="$PWD/.venv/bin/python"
elif [ -x ../../work/.venv/bin/python ]; then
  CAD_PYTHON="$(cd ../../work/.venv/bin && pwd)/python"
else
  if command -v python3.12 >/dev/null 2>&1; then
    CAD_BASE_PYTHON="$(command -v python3.12)"
  else
    echo 'Install Python 3.12 from python.org, then run this command again.'
    echo 'This project was validated with Python 3.12 on macOS Apple Silicon.'
    exit 1
  fi
  "$CAD_BASE_PYTHON" -m venv .venv
  CAD_PYTHON="$PWD/.venv/bin/python"
  "$CAD_PYTHON" -m pip install -r requirements.txt
  "$CAD_PYTHON" scripts/preparar_casadi.py
fi
"$CAD_PYTHON" scripts/preparar_casadi.py --verificar
exec "$CAD_PYTHON" -m streamlit run iniciar_cad.py --server.address 127.0.0.1
