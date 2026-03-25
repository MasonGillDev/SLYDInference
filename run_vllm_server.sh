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

# Source .env file if it exists (needed for cloud-init where each runcmd
# runs in its own shell and env vars don't carry over between entries)
ENV_FILE="${ENV_FILE:-/home/ubuntu/.env}"
if [ -f "$ENV_FILE" ]; then
    echo -e "${BLUE}Sourcing environment from $ENV_FILE${NC}"
    set -a
    . "$ENV_FILE"
    set +a
fi

# Defaults
DEFAULT_MODEL="HuggingFaceTB/SmolLM3-3B"

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

# Resolve HuggingFace token: env var > token file > none
if [ -n "${HF_TOKEN:-}" ]; then
    export HUGGINGFACE_TOKEN="$HF_TOKEN"
    echo -e "${GREEN}HuggingFace token loaded from environment${NC}"
elif [ -n "${HUGGINGFACE_TOKEN:-}" ]; then
    export HF_TOKEN="$HUGGINGFACE_TOKEN"
    echo -e "${GREEN}HuggingFace token loaded from environment${NC}"
elif [ -f "/home/ubuntu/.huggingface_token" ]; then
    export HUGGINGFACE_TOKEN=$(cat "/home/ubuntu/.huggingface_token")
    export HF_TOKEN="$HUGGINGFACE_TOKEN"
    echo -e "${GREEN}HuggingFace token loaded from /home/ubuntu/.huggingface_token${NC}"
else
    echo -e "${YELLOW}No HuggingFace token found — gated models will not be accessible${NC}"
fi

# Override model in config if MODEL_NAME is set in the environment
if [ -n "${MODEL_NAME:-}" ]; then
    echo -e "${BLUE}Overriding model with MODEL_NAME=$MODEL_NAME${NC}"
    python3 -c "
import json, sys
cfg = json.load(open('$CONFIG_FILE'))
cfg['model'] = '$MODEL_NAME'
json.dump(cfg, open('$CONFIG_FILE', 'w'), indent=2)
" 2>/dev/null && echo -e "${GREEN}Model updated in $CONFIG_FILE${NC}" \
             || echo -e "${YELLOW}Warning: could not update model in config — using config file value${NC}"
fi

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