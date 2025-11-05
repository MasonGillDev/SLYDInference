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

# Read values from JSON config
MODEL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['model'])")
HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['host'])")
PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['port'])")
MAX_NUM_SEQS=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['max_num_seqs'])")
GPU_MEM=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['gpu_memory_utilization'])")
MAX_MODEL_LEN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('max_model_len', 8192))")

echo -e "${GREEN}Configuration loaded:${NC}"
echo "  Model: $MODEL"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Max sequences: $MAX_NUM_SEQS"
echo "  GPU memory: $GPU_MEM"
echo "  Max model length: $MAX_MODEL_LEN"
echo ""

# Build command
CMD="python -m vllm.entrypoints.openai.api_server"
CMD="$CMD --model $MODEL"
CMD="$CMD --host $HOST"
CMD="$CMD --port $PORT"
CMD="$CMD --max-num-seqs $MAX_NUM_SEQS"
CMD="$CMD --gpu-memory-utilization $GPU_MEM"
CMD="$CMD --max-model-len $MAX_MODEL_LEN"

# Add optional parameters if they exist in config
TENSOR_PARALLEL=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('tensor_parallel_size', ''))" 2>/dev/null)
if [ ! -z "$TENSOR_PARALLEL" ]; then
    CMD="$CMD --tensor-parallel-size $TENSOR_PARALLEL"
fi

TRUST_REMOTE=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print('true' if c.get('trust_remote_code', False) else '')" 2>/dev/null)
if [ "$TRUST_REMOTE" = "true" ]; then
    CMD="$CMD --trust-remote-code"
fi

echo -e "${YELLOW}Starting vLLM server...${NC}"
echo -e "${BLUE}Command: $CMD${NC}"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Run the server
exec $CMD