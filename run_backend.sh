#!/bin/bash
# Resolve the directory of this script
cd "$(dirname "$0")"

# Run the backend using uv
uv run python -m backend.main
