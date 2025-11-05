#!/bin/bash

# Script to install vLLM server as a systemd service

echo "Installing vLLM server as systemd service..."

# Copy service file to systemd directory
sudo cp vllm-server.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable vllm-server.service

echo "Service installed successfully!"
echo ""
echo "Usage:"
echo "  Start service:   sudo systemctl start vllm-server"
echo "  Stop service:    sudo systemctl stop vllm-server"
echo "  Check status:    sudo systemctl status vllm-server"
echo "  View logs:       sudo journalctl -u vllm-server -f"
echo ""
echo "To start the service now, run: sudo systemctl start vllm-server"