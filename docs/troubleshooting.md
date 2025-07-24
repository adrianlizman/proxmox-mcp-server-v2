# Troubleshooting Guide

Common issues and solutions for the Proxmox MCP Server.

## Service Issues

### Service Won't Start

**Symptoms**: Container/service fails to start or exits immediately

**Solutions**:
1. Check configuration file:
   ```bash
   # Docker
   cat .env

   # LXC
   cat /opt/proxmox-mcp-server/config.env
   ```

2. Verify logs:
   ```bash
   # Docker
   docker-compose logs proxmox-mcp-server

   # LXC
   pct exec 200 -- journalctl -u proxmox-mcp-server -f
   ```

3. Test dependencies:
   ```bash
   # Test Proxmox connection
   curl -k https://172.32.0.11:8006/api2/json/version

   # Test Ollama connection
   curl http://172.32.2.71:11434/api/tags
   ```

### Authentication Errors

**Symptoms**: HTTP 401 errors when accessing Proxmox

**Solutions**:
1. Verify credentials in environment file
2. Check if user account exists in Proxmox
3. Ensure user has necessary permissions
4. Test manual login to Proxmox web interface

### Network Connectivity Issues

**Symptoms**: Connection timeouts or network errors

**Solutions**:
1. Check network configuration:
   ```bash
   # Docker
   docker network ls
   docker network inspect proxmox-mcp-server_proxmox-network

   # LXC
   pct config 200
   ```

2. Test connectivity:
   ```bash
   # From container to Proxmox
   ping 172.32.0.11

   # From container to Ollama
   ping 172.32.2.71
   ```

3. Check firewall rules on host and target systems

## Docker-Specific Issues

### Port Already in Use

**Error**: `port is already allocated`

**Solution**:
```bash
# Find process using port 8000
sudo lsof -i :8000

# Stop conflicting service or change port in docker-compose.yml
```

### Build Failures

**Error**: Docker build fails

**Solutions**:
1. Clear Docker cache:
   ```bash
   docker system prune -a
   ```

2. Check Dockerfile syntax
3. Verify requirements.txt dependencies

### Container Permissions

**Error**: Permission denied errors

**Solutions**:
1. Check volume mount permissions
2. Verify user mapping in container
3. Use correct file ownership

## LXC-Specific Issues

### Container Creation Fails

**Error**: LXC container creation fails

**Solutions**:
1. Check available storage:
   ```bash
   pvesm status
   ```

2. Verify template exists:
   ```bash
   pveam list local
   ```

3. Check network configuration:
   ```bash
   ip route show
   ```

### Service Permission Issues

**Error**: Service fails due to permissions

**Solutions**:
1. Check service file permissions:
   ```bash
   pct exec 200 -- ls -la /etc/systemd/system/proxmox-mcp-server.service
   ```

2. Verify application directory permissions:
   ```bash
   pct exec 200 -- ls -la /opt/proxmox-mcp-server/
   ```

## API Issues

### Slow Response Times

**Symptoms**: API calls take longer than expected

**Solutions**:
1. Monitor resource usage:
   ```bash
   # Docker
   docker stats

   # LXC
   pct exec 200 -- top
   ```

2. Check network latency:
   ```bash
   ping 172.32.0.11
   ping 172.32.2.71
   ```

3. Review application logs for bottlenecks

### Missing Dependencies

**Error**: Import errors or missing modules

**Solutions**:
1. Reinstall requirements:
   ```bash
   # Docker
   docker-compose build --no-cache

   # LXC
   pct exec 200 -- /opt/proxmox-mcp-server/venv/bin/pip install -r requirements.txt
   ```

## Diagnostic Commands

### Health Checks

```bash
# Test service health
curl http://localhost:8000/health  # Docker
curl http://172.32.0.200:8000/health  # LXC

# Test specific endpoints
curl http://localhost:8000/proxmox/nodes
curl http://localhost:8000/ollama/models
```

### Log Collection

```bash
# Docker logs
docker-compose logs --tail=100 proxmox-mcp-server

# LXC logs
pct exec 200 -- tail -f /opt/proxmox-mcp-server/logs/app.log
```

### System Information

```bash
# Docker system info
docker system info
docker-compose ps

# LXC system info
pct list
pct exec 200 -- systemctl status proxmox-mcp-server
```

## Getting Help

If you encounter issues not covered here:

1. Check the GitHub repository for similar issues
2. Review the configuration guide
3. Enable debug logging (`LOG_LEVEL=DEBUG`)
4. Collect relevant logs and system information
5. Create a detailed issue report

Include the following information in issue reports:
- Deployment method (Docker/LXC)
- Host OS and version
- Error messages and logs
- Configuration (sanitized)
- Steps to reproduce
