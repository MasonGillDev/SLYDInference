#!/bin/bash

# Setup vLLM as a systemd service
# This script creates and installs the systemd service

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    vLLM Systemd Service Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if [ ! -d "/opt/vllm-env" ]; then
    echo -e "${RED}Error: vLLM not installed${NC}"
    echo "Please run install_vllm.sh first"
    exit 1
fi

if [ ! -f "vllm_config.json" ]; then
    echo -e "${RED}Error: vllm_config.json not found${NC}"
    echo "Please create vllm_config.json first"
    exit 1
fi

if [ ! -f "run_vllm_server.sh" ]; then
    echo -e "${RED}Error: run_vllm_server.sh not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} All prerequisites met"

# Get current directory for absolute paths
INSTALL_DIR=$(pwd)

# Copy files to /opt/vllm
echo -e "${YELLOW}Setting up vLLM directory...${NC}"
mkdir -p /opt/vllm
cp vllm_config.json /opt/vllm/
cp run_vllm_server.sh /opt/vllm/
chmod +x /opt/vllm/run_vllm_server.sh
echo -e "${GREEN}✓${NC} Files copied to /opt/vllm"

# Create systemd service file
echo -e "${YELLOW}Creating systemd service...${NC}"

cat > /etc/systemd/system/vllm.service << EOF
[Unit]
Description=vLLM API Server
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/vllm
Environment="PATH=/opt/vllm-env/bin:/usr/local/bin:/usr/bin:/bin"

# Run the server script with config file
ExecStart=/opt/vllm/run_vllm_server.sh /opt/vllm/vllm_config.json

# Restart policy
Restart=on-failure
RestartSec=10

# Resource limits
LimitNOFILE=65536
TasksMax=infinity

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓${NC} Service file created"

# Reload systemd
echo -e "${YELLOW}Reloading systemd...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓${NC} Systemd reloaded"

# Enable service
echo -e "${YELLOW}Enabling service...${NC}"
systemctl enable vllm.service
echo -e "${GREEN}✓${NC} Service enabled (will start on boot)"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    Service Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service Management Commands:"
echo -e "${BLUE}Start service:${NC}   systemctl start vllm"
echo -e "${BLUE}Stop service:${NC}    systemctl stop vllm"
echo -e "${BLUE}Restart service:${NC} systemctl restart vllm"
echo -e "${BLUE}Check status:${NC}    systemctl status vllm"
echo -e "${BLUE}View logs:${NC}       journalctl -u vllm -f"
echo ""
echo "Configuration file: /opt/vllm/vllm_config.json"
echo ""
echo -e "${YELLOW}To start the service now, run:${NC}"
echo "  systemctl start vllm"