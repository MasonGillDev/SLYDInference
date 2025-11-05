#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Script must be run as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

log_info "Starting vLLM server setup for LXD instance..."

# Update system packages
log_info "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install basic dependencies
log_info "Installing basic dependencies..."
apt-get install -y \
    build-essential \
    software-properties-common \
    curl \
    wget \
    git \
    htop \
    nvtop \
    pciutils \
    lshw

# Check for NVIDIA GPU
log_info "Checking for NVIDIA GPU..."
if lspci | grep -i nvidia > /dev/null; then
    log_info "NVIDIA GPU detected"
    GPU_PRESENT=true
else
    log_warn "No NVIDIA GPU detected. vLLM requires GPU for optimal performance."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    GPU_PRESENT=false
fi

# Install NVIDIA drivers if GPU is present
if [ "$GPU_PRESENT" = true ]; then
    log_info "Checking NVIDIA drivers..."
    
    if ! command -v nvidia-smi &> /dev/null; then
        log_info "Installing NVIDIA drivers..."
        
        # Add NVIDIA PPA
        add-apt-repository ppa:graphics-drivers/ppa -y
        apt-get update
        
        # Install recommended driver
        ubuntu-drivers autoinstall
        
        # Alternative: Install specific version
        # apt-get install -y nvidia-driver-535
        
        log_warn "NVIDIA drivers installed. A reboot may be required."
        log_info "After reboot, run this script again to continue setup."
        read -p "Reboot now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            reboot
        fi
    else
        log_info "NVIDIA drivers already installed"
        nvidia-smi
    fi
    
    # Install CUDA
    log_info "Checking CUDA installation..."
    if ! command -v nvcc &> /dev/null; then
        log_info "Installing CUDA toolkit..."
        
        # Fix libtinfo5 dependency issue for newer Ubuntu versions
        log_info "Installing compatibility libraries..."
        
        # Check Ubuntu version
        UBUNTU_VERSION=$(lsb_release -rs)
        
        if [[ "$UBUNTU_VERSION" == "22.04" ]] || [[ "$UBUNTU_VERSION" > "22.04" ]]; then
            # For Ubuntu 22.04+, we need to add libtinfo5
            log_info "Installing libtinfo5 for compatibility..."
            
            # Download and install libtinfo5 directly
            wget http://archive.ubuntu.com/ubuntu/pool/universe/n/ncurses/libtinfo5_6.2-0ubuntu2_amd64.deb
            dpkg -i libtinfo5_6.2-0ubuntu2_amd64.deb || apt-get install -f -y
            rm libtinfo5_6.2-0ubuntu2_amd64.deb
            
            # Try to install libncurses5 if available
            apt-get install -y libncurses5 || log_warn "libncurses5 not available, continuing without it"
        fi
        
        # Download CUDA installer
        CUDA_VERSION="12.3"
        wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
        dpkg -i cuda-keyring_1.1-1_all.deb
        rm cuda-keyring_1.1-1_all.deb
        
        apt-get update
        
        # Install only CUDA toolkit without nsight-systems if it causes issues
        apt-get install -y cuda-toolkit-12-3 || {
            log_warn "Full CUDA toolkit installation failed, trying minimal installation..."
            apt-get install -y --no-install-recommends \
                cuda-cudart-12-3 \
                cuda-compiler-12-3 \
                cuda-libraries-12-3 \
                cuda-libraries-dev-12-3 \
                libcublas-12-3 \
                libcublas-dev-12-3
        }
        
        # Add CUDA to PATH
        echo 'export PATH=/usr/local/cuda/bin:$PATH' >> /etc/profile.d/cuda.sh
        echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> /etc/profile.d/cuda.sh
        source /etc/profile.d/cuda.sh
        
        log_info "CUDA ${CUDA_VERSION} installed"
    else
        log_info "CUDA already installed"
        nvcc --version
    fi
fi

# Install Python 3 and pip
log_info "Installing Python 3 and pip..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv

# Upgrade pip
log_info "Upgrading pip..."
pip3 install --upgrade pip

