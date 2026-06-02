#!/bin/bash

# Script to run MCP tests with various options

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
VERBOSE=false
COVERAGE=false
INTEGRATION=false
WATCH=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -i|--integration)
            INTEGRATION=true
            shift
            ;;
        -w|--watch)
            WATCH=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./scripts/run_mcp_tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose      Verbose output"
            echo "  -c, --coverage     Generate coverage report"
            echo "  -i, --integration  Include integration tests"
            echo "  -w, --watch        Watch mode (requires pytest-watch)"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_ARGS="tests/mcp/"

if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=src/mcp --cov-report=html --cov-report=term-missing"
fi

if [ "$INTEGRATION" = false ]; then
    PYTEST_ARGS="$PYTEST_ARGS -k 'not RealAPI'"
fi

# Run tests
if [ "$WATCH" = true ]; then
    echo -e "${BLUE}Running tests in watch mode...${NC}"
    ptw $PYTEST_ARGS
else
    echo -e "${BLUE}Running MCP tests...${NC}"
    echo -e "${BLUE}Command: pytest $PYTEST_ARGS${NC}"
    echo ""

    pytest $PYTEST_ARGS

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ All tests passed!${NC}"

        if [ "$COVERAGE" = true ]; then
            echo -e "${GREEN}✓ Coverage report generated: htmlcov/index.html${NC}"
        fi
    else
        echo ""
        echo -e "${RED}✗ Some tests failed${NC}"
        exit 1
    fi
fi
