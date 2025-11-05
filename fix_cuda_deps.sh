#!/bin/bash

# Quick fix script for CUDA dependency issues

set -e

echo "Fixing CUDA dependency issues..."

# Install lsb-release if not present
apt-get install -y lsb-release

# Get Ubuntu version
UBUNTU_VERSION=$(lsb_release -rs)
echo "Ubuntu version: $UBUNTU_VERSION"

# Install libtinfo5 from Ubuntu 20.04 repository
echo "Adding Ubuntu 20.04 repository for libtinfo5..."
echo "deb http://archive.ubuntu.com/ubuntu/ focal main universe" > /etc/apt/sources.list.d/focal-temp.list

apt-get update

echo "Installing compatibility libraries..."
apt-get install -y libtinfo5 libncurses5 libncurses5-dev

# Clean up temporary repository
rm /etc/apt/sources.list.d/focal-temp.list
apt-get update

echo "Dependencies fixed! You can now proceed with CUDA installation."