#!/bin/bash

# Test script to verify vLLM and SlydLLMSite integration

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    Testing vLLM Integration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test 1: Check vLLM service
echo -e "${YELLOW}Test 1: vLLM Service Status${NC}"
if systemctl is-active --quiet vllm; then
    echo -e "${GREEN}✓${NC} vLLM service is running"
else
    echo -e "${RED}✗${NC} vLLM service is not running"
    echo "  Run: systemctl start vllm"
fi

# Test 2: Check vLLM API
echo -e "${YELLOW}Test 2: vLLM API Response${NC}"
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5002/v1/models 2>/dev/null || echo "000")
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓${NC} vLLM API is responding (port 5002)"
    echo "  Models endpoint working"
else
    echo -e "${RED}✗${NC} vLLM API not responding (HTTP $response)"
fi

# Test 3: Check SlydLLMSite service
echo -e "${YELLOW}Test 3: SlydLLMSite Service Status${NC}"
if systemctl is-active --quiet slydllmsite 2>/dev/null; then
    echo -e "${GREEN}✓${NC} SlydLLMSite service is running"
else
    echo -e "${YELLOW}⚠${NC} SlydLLMSite service is not running or not installed"
    echo "  Run: ./setup_slydllmsite.sh to install"
fi

# Test 4: Check SlydLLMSite web interface
echo -e "${YELLOW}Test 4: SlydLLMSite Web Interface${NC}"
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5005 2>/dev/null || echo "000")
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓${NC} SlydLLMSite web interface is accessible (port 5005)"
else
    echo -e "${YELLOW}⚠${NC} SlydLLMSite web interface not responding (HTTP $response)"
fi

# Test 5: Check config file
echo -e "${YELLOW}Test 5: Configuration File${NC}"
if [ -f "/opt/vllm/vllm_config.json" ]; then
    echo -e "${GREEN}✓${NC} vLLM config file exists"
    MODEL=$(python3 -c "import json; print(json.load(open('/opt/vllm/vllm_config.json'))['model'])" 2>/dev/null || echo "Error reading")
    echo "  Current model: $MODEL"
else
    echo -e "${RED}✗${NC} Config file not found at /opt/vllm/vllm_config.json"
fi

# Test 6: Test vLLM inference
echo -e "${YELLOW}Test 6: vLLM Inference Test${NC}"
if [ "$response" = "200" ]; then
    inference_response=$(curl -s -X POST http://localhost:5002/v1/completions \
        -H "Content-Type: application/json" \
        -d '{"model": "HuggingFaceTB/SmolLM3-3B", "prompt": "Hello", "max_tokens": 5}' 2>/dev/null)
    
    if echo "$inference_response" | grep -q "choices"; then
        echo -e "${GREEN}✓${NC} vLLM inference is working"
    else
        echo -e "${YELLOW}⚠${NC} vLLM inference test failed"
        echo "  Response: $inference_response"
    fi
else
    echo -e "${YELLOW}⚠${NC} Skipped - vLLM API not running"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "vLLM API: http://localhost:5002/v1/models"
echo "SlydLLMSite: http://localhost:5005"
echo ""
echo "To view all logs:"
echo "  journalctl -u vllm -f        # vLLM logs"
echo "  journalctl -u slydllmsite -f # SlydLLMSite logs"