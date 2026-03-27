#!/bin/bash

# Asset Allocation Dashboard Startup Script
# Usage: ./start.sh [backend|frontend|all]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python not found. Please install Python 3.10+"
        exit 1
    fi
    log_info "Using Python: $($PYTHON_CMD --version)"
}

check_node() {
    if ! command -v node &> /dev/null; then
        log_error "Node.js not found. Please install Node.js 18+"
        exit 1
    fi
    log_info "Using Node.js: $(node --version)"
}

setup_backend() {
    log_info "Setting up backend..."
    cd "$BACKEND_DIR"

    # Create virtual environment if not exists
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        $PYTHON_CMD -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    log_info "Installing Python dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    # Create .env if not exists
    if [ ! -f ".env" ]; then
        log_warn ".env file not found. Creating from .env.example..."
        cp .env.example .env
        log_warn "Please edit .env and add your API keys"
    fi

    log_info "Backend setup complete"
}

setup_frontend() {
    log_info "Setting up frontend..."
    cd "$FRONTEND_DIR"

    # Install dependencies
    if [ ! -d "node_modules" ]; then
        log_info "Installing Node.js dependencies..."
        npm install
    fi

    log_info "Frontend setup complete"
}

start_backend() {
    log_info "Starting backend server..."
    cd "$BACKEND_DIR"
    source venv/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}

start_frontend() {
    log_info "Starting frontend dev server..."
    cd "$FRONTEND_DIR"
    npm run dev
}

start_all() {
    log_info "Starting all services..."

    # Start backend in background
    cd "$BACKEND_DIR"
    source venv/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    log_info "Backend started with PID: $BACKEND_PID"

    # Wait for backend to be ready
    sleep 3

    # Start frontend
    cd "$FRONTEND_DIR"
    npm run dev &
    FRONTEND_PID=$!
    log_info "Frontend started with PID: $FRONTEND_PID"

    # Wait and show info
    log_info "=========================================="
    log_info "Services running:"
    log_info "  Backend:  http://localhost:8000"
    log_info "  Frontend: http://localhost:5173"
    log_info "  API Docs: http://localhost:8000/docs"
    log_info "=========================================="
    log_info "Press Ctrl+C to stop all services"

    # Handle shutdown
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

    # Wait for processes
    wait
}

# Main script
case "${1:-all}" in
    backend)
        check_python
        setup_backend
        start_backend
        ;;
    frontend)
        check_node
        setup_frontend
        start_frontend
        ;;
    setup)
        check_python
        check_node
        setup_backend
        setup_frontend
        log_info "Setup complete! Run './start.sh' to start services"
        ;;
    all|*)
        check_python
        check_node
        setup_backend
        setup_frontend
        start_all
        ;;
esac
