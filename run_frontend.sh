#!/bin/bash
# Load fnm (Fast Node Manager)
export PATH="/home/dev/.local/share/fnm:$PATH"
eval "$(fnm env --use-on-cd)"

# Resolve the directory of the frontend project
cd "$(dirname "$0")/frontend"

# Serve the production build using Vite preview on port 3080
npm run preview -- --port 3080 --host
