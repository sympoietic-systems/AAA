#!/bin/bash
# Resolve the directory of the frontend project
cd "$(dirname "$0")/frontend"

# Serve the production build using Vite preview on port 3080
npm run preview -- --port 3080 --host
