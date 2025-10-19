#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Starting MineContext Development Environment..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "   It's recommended to use .env file for environment variables"
    echo "   Run: cp .env.example .env"
    echo "   Then edit .env with your configuration"
    echo ""
fi

# Check if config exists
if [ ! -f "config/config.yaml" ]; then
    echo -e "${YELLOW}⚠️  Warning: config/config.yaml not found${NC}"
    echo "   Checking for example configurations..."
    
    if [ -f "config/config.ollama.example.yaml" ]; then
        echo -e "${GREEN}✓${NC} Found Ollama example configuration"
        echo "   To use Ollama, run: cp config/config.ollama.example.yaml config/config.yaml"
    fi
    
    echo -e "${RED}✗${NC} Please create config/config.yaml before starting"
    echo "   See docs/LLM_CONFIGURATION_GUIDE.md for configuration help"
    exit 1
fi

echo -e "${GREEN}✓${NC} Configuration file found"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🐍 Activating Python virtual environment..."
    source .venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment activated"
else
    echo -e "${YELLOW}⚠️  No .venv found, using system Python${NC}"
fi

# Check Python dependencies
if ! python3 -c "import opencontext" 2>/dev/null; then
    echo -e "${RED}✗${NC} opencontext module not found. Installing dependencies..."
    pip install -e .
fi

# Start backend and save its PID
echo "🔧 Starting backend service..."
python3 -m opencontext.cli start &
BACKEND_PID=$!

# Wait a bit to check if backend started successfully
sleep 2
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}✗${NC} Backend failed to start. Check logs for details."
    exit 1
fi

echo -e "${GREEN}✓${NC} Backend started with PID: $BACKEND_PID"

# Function to kill the backend process
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo -e "${GREEN}✓${NC} Backend stopped"
    fi
    exit
}

# Trap Ctrl+C and call cleanup
trap cleanup INT TERM

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend && pnpm install
    cd ..
fi

# Start frontend in the foreground
echo "💻 Starting frontend development server..."
cd frontend && pnpm run dev

# Call cleanup when frontend exits
cleanup