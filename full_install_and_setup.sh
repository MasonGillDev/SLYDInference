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

echo -e "\n${YELLOW}Note: Remember to set your HuggingFace token in the control panel for gated models.${NC}"

