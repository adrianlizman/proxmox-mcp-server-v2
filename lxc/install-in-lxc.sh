#!/bin/bash
set -e

echo "Installing Proxmox MCP Server inside LXC container..."

# Update system first
echo "Updating package lists..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -yq

# Install ALL required Python packages for Ubuntu 24.04
echo "Installing Python and required packages..."
apt-get install -yq \
    python3 \
    python3-pip \
    python3-venv \
    python3.12-venv \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    git \
    curl \
    wget \
    build-essential

# Ensure we're in the right directory
cd /opt/proxmox-mcp-server

# Remove any existing venv directory
echo "Cleaning up any existing virtual environment..."
rm -rf venv

# Create virtual environment with explicit python version and ensurepip
echo "Creating Python virtual environment..."
python3.12 -m venv venv --upgrade-deps

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Verify the virtual environment works
echo "Verifying virtual environment..."
which python
python --version

# Upgrade pip inside the virtual environment
echo "Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs

# Set permissions
echo "Setting permissions..."
chown -R root:root /opt/proxmox-mcp-server
chmod +x app.py

echo "Installation completed successfully!"
echo "Virtual environment created at: /opt/proxmox-mcp-server/venv"
echo "Python executable: $(which python)"
echo "Application is ready to start."
