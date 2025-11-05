#!/bin/bash

# Setup script for SlydLLMSite management interface
# This runs the web UI for managing vLLM configuration

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
echo -e "${BLUE}    SlydLLMSite Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if vLLM is installed
if [ ! -d "/opt/vllm-env" ]; then
    echo -e "${RED}Error: vLLM not installed${NC}"
    echo "Please run install_vllm.sh first"
    exit 1
fi

# Check if vLLM service is setup
if [ ! -f "/opt/vllm/vllm_config.json" ]; then
    echo -e "${RED}Error: vLLM service not configured${NC}"
    echo "Please run setup_vllm_service.sh first"
    exit 1
fi

# Install Flask and dependencies in vLLM environment
echo -e "${YELLOW}Installing Flask dependencies...${NC}"
source /opt/vllm-env/bin/activate
pip install flask requests >> /dev/null 2>&1
echo -e "${GREEN}✓${NC} Flask installed"

# Copy SlydLLMSite to /opt
echo -e "${YELLOW}Setting up SlydLLMSite...${NC}"
cp -r SlydLLMSite /opt/
echo -e "${GREEN}✓${NC} SlydLLMSite copied to /opt"

# Create systemd service for SlydLLMSite
echo -e "${YELLOW}Creating systemd service...${NC}"

cat > /etc/systemd/system/slydllmsite.service << EOF
[Unit]
Description=SlydLLMSite - vLLM Management Interface
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/SlydLLMSite
Environment="PATH=/opt/vllm-env/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/vllm-env/bin/python /opt/SlydLLMSite/app.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓${NC} Service file created"

# Reload systemd
systemctl daemon-reload
echo -e "${GREEN}✓${NC} Systemd reloaded"

# Enable and start service
systemctl enable slydllmsite.service
echo -e "${GREEN}✓${NC} Service enabled"

systemctl start slydllmsite
echo -e "${GREEN}✓${NC} Service started"

# Check if service started successfully
sleep 2
if systemctl is-active --quiet slydllmsite; then
    echo -e "${GREEN}✓${NC} SlydLLMSite is running"
else
    echo -e "${RED}✗${NC} Service failed to start"
    echo "Check logs with: journalctl -u slydllmsite -n 50"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    SlydLLMSite Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Web Interface:${NC} http://$(hostname -I | awk '{print $1}'):5005"
echo ""
echo "Features:"
echo "  • Modify vLLM configuration"
echo "  • Restart vLLM service"
echo "  • Check service status"
echo "  • Validate HuggingFace models"
echo ""
echo "Service commands:"
echo "  systemctl status slydllmsite  - Check status"
echo "  systemctl restart slydllmsite - Restart interface"
echo "  journalctl -u slydllmsite -f  - View logs"