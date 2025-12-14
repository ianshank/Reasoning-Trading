#!/bin/bash
# Test runner script for Reasoning Trading Enterprise UI
# Runs backend and frontend tests with optional coverage

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

# Default options
RUN_BACKEND=true
RUN_FRONTEND=true
COVERAGE=false
VERBOSE=false
FAIL_FAST=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            RUN_FRONTEND=false
            shift
            ;;
        --frontend-only)
            RUN_BACKEND=false
            shift
            ;;
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --fail-fast|-x)
            FAIL_FAST=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --backend-only     Run only backend tests"
            echo "  --frontend-only    Run only frontend tests"
            echo "  --coverage, -c     Generate coverage reports"
            echo "  --verbose, -v      Verbose output"
            echo "  --fail-fast, -x    Stop on first failure"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Track test results
BACKEND_EXIT_CODE=0
FRONTEND_EXIT_CODE=0

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Reasoning Trading Enterprise UI Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Backend Tests
if [ "$RUN_BACKEND" = true ]; then
    echo -e "${BLUE}Running Backend Tests...${NC}"
    echo ""

    cd "$PROJECT_ROOT/backend"

    # Check if pytest is installed
    if ! python3 -c "import pytest" 2>/dev/null; then
        print_error "pytest not installed. Installing dev dependencies..."
        cd "$REPO_ROOT"
        pip install -e ".[dev]" || {
            print_error "Failed to install dev dependencies"
            exit 1
        }
        cd "$PROJECT_ROOT/backend"
    fi

    # Build pytest command
    PYTEST_CMD="python3 -m pytest"

    # Add coverage options
    if [ "$COVERAGE" = true ]; then
        PYTEST_CMD="$PYTEST_CMD --cov=enterprise_ui.backend --cov-report=term-missing --cov-report=html:htmlcov"
    fi

    # Add verbose option
    if [ "$VERBOSE" = true ]; then
        PYTEST_CMD="$PYTEST_CMD -v"
    else
        PYTEST_CMD="$PYTEST_CMD -q"
    fi

    # Add fail-fast option
    if [ "$FAIL_FAST" = true ]; then
        PYTEST_CMD="$PYTEST_CMD -x"
    fi

    # Add test discovery
    PYTEST_CMD="$PYTEST_CMD tests/"

    # Run tests
    print_info "Command: $PYTEST_CMD"
    echo ""

    if $PYTEST_CMD; then
        print_status "Backend tests passed"
        if [ "$COVERAGE" = true ]; then
            print_info "Coverage report saved to: backend/htmlcov/index.html"
        fi
    else
        BACKEND_EXIT_CODE=$?
        print_error "Backend tests failed (exit code: $BACKEND_EXIT_CODE)"
    fi

    echo ""
fi

# Frontend Tests
if [ "$RUN_FRONTEND" = true ]; then
    echo -e "${BLUE}Running Frontend Tests...${NC}"
    echo ""

    cd "$PROJECT_ROOT/frontend"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_warning "Frontend dependencies not installed. Installing..."
        npm install || {
            print_error "Failed to install frontend dependencies"
            exit 1
        }
    fi

    # Build test command
    TEST_CMD="npm run test"

    if [ "$COVERAGE" = true ]; then
        TEST_CMD="npm run test:coverage"
    fi

    # Add run option for non-watch mode
    if [ "$VERBOSE" = true ]; then
        TEST_CMD="$TEST_CMD -- --reporter=verbose"
    else
        TEST_CMD="$TEST_CMD -- --reporter=default"
    fi

    # Always run in CI mode (non-watch)
    TEST_CMD="$TEST_CMD --run"

    # Run tests
    print_info "Command: $TEST_CMD"
    echo ""

    if $TEST_CMD; then
        print_status "Frontend tests passed"
        if [ "$COVERAGE" = true ]; then
            print_info "Coverage report saved to: frontend/coverage/index.html"
        fi
    else
        FRONTEND_EXIT_CODE=$?
        print_error "Frontend tests failed (exit code: $FRONTEND_EXIT_CODE)"
    fi

    echo ""
fi

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$RUN_BACKEND" = true ]; then
    if [ $BACKEND_EXIT_CODE -eq 0 ]; then
        echo -e "Backend:  ${GREEN}PASSED${NC}"
    else
        echo -e "Backend:  ${RED}FAILED${NC} (exit code: $BACKEND_EXIT_CODE)"
    fi
fi

if [ "$RUN_FRONTEND" = true ]; then
    if [ $FRONTEND_EXIT_CODE -eq 0 ]; then
        echo -e "Frontend: ${GREEN}PASSED${NC}"
    else
        echo -e "Frontend: ${RED}FAILED${NC} (exit code: $FRONTEND_EXIT_CODE)"
    fi
fi

echo ""

# Coverage reports
if [ "$COVERAGE" = true ]; then
    echo -e "${BLUE}Coverage Reports:${NC}"
    if [ "$RUN_BACKEND" = true ]; then
        echo -e "  Backend:  file://$PROJECT_ROOT/backend/htmlcov/index.html"
    fi
    if [ "$RUN_FRONTEND" = true ]; then
        echo -e "  Frontend: file://$PROJECT_ROOT/frontend/coverage/index.html"
    fi
    echo ""
fi

# Exit with appropriate code
TOTAL_EXIT_CODE=$((BACKEND_EXIT_CODE + FRONTEND_EXIT_CODE))

if [ $TOTAL_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
