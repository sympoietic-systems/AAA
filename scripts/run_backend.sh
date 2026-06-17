#!/bin/bash
# Resolve the directory of this script
cd "$(dirname "$0")"

export AAA_RUN_MIGRATIONS=true
# Run the backend using uv
uv run python -m backend.main
