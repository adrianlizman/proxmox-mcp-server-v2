#!/bin/bash

# Proxmox MCP Server - Monitoring Script
# Monitors server health and logs status

set -e

# Configuration
SERVER_URL="http://172.32.0.200:8000"  # Change for Docker: http://localhost:8000
CHECK_INTERVAL=30
LOG_FILE="monitoring_$(date +%Y%m%d).log"
DEPLOYMENT_TYPE="lxc"  # or "docker"

echo "========================================"
echo "  Proxmox MCP Server - Monitoring"
echo "========================================"
echo "Server URL: $SERVER_URL"
echo "Check interval: $CHECK_INTERVAL seconds"
echo "Log file: $LOG_FILE"
echo "Deployment type: $DEPLOYMENT_TYPE"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

# Function to log message
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" | tee -a $LOG_FILE
}

# Function to check service health
check_health() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Check API health
    if curl -s -f "$SERVER_URL/health" > /dev/null 2>&1; then
        log_message "✓ API Health: OK"
    else
        log_message "✗ API Health: FAILED"
        return 1
    fi

    # Check specific endpoints
    if curl -s -f "$SERVER_URL/proxmox/nodes" > /dev/null 2>&1; then
        log_message "✓ Proxmox Connection: OK"
    else
        log_message "✗ Proxmox Connection: FAILED"
    fi

    if curl -s -f "$SERVER_URL/ollama/models" > /dev/null 2>&1; then
        log_message "✓ Ollama Connection: OK"
    else
        log_message "✗ Ollama Connection: FAILED"
    fi

    # Check deployment-specific metrics
    if [ "$DEPLOYMENT_TYPE" = "docker" ]; then
        if docker ps | grep -q "proxmox-mcp-server"; then
            log_message "✓ Docker Container: Running"

            # Get container stats
            local stats=$(docker stats --no-stream --format "table {{.CPUPerc}}	{{.MemUsage}}" proxmox-mcp-server | tail -n 1)
            log_message "📊 Container Stats: $stats"
        else
            log_message "✗ Docker Container: Not running"
        fi
    elif [ "$DEPLOYMENT_TYPE" = "lxc" ]; then
        if pct status 200 | grep -q "running"; then
            log_message "✓ LXC Container: Running"

            # Check service status inside container
            if pct exec 200 -- systemctl is-active --quiet proxmox-mcp-server; then
                log_message "✓ Service Status: Active"
            else
                log_message "✗ Service Status: Inactive"
            fi
        else
            log_message "✗ LXC Container: Not running"
        fi
    fi

    return 0
}

# Initialize log file
log_message "Starting monitoring for Proxmox MCP Server"
log_message "Configuration: URL=$SERVER_URL, Interval=${CHECK_INTERVAL}s, Type=$DEPLOYMENT_TYPE"

# Main monitoring loop
while true; do
    if check_health; then
        log_message "🎯 Overall Status: HEALTHY"
    else
        log_message "🚨 Overall Status: UNHEALTHY"
    fi

    echo "---"
    sleep $CHECK_INTERVAL
done
