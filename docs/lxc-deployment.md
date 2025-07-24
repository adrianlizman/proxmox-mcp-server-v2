# LXC Deployment Guide

Complete guide for deploying the Proxmox MCP Server as an LXC container.

## System Requirements

- **Proxmox VE**: 7.0 or later
- **RAM**: 2GB minimum allocated to container
- **Storage**: 10GB for container
- **Network**: Bridge network with internet access

## Prerequisites

### 1. Download Ubuntu Template

On your Proxmox server:

```bash
# List available templates
pveam available | grep ubuntu

# Download Ubuntu 22.04 template
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst

# Verify download
pveam list local
```

### 2. Prepare Project Files

**Option A: Direct Upload to Proxmox**
```bash
# From your local machine, copy files to Proxmox
scp -r lxc/ root@172.32.0.11:/tmp/proxmox-mcp-server/
```

**Option B: Clone from Repository**
```bash
# On Proxmox server
cd /tmp
git clone https://github.com/your-username/proxmox-mcp-server.git
cd proxmox-mcp-server/lxc/
```

## Deployment Steps

### 1. Configure Settings

Edit the configuration before deployment:

```bash
# Navigate to LXC directory
cd /tmp/proxmox-mcp-server/lxc/

# Edit environment configuration
nano config.env
```

Update the following values:
```env
PROXMOX_PASSWORD=your_actual_password
```

### 2. Customize Container Settings (Optional)

Edit `setup-lxc.sh` to modify container specifications:

```bash
nano setup-lxc.sh
```

Key variables to customize:
```bash
CONTAINER_ID=200           # Change if ID 200 is used
CONTAINER_NAME="proxmox-mcp-server"
MEMORY=2048               # RAM in MB
CORES=2                   # CPU cores
DISK_SIZE=10              # Disk size in GB
NETWORK_IP="172.32.0.200/22"  # Container IP
```

### 3. Run Deployment Script

```bash
# Make script executable
chmod +x setup-lxc.sh

# Run the setup script
./setup-lxc.sh
```

The script will:
1. Create the LXC container
2. Start the container
3. Install system dependencies
4. Copy application files
5. Set up Python environment
6. Create and start systemd service

### 4. Verify Deployment

```bash
# Check container status
pct list

# Check service status
pct exec 200 -- systemctl status proxmox-mcp-server

# Test API endpoints
curl http://172.32.0.200:8000/health
curl http://172.32.0.200:8000/proxmox/nodes
```

## Manual Deployment Steps

If you prefer manual setup or need to troubleshoot:

### 1. Create Container Manually

```bash
pct create 200 /var/lib/vz/template/cache/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
    --hostname proxmox-mcp-server \
    --memory 2048 \
    --cores 2 \
    --rootfs local-lvm:10 \
    --net0 name=eth0,bridge=vmbr0,ip=172.32.0.200/22,gw=172.32.0.1 \
    --nameserver 8.8.8.8 \
    --features nesting=1 \
    --unprivileged 1 \
    --onboot 1

# Start the container
pct start 200
```

### 2. Install Dependencies

```bash
# Enter container
pct enter 200

# Update system
apt update && apt upgrade -y

# Install Python and tools
apt install -y python3 python3-pip python3-venv curl wget git nano

# Exit container
exit
```

### 3. Setup Application

```bash
# Create application directory
pct exec 200 -- mkdir -p /opt/proxmox-mcp-server

# Copy files
pct push 200 app.py /opt/proxmox-mcp-server/
pct push 200 requirements.txt /opt/proxmox-mcp-server/
pct push 200 config.env /opt/proxmox-mcp-server/

# Setup Python environment
pct exec 200 -- bash -c "
cd /opt/proxmox-mcp-server
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p logs
"
```

### 4. Create Systemd Service

```bash
pct exec 200 -- bash -c 'cat > /etc/systemd/system/proxmox-mcp-server.service << EOF
[Unit]
Description=Proxmox MCP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/proxmox-mcp-server
Environment=PATH=/opt/proxmox-mcp-server/venv/bin
ExecStart=/opt/proxmox-mcp-server/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'

# Enable and start service
pct exec 200 -- systemctl daemon-reload
pct exec 200 -- systemctl enable proxmox-mcp-server
pct exec 200 -- systemctl start proxmox-mcp-server
```

## Container Management

### Basic Operations

```bash
# Start container
pct start 200

# Stop container
pct stop 200

# Restart container
pct restart 200

# Enter container shell
pct enter 200

# Execute commands in container
pct exec 200 -- command

# Show container configuration
pct config 200
```

### Service Management

```bash
# Check service status
pct exec 200 -- systemctl status proxmox-mcp-server

# View service logs
pct exec 200 -- journalctl -u proxmox-mcp-server -f

# Restart service
pct exec 200 -- systemctl restart proxmox-mcp-server

# Stop service
pct exec 200 -- systemctl stop proxmox-mcp-server
```

