#!/bin/bash
set -e

# Start backend and save its PID
source .venv/bin/activate && python3 -m opencontext.cli start &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Function to kill the backend process
cleanup() {
    echo "Stopping backend..."
    kill $BACKEND_PID
    exit
}

# Trap Ctrl+C and call cleanup
trap cleanup INT

# Start frontend in the foreground
cd frontend && pnpm run dev

# Call cleanup when frontend exits
cleanup