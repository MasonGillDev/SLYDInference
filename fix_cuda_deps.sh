#!/bin/bash

# Quick fix script for CUDA dependency issues

echo "Fixing CUDA dependency issues..."

# Install lsb-release if not present
apt-get install -y lsb-release

# Get Ubuntu version
UBUNTU_VERSION=$(lsb_release -rs)
echo "Ubuntu version: $UBUNTU_VERSION"

# Download and install libtinfo5 directly
echo "Installing libtinfo5..."
wget http://archive.ubuntu.com/ubuntu/pool/universe/n/ncurses/libtinfo5_6.2-0ubuntu2_amd64.deb
dpkg -i libtinfo5_6.2-0ubuntu2_amd64.deb || apt-get install -f -y
rm libtinfo5_6.2-0ubuntu2_amd64.deb

# Try to install libncurses5 if available
echo "Installing libncurses5..."
apt-get install -y libncurses5 2>/dev/null || echo "libncurses5 not critical, continuing..."

echo "Dependencies fixed! You can now proceed with CUDA installation."
echo ""
echo "To continue with CUDA installation, run:"
echo "  sudo apt-get install cuda-toolkit-12-3"
echo ""
echo "Or for minimal installation without nsight-systems:"
echo "  sudo apt-get install --no-install-recommends cuda-cudart-12-3 cuda-compiler-12-3 cuda-libraries-12-3 cuda-libraries-dev-12-3"