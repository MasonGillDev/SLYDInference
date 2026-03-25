#!/bin/bash

# Full installation and setup script for SlydInference
# This script orchestrates all the installation steps

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  SlydInference Full Setup${NC}"
echo -e "${GREEN}=================================${NC}\n"

# Source .env file if it exists (needed for cloud-init where each runcmd
# runs in its own shell and env vars don't carry over between entries)
ENV_FILE="${ENV_FILE:-/home/ubuntu/.env}"
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Sourcing environment from $ENV_FILE${NC}"
    set -a
    . "$ENV_FILE"
    set +a
fi

# Defaults
DEFAULT_MODEL="HuggingFaceTB/SmolLM3-3B"
MODEL_NAME="${MODEL_NAME:-$DEFAULT_MODEL}"

# Persist HF token to token file if provided via env var
HF_TOKEN_DIR="/home/ubuntu"
if [ -n "${HF_TOKEN:-${HUGGINGFACE_TOKEN:-}}" ]; then
    HF_TOKEN="${HF_TOKEN:-$HUGGINGFACE_TOKEN}"
    export HF_TOKEN
    export HUGGINGFACE_TOKEN="$HF_TOKEN"
    echo "$HF_TOKEN" > "$HF_TOKEN_DIR/.huggingface_token"
    chmod 600 "$HF_TOKEN_DIR/.huggingface_token"
    echo -e "${GREEN}HuggingFace token persisted to $HF_TOKEN_DIR/.huggingface_token${NC}"
else
    echo -e "${YELLOW}No HF_TOKEN set — skipping token setup (gated models will not be accessible)${NC}"
fi

# Apply MODEL_NAME to config files if set
if [ -n "${MODEL_NAME:-}" ]; then
    for cfg in vllm_config.json default_vllm_config.json; do
        if [ -f "$cfg" ]; then
            python3 -c "
import json
with open('$cfg') as f:
    c = json.load(f)
c['model'] = '$MODEL_NAME'
with open('$cfg', 'w') as f:
    json.dump(c, f, indent=2)
" 2>/dev/null && echo -e "${GREEN}Set model=$MODEL_NAME in $cfg${NC}" \
             || echo -e "${YELLOW}Warning: could not update model in $cfg${NC}"
        fi
    done
fi

echo -e "${GREEN}Environment:${NC}"
echo -e "  MODEL_NAME = ${MODEL_NAME}"
if [ -n "${HF_TOKEN:-}" ]; then
    echo -e "  HF_TOKEN   = set (hidden)"
else
    echo -e "  HF_TOKEN   = not set"
fi
echo ""

# Step 1: Install vLLM
echo -e "${YELLOW}Step 1/4: Installing vLLM...${NC}"
./install_vllm.sh
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ vLLM installed successfully${NC}\n"
else
    echo -e "${RED}✗ vLLM installation failed${NC}"
    exit 1
fi

# Step 2: Setup vLLM service
echo -e "${YELLOW}Step 2/4: Setting up vLLM service...${NC}"
./setup_vllm_service.sh
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ vLLM service configured${NC}\n"
else
    echo -e "${RED}✗ vLLM service setup failed${NC}"
    exit 1
fi

# Step 3: Setup SlydLLMSite
echo -e "${YELLOW}Step 3/4: Setting up SlydLLMSite...${NC}"
./setup_slydllmsite.sh
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ SlydLLMSite configured${NC}\n"
else
    echo -e "${RED}✗ SlydLLMSite setup failed${NC}"
    exit 1
fi

# Step 4: Setup nginx
echo -e "${YELLOW}Step 4/4: Setting up nginx...${NC}"
./setup_nginx.sh
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ nginx configured${NC}\n"
else
    echo -e "${RED}✗ nginx setup failed${NC}"
    exit 1
fi

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo -e "${GREEN}=================================${NC}\n"

echo -e "${YELLOW}Service Status:${NC}"
systemctl status vllm --no-pager | head -5
echo ""
systemctl status slydllmsite --no-pager | head -5
echo ""
systemctl status nginx --no-pager | head -5

echo -e "\n${GREEN}Access the control panel at:${NC}"
echo -e "  http://$(hostname -I | awk '{print $1}'):8080"
echo -e "\n${GREEN}API endpoints available at:${NC}"
echo -e "  http://$(hostname -I | awk '{print $1}'):8080/v1/models"
echo -e "  http://$(hostname -I | awk '{print $1}'):8080/v1/chat/completions"

echo -e "\n${YELLOW}Note: vLLM is downloading the model in the background. The management portal will"
echo -e "show the server as DOWN until the download completes and the model is loaded into"
echo -e "GPU memory. This can take several minutes depending on model size and network speed."
echo -e "Monitor progress with: journalctl -u vllm -f${NC}"

