# Docker Deployment Guide

Complete guide for deploying the Proxmox MCP Server using Docker.

## System Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended)
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB available space
- **Network**: Access to Proxmox (172.32.0.11) and Ollama (172.32.2.71)

## Prerequisites

### Install Docker

**Ubuntu/Debian**:
```bash
# Update package index
sudo apt update

# Install required packages
sudo apt install apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io

# Add user to docker group
sudo usermod -aG docker $USER
```

### Install Docker Compose

```bash
# Download Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

## Deployment Steps

### 1. Download and Extract

```bash
# Download the project files
wget https://github.com/your-username/proxmox-mcp-server/archive/main.zip
unzip main.zip
cd proxmox-mcp-server-main/docker/
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.template .env

# Edit configuration
nano .env
```

**Required Configuration**:
```env
PROXMOX_HOST=172.32.0.11
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your_actual_password
PROXMOX_VERIFY_SSL=false

OLLAMA_HOST=172.32.2.71
OLLAMA_PORT=11434

MCP_SERVER_PORT=8000
LOG_LEVEL=INFO
```

### 3. Deploy Services

**Option A: Using Setup Script**
```bash
chmod +x setup-docker.sh
./setup-docker.sh
```

**Option B: Manual Deployment**
```bash
# Create directories
mkdir -p logs data

# Build and start services
docker-compose build
docker-compose up -d

# Check status
docker-compose ps
```

### 4. Verify Deployment

```bash
# Check service health
curl http://localhost:8000/health

# View logs
docker-compose logs -f proxmox-mcp-server

# Test API endpoints
curl http://localhost:8000/proxmox/nodes
curl http://localhost:8000/ollama/models
```

## Service Management

### Basic Commands

```bash
# Start services
docker-compose start

# Stop services
docker-compose stop

# Restart services
docker-compose restart

# View status
docker-compose ps

# View logs
docker-compose logs -f

# Remove services
docker-compose down
```

### Update Deployment

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build

# Clean up old images
docker image prune -f
```

## Configuration Options

### Environment Variables

All configuration is done through environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `PROXMOX_HOST` | Proxmox server IP/hostname | `172.32.0.11` |
| `PROXMOX_USER` | Proxmox username | `root@pam` |
| `PROXMOX_PASSWORD` | Proxmox password | Required |
| `PROXMOX_VERIFY_SSL` | Verify SSL certificates | `false` |
| `OLLAMA_HOST` | Ollama server IP/hostname | `172.32.2.71` |
| `OLLAMA_PORT` | Ollama server port | `11434` |
| `MCP_SERVER_PORT` | Server listening port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Docker Compose Customization

Edit `docker-compose.yml` to customize:

- **Memory limits**: Add `mem_limit: 2g`
- **CPU limits**: Add `cpus: '1.0'`
- **Port mapping**: Change `"8000:8000"` to use different host port
- **Volume mounts**: Add additional volume mappings

### Network Configuration

The default setup uses a bridge network. For custom networking:

```yaml
networks:
  proxmox-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
          gateway: 172.20.0.1
```

## Security Considerations

### Production Deployment

1. **Use SSL/TLS**:
   - Set `PROXMOX_VERIFY_SSL=true`
   - Use reverse proxy (nginx/traefik) with SSL

2. **Network Security**:
   - Restrict port access with firewall
   - Use VPN for remote access
   - Implement network segmentation

3. **Container Security**:
   - Use non-root user in container
   - Limit container capabilities
   - Keep images updated

### Reverse Proxy Setup (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring and Logging

### Log Management

```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs for specific service
docker-compose logs proxmox-mcp-server

# Limit log output
docker-compose logs --tail=100
```

### Health Monitoring

```bash
# Check container health
docker-compose ps

# Inspect container
docker inspect proxmox-mcp-server

# Container resource usage
docker stats proxmox-mcp-server
```

## Backup and Recovery

### Backup Configuration

```bash
# Backup configuration and data
tar -czf proxmox-mcp-backup.tar.gz .env logs/ data/

# Backup with timestamp
tar -czf "proxmox-mcp-backup-$(date +%Y%m%d-%H%M%S).tar.gz" .env logs/ data/
```

### Recovery Process

```bash
# Extract backup
tar -xzf proxmox-mcp-backup.tar.gz

# Restore services
docker-compose up -d
```

## Troubleshooting

See the main [Troubleshooting Guide](troubleshooting.md) for detailed solutions to common issues.

### Quick Diagnostics

```bash
# Check if Docker is running
systemctl status docker

# Test connectivity
ping 172.32.0.11
ping 172.32.2.71

# Check port availability
netstat -tulpn | grep :8000

# View container logs
docker logs proxmox-mcp-server
```
