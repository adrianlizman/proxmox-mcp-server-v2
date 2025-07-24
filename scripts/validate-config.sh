#!/bin/bash

# Proxmox MCP Server - Configuration Validator
# Validates configuration and network connectivity

set -e

echo "========================================"
echo "  Configuration Validator"
echo "========================================"
echo ""

# Default values
PROXMOX_HOST="172.32.0.11"
OLLAMA_HOST="172.32.2.71"
CONFIG_FILE=""

# Detect configuration file
if [ -f ".env" ]; then
    CONFIG_FILE=".env"
    echo "Found Docker configuration: .env"
elif [ -f "config.env" ]; then
    CONFIG_FILE="config.env"
    echo "Found LXC configuration: config.env"
else
    echo "No configuration file found (.env or config.env)"
    echo "Please create one before running validation."
    exit 1
fi

echo "Validating configuration file: $CONFIG_FILE"
echo ""

# Load configuration
source $CONFIG_FILE

# Validate required variables
echo "Checking required configuration variables..."

check_var() {
    local var_name=$1
    local var_value=$2
    local is_required=$3

    if [ -z "$var_value" ]; then
        if [ "$is_required" = "true" ]; then
            echo "✗ $var_name: Missing (required)"
            return 1
        else
            echo "⚠ $var_name: Not set (optional)"
        fi
    else
        echo "✓ $var_name: $var_value"
    fi
    return 0
}

VALIDATION_FAILED=false

check_var "PROXMOX_HOST" "$PROXMOX_HOST" "true" || VALIDATION_FAILED=true
check_var "PROXMOX_USER" "$PROXMOX_USER" "true" || VALIDATION_FAILED=true
check_var "PROXMOX_PASSWORD" "$PROXMOX_PASSWORD" "true" || VALIDATION_FAILED=true
check_var "OLLAMA_HOST" "$OLLAMA_HOST" "true" || VALIDATION_FAILED=true
check_var "OLLAMA_PORT" "$OLLAMA_PORT" "false"
check_var "MCP_SERVER_PORT" "$MCP_SERVER_PORT" "false"

echo ""

# Network connectivity tests
echo "Testing network connectivity..."

test_connection() {
    local host=$1
    local port=$2
    local service=$3

    echo -n "Testing $service ($host:$port)... "

    if timeout 5 bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
        echo "✓ Connected"
        return 0
    else
        echo "✗ Failed"
        return 1
    fi
}

# Test Proxmox connection
test_connection "$PROXMOX_HOST" "8006" "Proxmox Web Interface" || VALIDATION_FAILED=true

# Test Ollama connection
OLLAMA_PORT_TO_TEST=${OLLAMA_PORT:-11434}
test_connection "$OLLAMA_HOST" "$OLLAMA_PORT_TO_TEST" "Ollama API" || VALIDATION_FAILED=true

echo ""

# Test API endpoints if available
echo "Testing API endpoints (if server is running)..."

SERVER_PORT=${MCP_SERVER_PORT:-8000}
LOCAL_SERVER="localhost:$SERVER_PORT"

if timeout 2 bash -c "</dev/tcp/localhost/$SERVER_PORT" 2>/dev/null; then
    echo "✓ MCP Server is running on port $SERVER_PORT"

    # Test health endpoint
    if curl -s -f "http://$LOCAL_SERVER/health" > /dev/null 2>&1; then
        echo "✓ Health endpoint responding"
    else
        echo "✗ Health endpoint not responding"
        VALIDATION_FAILED=true
    fi
else
    echo "ℹ MCP Server not running (this is OK if not started yet)"
fi

echo ""

# Security checks
echo "Security checks..."

if [ "$PROXMOX_VERIFY_SSL" = "false" ]; then
    echo "⚠ SSL verification disabled (OK for development/testing)"
else
    echo "✓ SSL verification enabled"
fi

if [ "$PROXMOX_PASSWORD" = "your_proxmox_password_here" ] || [ "$PROXMOX_PASSWORD" = "changeme" ]; then
    echo "✗ Default password detected - please change PROXMOX_PASSWORD"
    VALIDATION_FAILED=true
else
    echo "✓ Password appears to be customized"
fi

echo ""

# Summary
if [ "$VALIDATION_FAILED" = "true" ]; then
    echo "❌ Validation FAILED - Please fix the issues above"
    exit 1
else
    echo "✅ Configuration validation PASSED"
    echo ""
    echo "Your configuration looks good!"
    echo "You can now start the Proxmox MCP Server."
fi
