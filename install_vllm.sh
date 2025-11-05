#!/bin/bash

# vLLM Installation Script for Ubuntu 24.04 LXD Instances
# Run this immediately after LXD instance creation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Log file
LOG_FILE="/var/log/vllm_install.log"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    vLLM Installation for LXD${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Initialize log
echo "=== vLLM Installation Started at $(date) ===" > "$LOG_FILE"

# Step 1: Update system
echo -e "${YELLOW}[1/7]${NC} Updating package lists..."
apt update >> "$LOG_FILE" 2>&1
echo -e "${GREEN}✓${NC} Package lists updated"

# Step 2: Install build tools
echo -e "${YELLOW}[2/7]${NC} Installing build essentials..."
apt install -y build-essential gcc g++ >> "$LOG_FILE" 2>&1
echo -e "${GREEN}✓${NC} Build tools installed"

# Step 3: Install Python development headers
echo -e "${YELLOW}[3/7]${NC} Installing Python development headers..."
apt install -y python3-dev >> "$LOG_FILE" 2>&1
echo -e "${GREEN}✓${NC} Python headers installed"

# Step 4: Install Python venv (must come before pip on Ubuntu 24.04)
echo -e "${YELLOW}[4/7]${NC} Installing Python virtual environment support..."
apt install -y python3.12-venv >> "$LOG_FILE" 2>&1
echo -e "${GREEN}✓${NC} Python venv installed"

# Step 5: Create virtual environment
echo -e "${YELLOW}[5/7]${NC} Creating virtual environment..."
python3 -m venv /opt/vllm-env >> "$LOG_FILE" 2>&1
echo -e "${GREEN}✓${NC} Virtual environment created at /opt/vllm-env"

# Step 6: Activate venv and install pip (avoiding PEP 668 error)
echo -e "${YELLOW}[6/7]${NC} Installing pip in virtual environment..."
source /opt/vllm-env/bin/activate

# Now we're in venv, safe to install pip
curl -s https://bootstrap.pypa.io/get-pip.py | python >> "$LOG_FILE" 2>&1
pip install --upgrade pip >> "$LOG_FILE" 2>&1
echo -e "${GREEN}✓${NC} pip installed and upgraded"

# Step 7: Install PyTorch and vLLM
echo -e "${YELLOW}[7/7]${NC} Installing PyTorch and vLLM (this may take 3-5 minutes)..."
echo "  Installing PyTorch..."
pip install torch >> "$LOG_FILE" 2>&1
echo "  Installing vLLM..."
pip install vllm >> "$LOG_FILE" 2>&1
echo -e "${GREEN}✓${NC} PyTorch and vLLM installed"

# Verify installation
echo ""
echo -e "${BLUE}Verifying installation...${NC}"
python -c "import torch; print(f'PyTorch version: {torch.__version__}')" 2>&1 | tee -a "$LOG_FILE"
python -c "import vllm; print(f'vLLM version: {vllm.__version__}')" 2>&1 | tee -a "$LOG_FILE"

# Check GPU availability
echo ""
echo -e "${BLUE}Checking GPU availability...${NC}"
GPU_CHECK=$(python -c "import torch; print('GPU Available' if torch.cuda.is_available() else 'No GPU detected')" 2>/dev/null)
if [[ $GPU_CHECK == *"GPU Available"* ]]; then
    echo -e "${GREEN}✓${NC} $GPU_CHECK"
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "Unknown GPU")
    echo -e "  GPU: $GPU_NAME"
else
    echo -e "${YELLOW}⚠${NC} $GPU_CHECK"
    echo -e "  Install NVIDIA drivers: apt install nvidia-driver-535"
fi

log "Installation completed successfully"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit vllm_config.json with your model"
echo "2. Run: ./run_vllm_server.sh"
echo "3. Or setup systemd service: sudo ./setup_vllm_service.sh"
echo ""
echo "Virtual environment: /opt/vllm-env"
echo "Log file: $LOG_FILE"