### Log Management

```bash
# View application logs
pct exec 200 -- tail -f /opt/proxmox-mcp-server/logs/app.log

# View systemd logs
pct exec 200 -- journalctl -u proxmox-mcp-server --since "1 hour ago"

# Clear logs
pct exec 200 -- truncate -s 0 /opt/proxmox-mcp-server/logs/app.log
```

## Configuration Management

### Update Configuration

```bash
# Edit configuration
pct exec 200 -- nano /opt/proxmox-mcp-server/config.env

# Restart service to apply changes
pct exec 200 -- systemctl restart proxmox-mcp-server
```

### Update Application

```bash
# Copy updated files
pct push 200 new-app.py /opt/proxmox-mcp-server/app.py

# Restart service
pct exec 200 -- systemctl restart proxmox-mcp-server
```

### Update Dependencies

```bash
# Enter container and update
pct exec 200 -- bash -c "
cd /opt/proxmox-mcp-server
source venv/bin/activate
pip install --upgrade -r requirements.txt
"

# Restart service
pct exec 200 -- systemctl restart proxmox-mcp-server
```

## Network Configuration

### Default Network Setup

The container uses a bridge network configuration:
- **IP Address**: 172.32.0.200/22
- **Gateway**: 172.32.0.1
- **DNS**: 8.8.8.8

### Custom Network Configuration

To use different network settings, modify the container creation command:

```bash
# Example: Different IP range
pct create 200 ... --net0 name=eth0,bridge=vmbr0,ip=192.168.1.200/24,gw=192.168.1.1
```

### Firewall Configuration

Configure Proxmox firewall for the container:

```bash
# Enable firewall for container
pct set 200 -firewall 1

# Add firewall rules (via web interface or pve-firewall)
# Allow HTTP traffic on port 8000
```

## Storage Management

### Container Storage

```bash
# Check container storage usage
pct exec 200 -- df -h

# Resize container disk (if needed)
pct resize 200 rootfs +5G
```

### Backup and Restore

```bash
# Create backup
vzdump 200 --storage local --compress gzip

# List backups
ls /var/lib/vz/dump/

# Restore from backup
pct restore 201 /var/lib/vz/dump/vzdump-lxc-200-*.tar.gz
```

## Performance Tuning

### Resource Allocation

```bash
# Increase memory
pct set 200 -memory 4096

# Add CPU cores
pct set 200 -cores 4

# Set CPU limits
pct set 200 -cpulimit 2
```

### Optimization Tips

1. **Use local storage** for better I/O performance
2. **Enable nesting** if running containers inside LXC
3. **Allocate appropriate resources** based on usage
4. **Monitor resource usage** regularly

## Security Considerations

### Container Security

1. **Use unprivileged containers** (default in setup)
2. **Limit container capabilities** as needed
3. **Regular updates** of container and packages
4. **Network segmentation** with firewall rules

### Access Control

```bash
# Set container permissions
pct set 200 -unprivileged 1

# Configure container features
pct set 200 -features nesting=1,keyctl=1
```

## Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   # Check container status
   pct status 200

   # View container logs
   journalctl -u pve-container@200.service
   ```

2. **Service not accessible**
   ```bash
   # Check if service is running
   pct exec 200 -- systemctl status proxmox-mcp-server

   # Test network connectivity
   ping 172.32.0.200
   ```

3. **Permission issues**
   ```bash
   # Check file permissions
   pct exec 200 -- ls -la /opt/proxmox-mcp-server/

   # Fix permissions if needed
   pct exec 200 -- chown -R root:root /opt/proxmox-mcp-server/
   ```

### Debug Mode

Enable debug logging:

```bash
pct exec 200 -- sed -i 's/LOG_LEVEL=INFO/LOG_LEVEL=DEBUG/' /opt/proxmox-mcp-server/config.env
pct exec 200 -- systemctl restart proxmox-mcp-server
```

For more detailed troubleshooting, see the main [Troubleshooting Guide](troubleshooting.md).

## Migration and Upgrades

### Container Migration

```bash
# Migrate to another Proxmox node
pct migrate 200 target-node

# Migrate with storage
pct migrate 200 target-node --restart
```

### Application Upgrades

```bash
# Backup current version
pct exec 200 -- cp -r /opt/proxmox-mcp-server /opt/proxmox-mcp-server.backup

# Apply updates
# (copy new files and restart service)

# Rollback if needed
pct exec 200 -- rm -rf /opt/proxmox-mcp-server
pct exec 200 -- mv /opt/proxmox-mcp-server.backup /opt/proxmox-mcp-server
pct exec 200 -- systemctl restart proxmox-mcp-server
```
