#!/bin/bash
# Test runner script for Bindu

set -e

echo "🧪 Bindu Test Suite"
echo "==================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    unit)
        echo -e "${BLUE}Running unit tests...${NC}"
        pytest tests/unit/ -v
        ;;
    integration)
        echo -e "${BLUE}Running integration tests...${NC}"
        pytest tests/integration/ -v
        ;;
    e2e)
        echo -e "${BLUE}Running E2E tests...${NC}"
        pytest tests/e2e/ -v
        ;;
    coverage)
        echo -e "${BLUE}Running tests with coverage...${NC}"
        pytest --cov=bindu --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    fast)
        echo -e "${BLUE}Running fast tests (unit only)...${NC}"
        pytest tests/unit/ -v --tb=short
        ;;
    all)
        echo -e "${BLUE}Running all tests...${NC}"
        pytest -v
        ;;
    *)
        echo "Usage: ./run_tests.sh [unit|integration|e2e|coverage|fast|all]"
        echo ""
        echo "Options:"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  e2e         - Run end-to-end tests only"
        echo "  coverage    - Run all tests with coverage report"
        echo "  fast        - Run fast tests (unit only)"
        echo "  all         - Run all tests (default)"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Tests completed!${NC}"
