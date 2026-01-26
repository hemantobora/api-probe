#!/bin/bash
# Local development runner - sets up venv and runs api-probe

set -e  # Exit on error

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}API-Probe Local Runner${NC}"
echo "======================="
echo

# Check if venv exists, create if not
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate venv
echo -e "${BLUE}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Check if dependencies are installed
if ! python -c "import yaml" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install --quiet -r "$PROJECT_DIR/requirements.txt"
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

# Install api-probe in editable mode if not already installed
if ! python -c "import api_probe" 2>/dev/null; then
    echo -e "${YELLOW}Installing api-probe in development mode...${NC}"
    pip install --quiet -e "$PROJECT_DIR"
    echo -e "${GREEN}✓ api-probe installed${NC}"
fi

echo -e "${GREEN}✓ Environment ready${NC}"
echo

# If arguments provided, run api-probe with them
if [ $# -gt 0 ]; then
    echo -e "${BLUE}Running: api-probe $@${NC}"
    echo
    python -m api_probe.cli "$@"
    EXIT_CODE=$?
    echo
    echo -e "${BLUE}Exit code: $EXIT_CODE${NC}"
    exit $EXIT_CODE
else
    # No arguments - show help
    echo "Usage:"
    echo "  ./run.sh <config-file>              Run probes"
    echo "  ./run.sh validate <config-file>     Validate config"
    echo
    echo "Examples:"
    echo "  ./run.sh examples/passing/simple.yaml"
    echo "  ./run.sh validate examples/passing/simple.yaml"
    echo
    echo -e "${YELLOW}Virtual environment is activated.${NC}"
    echo "You can now run commands directly:"
    echo "  python -m api_probe.cli <config-file>"
    echo "  python -m api_probe.cli validate <config-file>"
fi