# Create virtual environment for vLLM
log_info "Creating Python virtual environment..."
VENV_DIR="/opt/vllm-env"
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Install PyTorch with CUDA support
log_info "Installing PyTorch..."
if [ "$GPU_PRESENT" = true ]; then
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
else
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Install vLLM
log_info "Installing vLLM..."
pip install vllm

# Install additional dependencies
log_info "Installing additional Python packages..."
pip install \
    numpy \
    pandas \
    transformers \
    accelerate \
    sentencepiece \
    protobuf \
    fastapi \
    uvicorn \
    openai

# Create vLLM user (optional, for security)
log_info "Setting up vLLM user..."
if ! id -u vllm > /dev/null 2>&1; then
    useradd -m -s /bin/bash vllm
    usermod -aG video vllm  # Add to video group for GPU access
fi

# Copy configuration and scripts
log_info "Setting up vLLM configuration..."
VLLM_DIR="/opt/vllm"
mkdir -p $VLLM_DIR

# Copy files if they exist in current directory
if [ -f "vllm_config_port5002.json" ]; then
    cp vllm_config_port5002.json $VLLM_DIR/
    chown vllm:vllm $VLLM_DIR/vllm_config_port5002.json
fi

if [ -f "launch_vllm_server.py" ]; then
    cp launch_vllm_server.py $VLLM_DIR/
    chown vllm:vllm $VLLM_DIR/launch_vllm_server.py
    chmod +x $VLLM_DIR/launch_vllm_server.py
fi

# Create wrapper script that uses the virtual environment
cat > $VLLM_DIR/run_vllm.sh << 'EOF'
#!/bin/bash
source /opt/vllm-env/bin/activate
cd /opt/vllm
python3 launch_vllm_server.py --config vllm_config_port5002.json "$@"
EOF

chmod +x $VLLM_DIR/run_vllm.sh
chown vllm:vllm $VLLM_DIR/run_vllm.sh

# Update systemd service file to use virtual environment
cat > /etc/systemd/system/vllm-server.service << EOF
[Unit]
Description=vLLM Server on Port 5002
After=network.target

[Service]
Type=simple
User=vllm
Group=vllm
WorkingDirectory=/opt/vllm
Environment="PATH=/opt/vllm-env/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin"
Environment="LD_LIBRARY_PATH=/usr/local/cuda/lib64"
ExecStart=/opt/vllm/run_vllm.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
LimitNOFILE=65536
TasksMax=infinity

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable vllm-server.service

# Test Python and vLLM installation
log_info "Testing installations..."
source $VENV_DIR/bin/activate

python3 -c "import torch; print(f'PyTorch version: {torch.__version__}')"
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
if [ "$GPU_PRESENT" = true ]; then
    python3 -c "import torch; print(f'CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
fi
python3 -c "import vllm; print(f'vLLM version: {vllm.__version__}')"

# Display summary
echo ""
log_info "==================== Setup Complete ===================="
log_info "vLLM server has been successfully installed!"
echo ""
log_info "Configuration file: /opt/vllm/vllm_config_port5002.json"
log_info "Launch script: /opt/vllm/launch_vllm_server.py"
log_info "Service name: vllm-server"
echo ""
log_info "Next steps:"
log_info "1. Edit the configuration file to specify your model:"
log_info "   nano /opt/vllm/vllm_config_port5002.json"
log_info ""
log_info "2. Start the vLLM server:"
log_info "   systemctl start vllm-server"
log_info ""
log_info "3. Check server status:"
log_info "   systemctl status vllm-server"
log_info ""
log_info "4. View logs:"
log_info "   journalctl -u vllm-server -f"
log_info ""
log_info "5. Test the API endpoint:"
log_info "   curl http://localhost:5002/v1/models"
log_info "========================================================"

# Check if GPU is available but drivers need reboot
if [ "$GPU_PRESENT" = true ] && ! nvidia-smi > /dev/null 2>&1; then
    log_warn "GPU detected but drivers not active. Please reboot and run:"
    log_warn "  systemctl start vllm-server"
fi