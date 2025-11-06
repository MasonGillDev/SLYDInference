#!/bin/bash

# vLLM Server Runner Script
# Reads configuration from vllm_config.json

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default config path
CONFIG_FILE="${1:-vllm_config.json}"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Configuration file not found: $CONFIG_FILE${NC}"
    echo "Usage: $0 [config_file]"
    echo "Default: vllm_config.json"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "/opt/vllm-env" ]; then
    echo -e "${RED}Error: Virtual environment not found at /opt/vllm-env${NC}"
    echo "Please run install_vllm.sh first"
    exit 1
fi

# Activate virtual environment
source /opt/vllm-env/bin/activate

# Parse configuration
echo -e "${BLUE}Loading configuration from $CONFIG_FILE...${NC}"

# Display configuration
echo -e "${GREEN}Configuration loaded:${NC}"
python3 build_vllm_command.py "$CONFIG_FILE" --display
echo ""

# Build command dynamically from config
CMD=$(python3 build_vllm_command.py "$CONFIG_FILE")

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to build command from configuration${NC}"
    exit 1
fi

echo -e "${YELLOW}Starting vLLM server...${NC}"
echo -e "${BLUE}Command: $CMD${NC}"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Run the server
exec $CMD