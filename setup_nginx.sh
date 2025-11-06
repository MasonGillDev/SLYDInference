#!/bin/bash

# Simple nginx setup script for fresh LXD instance

set -e

echo "Installing nginx..."
apt-get update
apt-get install -y nginx

echo "Copying nginx configuration..."
# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cp "$SCRIPT_DIR/nginx.conf" /etc/nginx/sites-available/slyd

echo "Disabling default nginx site..."
rm -f /etc/nginx/sites-enabled/default

echo "Enabling SlydInference site..."
ln -sf /etc/nginx/sites-available/slyd /etc/nginx/sites-enabled/slyd

echo "Testing nginx configuration..."
nginx -t

echo "Restarting nginx..."
systemctl restart nginx
systemctl enable nginx

echo "Nginx setup complete!"
echo "Nginx is now proxying:"
echo "  - http://your-server/ -> Configuration interface (port 5005)"
echo "  - http://your-server/v1/* -> vLLM API (port 5002)"