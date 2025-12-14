#!/bin/bash
# Development startup script for Reasoning Trading Enterprise UI
# Starts both backend and frontend in development mode

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$PROJECT_ROOT")"

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}Reasoning Trading Development Mode${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command_exists python3; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_status "Python $(python3 --version)"

if ! command_exists node; then
    print_error "Node.js is not installed"
    exit 1
fi
print_status "Node $(node --version)"

if ! command_exists npm; then
    print_error "npm is not installed"
    exit 1
fi
print_status "npm $(npm --version)"

# Check for Redis
if command_exists redis-cli; then
    if redis-cli ping >/dev/null 2>&1; then
        print_status "Redis is running"
    else
        print_warning "Redis is not running. Start it with: redis-server"
        print_warning "Or install with: brew install redis (macOS) / apt-get install redis (Linux)"
    fi
else
    print_warning "Redis CLI not found. Install Redis for caching functionality."
fi

echo ""

# Environment setup
echo -e "${BLUE}Setting up environment...${NC}"

# Check for .env file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    print_warning "No .env file found. Creating from .env.example..."
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        print_status "Created .env file. Please edit it with your configuration."
        echo -e "${YELLOW}Required: ALPACA_API_KEY, ALPACA_API_SECRET${NC}"
        echo -e "${YELLOW}Optional: OPENAI_API_KEY, ANTHROPIC_API_KEY${NC}"
        echo ""
        read -p "Press Enter after configuring .env to continue..."
    else
        print_error ".env.example not found"
        exit 1
    fi
else
    print_status "Found .env file"
fi

# Load environment variables
export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)

echo ""

# Backend setup
echo -e "${BLUE}Setting up backend...${NC}"

cd "$PROJECT_ROOT/backend"

# Check if reasoning_trading is installed
if ! python3 -c "import reasoning_trading" 2>/dev/null; then
    print_warning "reasoning_trading package not found. Installing..."
    cd "$REPO_ROOT"
    pip install -e ".[dev]" || {
        print_error "Failed to install reasoning_trading package"
        exit 1
    }
    cd "$PROJECT_ROOT/backend"
    print_status "Installed reasoning_trading package"
else
    print_status "reasoning_trading package is installed"
fi

# Check backend dependencies
if ! python3 -c "import fastapi" 2>/dev/null; then
    print_warning "Backend dependencies not complete. Installing..."
    cd "$REPO_ROOT"
    pip install -e ".[dev,webui]" || {
        print_error "Failed to install backend dependencies"
        exit 1
    }
    cd "$PROJECT_ROOT/backend"
    print_status "Installed backend dependencies"
else
    print_status "Backend dependencies installed"
fi

echo ""

# Frontend setup
echo -e "${BLUE}Setting up frontend...${NC}"

cd "$PROJECT_ROOT/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    print_warning "Frontend dependencies not installed. Installing..."
    npm install || {
        print_error "Failed to install frontend dependencies"
        exit 1
    }
    print_status "Installed frontend dependencies"
else
    print_status "Frontend dependencies installed"
fi

echo ""

# Create PID file directory
PID_DIR="$PROJECT_ROOT/.pids"
mkdir -p "$PID_DIR"

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"

    # Kill backend
    if [ -f "$PID_DIR/backend.pid" ]; then
        BACKEND_PID=$(cat "$PID_DIR/backend.pid")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill "$BACKEND_PID"
            print_status "Stopped backend (PID: $BACKEND_PID)"
        fi
        rm "$PID_DIR/backend.pid"
    fi

    # Kill frontend
    if [ -f "$PID_DIR/frontend.pid" ]; then
        FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            kill "$FRONTEND_PID"
            print_status "Stopped frontend (PID: $FRONTEND_PID)"
        fi
        rm "$PID_DIR/frontend.pid"
    fi

    echo -e "${GREEN}Development servers stopped${NC}"
    exit 0
}

# Register cleanup on exit
trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo -e "${BLUE}Starting backend server...${NC}"
cd "$PROJECT_ROOT"

# Set development environment variables
export ENVIRONMENT=development
export API_HOST=0.0.0.0
export API_PORT=8000
export API_RELOAD=true
export LOG_LEVEL=DEBUG

python3 -m enterprise_ui.backend.main > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_DIR/backend.pid"

# Wait for backend to start
sleep 3

if kill -0 "$BACKEND_PID" 2>/dev/null; then
    print_status "Backend started (PID: $BACKEND_PID)"
    print_status "Backend API: http://localhost:8000"
    print_status "API Docs: http://localhost:8000/docs"
else
    print_error "Backend failed to start. Check logs/backend.log"
    exit 1
fi

echo ""

# Start frontend
echo -e "${BLUE}Starting frontend server...${NC}"
cd "$PROJECT_ROOT/frontend"

# Set frontend environment variables
export VITE_API_BASE_URL=http://localhost:8000/api/v1
export VITE_WS_BASE_URL=ws://localhost:8000/api/v1/ws

npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PID_DIR/frontend.pid"

# Wait for frontend to start
sleep 3

if kill -0 "$FRONTEND_PID" 2>/dev/null; then
    print_status "Frontend started (PID: $FRONTEND_PID)"
    print_status "Frontend UI: http://localhost:3000"
else
    print_error "Frontend failed to start. Check logs/frontend.log"
    exit 1
fi

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}Development servers are running!${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo -e "${BLUE}Frontend:${NC} http://localhost:3000"
echo -e "${BLUE}Backend API:${NC} http://localhost:8000"
echo -e "${BLUE}API Docs:${NC} http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo -e "  Backend: tail -f $PROJECT_ROOT/logs/backend.log"
echo -e "  Frontend: tail -f $PROJECT_ROOT/logs/frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Wait indefinitely (cleanup will be called on Ctrl+C)
wait
