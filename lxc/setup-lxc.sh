#!/bin/bash
# filepath: z:\github\DEV-TEST\devtest-003\proxmox-mcp-server-v2\lxc\setup-lxc.sh

# Proxmox MCP Server - LXC Setup Script
# This script creates and configures an LXC container for the MCP server

set -e

echo "========================================"
echo "  Proxmox MCP Server - LXC Setup"
echo "========================================"

# Configuration
CONTAINER_ID=200
CONTAINER_NAME="proxmox-mcp-server"
TEMPLATE="ubuntu-24.04-standard_24.04-2_amd64.tar.zst"
STORAGE="local-lvm"
MEMORY=2048
CORES=2
DISK_SIZE=10
NETWORK_BRIDGE="vmbr1"
NETWORK_IP="172.32.0.200/22"
NETWORK_GW="172.32.0.1"

echo "Container Configuration:"
echo "  - ID: $CONTAINER_ID"
echo "  - Name: $CONTAINER_NAME"
echo "  - Template: $TEMPLATE"
echo "  - Memory: ${MEMORY}MB"
echo "  - Cores: $CORES"
echo "  - Disk: ${DISK_SIZE}GB"
echo "  - Network: $NETWORK_IP"
echo ""

read -p "Press Enter to continue or Ctrl+C to abort..."

# Check if container already exists
if pct list | grep -q "$CONTAINER_ID"; then
    echo "Warning: Container $CONTAINER_ID already exists!"
    read -p "Do you want to destroy and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping and destroying existing container..."
        pct stop $CONTAINER_ID || true
        pct destroy $CONTAINER_ID || true
    else
        echo "Aborting setup."
        exit 1
    fi
fi

echo "Step 1: Creating LXC container..."
pct create $CONTAINER_ID /var/lib/vz/template/cache/$TEMPLATE \
    --hostname $CONTAINER_NAME \
    --memory $MEMORY \
    --cores $CORES \
    --rootfs "$STORAGE:${DISK_SIZE}" \
    --net0 name=eth0,bridge=$NETWORK_BRIDGE,ip=$NETWORK_IP,gw=$NETWORK_GW \
    --nameserver 8.8.8.8 \
    --features nesting=1 \
    --unprivileged 1 \
    --onboot 1

echo "Step 2: Starting container..."
pct start $CONTAINER_ID

echo "Step 3: Waiting for container to boot..."
sleep 10

echo "Step 4: Creating application directory..."
pct exec $CONTAINER_ID -- mkdir -p /opt/proxmox-mcp-server

echo "Step 5: Copying application files..."
pct push $CONTAINER_ID requirements.txt /opt/proxmox-mcp-server/requirements.txt
pct push $CONTAINER_ID app.py /opt/proxmox-mcp-server/app.py
pct push $CONTAINER_ID config.env /opt/proxmox-mcp-server/config.env
pct push $CONTAINER_ID install-in-lxc.sh /opt/proxmox-mcp-server/install-in-lxc.sh

echo "Step 6: Running installation inside container..."
pct exec $CONTAINER_ID -- chmod +x /opt/proxmox-mcp-server/install-in-lxc.sh
pct exec $CONTAINER_ID -- /opt/proxmox-mcp-server/install-in-lxc.sh

echo "Step 6.5: Verifying virtual environment..."
pct exec $CONTAINER_ID -- test -f /opt/proxmox-mcp-server/venv/bin/python || echo "WARNING: Virtual environment not found!"

echo "Step 7: Creating systemd service..."
pct exec $CONTAINER_ID -- bash -c 'cat > /etc/systemd/system/proxmox-mcp-server.service << EOF
[Unit]
Description=Proxmox MCP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/proxmox-mcp-server
ExecStart=/opt/proxmox-mcp-server/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'

echo "Step 8: Setting up service permissions..."
pct exec $CONTAINER_ID -- systemctl daemon-reload

echo "Step 9: Enabling and starting service..."
pct exec $CONTAINER_ID -- systemctl enable proxmox-mcp-server
pct exec $CONTAINER_ID -- systemctl start proxmox-mcp-server

echo "Step 10: Checking service status..."
sleep 5
pct exec $CONTAINER_ID -- systemctl status proxmox-mcp-server --no-pager

echo ""
echo "SUCCESS: Proxmox MCP Server LXC container is ready!"
echo ""
echo "Container Information:"
echo "  - Container ID: $CONTAINER_ID"
echo "  - IP Address: $NETWORK_IP"
echo "  - Service URL: http://172.32.0.200:8000"
echo "  - Health Check: http://172.32.0.200:8000/health"
echo ""
echo "Management Commands:"
echo "  - Enter container: pct enter $CONTAINER_ID"
echo "  - Stop container: pct stop $CONTAINER_ID"
echo "  - Start container: pct start $CONTAINER_ID"
echo "  - Check service: pct exec $CONTAINER_ID -- systemctl status proxmox-mcp-server"
echo ""
echo "Setup complete!"
