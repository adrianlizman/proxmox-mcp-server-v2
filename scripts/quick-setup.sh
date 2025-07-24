#!/bin/bash

# Proxmox MCP Server - Quick Setup Script
# Automatically detects environment and guides through setup

set -e

echo "========================================"
echo "  Proxmox MCP Server - Quick Setup"
echo "========================================"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect environment
echo "Detecting environment..."

HAS_DOCKER=false
HAS_PROXMOX=false
IS_PROXMOX_HOST=false

if command_exists docker; then
    HAS_DOCKER=true
    echo "✓ Docker detected"
fi

if command_exists pct && command_exists pvesh; then
    HAS_PROXMOX=true
    IS_PROXMOX_HOST=true
    echo "✓ Proxmox VE detected (running on Proxmox host)"
elif command_exists pct; then
    HAS_PROXMOX=true
    echo "✓ Proxmox tools detected"
fi

echo ""
echo "Available deployment options:"

if [ "$HAS_DOCKER" = true ]; then
    echo "1) Docker deployment (recommended for general use)"
fi

if [ "$HAS_PROXMOX" = true ]; then
    echo "2) LXC deployment (recommended for Proxmox hosts)"
fi

echo "3) Manual setup guidance"
echo "4) Exit"
echo ""

read -p "Select deployment option (1-4): " choice

case $choice in
    1)
        if [ "$HAS_DOCKER" = false ]; then
            echo "Error: Docker not available. Please install Docker first."
            exit 1
        fi
        echo ""
        echo "Starting Docker deployment..."
        cd docker/
        chmod +x setup-docker.sh
        ./setup-docker.sh
        ;;
    2)
        if [ "$HAS_PROXMOX" = false ]; then
            echo "Error: Proxmox tools not available."
            exit 1
        fi
        echo ""
        echo "Starting LXC deployment..."
        cd lxc/
        chmod +x setup-lxc.sh
        ./setup-lxc.sh
        ;;
    3)
        echo ""
        echo "Manual Setup Guidance:"
        echo "======================"
        echo ""
        echo "1. Choose your deployment method:"
        echo "   - Docker: Good for development and testing"
        echo "   - LXC: Efficient for production on Proxmox"
        echo ""
        echo "2. Configure your environment:"
        echo "   - Edit .env (Docker) or config.env (LXC)"
        echo "   - Set your Proxmox password"
        echo "   - Verify IP addresses match your network"
        echo ""
        echo "3. Follow the specific deployment guide:"
        echo "   - docs/docker-deployment.md"
        echo "   - docs/lxc-deployment.md"
        echo ""
        echo "4. Test the deployment:"
        echo "   - Run testing/test-api.sh"
        echo "   - Check testing/monitor.sh for ongoing monitoring"
        echo ""
        ;;
    4)
        echo "Setup cancelled."
        exit 0
        ;;
    *)
        echo "Invalid option selected."
        exit 1
        ;;
esac

echo ""
echo "Setup completed! Check the documentation for next steps."
