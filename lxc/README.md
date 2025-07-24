# LXC Deployment

Deploy the Proxmox MCP Server as an LXC container on Proxmox.

## Prerequisites

- Proxmox VE server with LXC support
- Ubuntu 22.04 LXC template downloaded
- Root access to Proxmox host
- Network access to Proxmox (172.32.0.11) and Ollama (172.32.2.71)

## Quick Setup

1. **Copy files to Proxmox server:**
   ```bash
   scp -r lxc/ root@172.32.0.11:/tmp/proxmox-mcp-server/
   ```

2. **Connect to Proxmox and run setup:**
   ```bash
   ssh root@172.32.0.11
   cd /tmp/proxmox-mcp-server
   ./setup-lxc.sh
   ```

3. **Edit configuration (before running setup):**
   ```bash
   nano config.env
   ```
   Update the `PROXMOX_PASSWORD` field.

## Container Management

- **Enter container:** `pct enter 200`
- **Stop container:** `pct stop 200`
- **Start container:** `pct start 200`
- **Check service:** `pct exec 200 -- systemctl status proxmox-mcp-server`
- **View logs:** `pct exec 200 -- tail -f /opt/proxmox-mcp-server/logs/app.log`

## Accessing the Service

- **Service URL:** http://172.32.0.200:8000
- **Health Check:** http://172.32.0.200:8000/health
- **API Documentation:** http://172.32.0.200:8000/docs

## Troubleshooting

1. **Check container status:**
   ```bash
   pct list
   ```

2. **View container logs:**
   ```bash
   pct exec 200 -- journalctl -u proxmox-mcp-server -f
   ```

3. **Test connectivity:**
   ```bash
   curl http://172.32.0.200:8000/health
   ```

For more troubleshooting, see the main documentation.
