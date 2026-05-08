#!/usr/bin/env bash
# Launches the Streamlit UI. Run from the project root:
#   ./run_app.sh
# or:
#   bash run_app.sh
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:-}:src"
exec python3 -m streamlit run app/streamlit_app.py "$@"
