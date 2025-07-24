#!/bin/bash

# Proxmox MCP Server - Docker Setup Script
# This script sets up the Proxmox MCP Server using Docker

set -e

echo "========================================"
echo "  Proxmox MCP Server - Docker Setup"
echo "========================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "Step 1: Setting up environment configuration..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.template .env
    echo "Created .env file from template"
    echo "Please edit .env file with your Proxmox credentials:"
    echo "  - Update PROXMOX_PASSWORD with your actual password"
    echo ""
    read -p "Press Enter to continue after editing .env file..."
else
    echo ".env file already exists"
fi

echo "Step 2: Creating necessary directories..."
mkdir -p logs data

echo "Step 3: Building and starting services..."
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d

echo "Step 4: Waiting for services to start..."
sleep 10

# Check if service is running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "SUCCESS: Proxmox MCP Server is running!"
    echo ""
    echo "Service Information:"
    echo "  - Server URL: http://localhost:8000"
    echo "  - Health Check: http://localhost:8000/health"
    echo "  - API Documentation: http://localhost:8000/docs"
    echo ""
    echo "Check logs with: docker-compose logs -f"
    echo "Stop service with: docker-compose down"
    echo ""
else
    echo "Warning: Service may not have started correctly"
    echo "Check logs with: docker-compose logs"
fi

echo "Setup complete!"
