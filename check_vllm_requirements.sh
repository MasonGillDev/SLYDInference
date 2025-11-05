#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "vLLM Server Requirements Check"
echo "========================================="
echo ""

# Function to check command
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $2 is installed"
        if [ ! -z "$3" ]; then
            eval $3
        fi
        return 0
    else
        echo -e "${RED}✗${NC} $2 is NOT installed"
        return 1
    fi
}

# Function to check Python package
check_python_package() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Python package '$1' is installed"
        if [ ! -z "$2" ]; then
            python3 -c "$2"
        fi
        return 0
    else
        echo -e "${RED}✗${NC} Python package '$1' is NOT installed"
        return 1
    fi
}

# System checks
echo "System Requirements:"
echo "-------------------"

# Check for GPU
echo -n "NVIDIA GPU: "
if lspci | grep -i nvidia > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Detected"
    GPU_MODEL=$(lspci | grep -i nvidia | head -1)
    echo "  └─ $GPU_MODEL"
else
    echo -e "${YELLOW}⚠${NC} Not detected (vLLM requires GPU)"
fi

# Check NVIDIA driver
check_command nvidia-smi "NVIDIA Driver" "nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | xargs echo '  └─ Version:'"

# Check CUDA
check_command nvcc "CUDA Toolkit" "nvcc --version | grep 'release' | awk '{print \"  └─ Version:\", \$5}' | sed 's/,//'"

echo ""
echo "Software Requirements:"
echo "---------------------"

# Check Python
check_command python3 "Python 3" "python3 --version | awk '{print \"  └─\", \$0}'"

# Check pip
check_command pip3 "pip3" "pip3 --version | awk '{print \"  └─ Version:\", \$2}'"

echo ""
echo "Python Packages:"
echo "---------------"

# Check for virtual environment
if [ -d "/opt/vllm-env" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment exists at /opt/vllm-env"
    source /opt/vllm-env/bin/activate 2>/dev/null
else
    echo -e "${YELLOW}⚠${NC} No virtual environment at /opt/vllm-env"
fi

# Check Python packages
check_python_package torch "import torch; print(f'  └─ Version: {torch.__version__}')"

if python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} PyTorch CUDA support is available"
    python3 -c "import torch; print(f'  └─ CUDA Version: {torch.version.cuda}')" 2>/dev/null
else
    echo -e "${RED}✗${NC} PyTorch CUDA support is NOT available"
fi

check_python_package vllm "import vllm; print(f'  └─ Version: {vllm.__version__}')"
check_python_package transformers "import transformers; print(f'  └─ Version: {transformers.__version__}')"
check_python_package fastapi
check_python_package uvicorn

echo ""
echo "Service Status:"
echo "--------------"

# Check if service file exists
if [ -f "/etc/systemd/system/vllm-server.service" ]; then
    echo -e "${GREEN}✓${NC} Systemd service file exists"
    
    # Check service status
    if systemctl is-enabled vllm-server &> /dev/null; then
        echo -e "${GREEN}✓${NC} Service is enabled"
    else
        echo -e "${YELLOW}⚠${NC} Service is not enabled"
    fi
    
    if systemctl is-active vllm-server &> /dev/null; then
        echo -e "${GREEN}✓${NC} Service is running"
    else
        echo -e "${YELLOW}⚠${NC} Service is not running"
    fi
else
    echo -e "${RED}✗${NC} Systemd service file not found"
fi

echo ""
echo "Configuration:"
echo "-------------"

# Check for config files
for file in "/opt/vllm/vllm_config_port5002.json" "vllm_config_port5002.json"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} Config file found: $file"
        MODEL=$(python3 -c "import json; print(json.load(open('$file'))['model'])" 2>/dev/null || echo "Not specified")
        PORT=$(python3 -c "import json; print(json.load(open('$file'))['port'])" 2>/dev/null || echo "Unknown")
        echo "  ├─ Model: $MODEL"
        echo "  └─ Port: $PORT"
        break
    fi
done

echo ""
echo "Memory Status:"
echo "-------------"

# Check GPU memory if available
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader,nounits | while read total free; do
        echo "GPU Memory: ${free}MB free / ${total}MB total"
    done
fi

# Check system memory
free -h | grep "^Mem:" | awk '{print "System RAM:", $4, "free /", $2, "total"}'

echo ""
echo "========================================="
echo "Summary:"
echo "========================================="

# Determine overall status
READY=true

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} Python 3 is required"
    READY=false
fi

if ! python3 -c "import vllm" 2>/dev/null; then
    echo -e "${RED}✗${NC} vLLM is not installed"
    READY=false
fi

if ! lspci | grep -i nvidia > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC} No GPU detected - vLLM requires NVIDIA GPU for production use"
fi

if [ "$READY" = true ]; then
    echo -e "${GREEN}✓${NC} System appears ready for vLLM"
    echo ""
    echo "To install missing components, run:"
    echo "  sudo ./setup_vllm_complete.sh"
else
    echo -e "${RED}✗${NC} System is missing required components"
    echo ""
    echo "To install all requirements, run:"
    echo "  sudo ./setup_vllm_complete.sh"
fi