#!/bin/bash

# Proxmox MCP Server - LXC Internal Installation Script
# This script runs inside the LXC container to set up the application

set -e

echo "Installing Proxmox MCP Server inside LXC container..."

# Create virtual environment
echo "Creating Python virtual environment..."
cd /opt/proxmox-mcp-server
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs

# Set permissions
echo "Setting permissions..."
chown -R root:root /opt/proxmox-mcp-server
chmod +x app.py

echo "Installation completed successfully!"
echo "Application is ready to start."
