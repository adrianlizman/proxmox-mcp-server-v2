# Docker Deployment

Deploy the Proxmox MCP Server using Docker containers.

## Prerequisites

- Docker Engine installed
- Docker Compose installed
- Access to Proxmox server (172.32.0.11)
- Access to Ollama server (172.32.2.71)

## Quick Setup

1. **Run the setup script:**
   ```bash
   ./setup-docker.sh
   ```

2. **Edit the .env file with your credentials:**
   ```bash
   nano .env
   ```
   Update the `PROXMOX_PASSWORD` field.

3. **Start the service:**
   ```bash
   docker-compose up -d
   ```

## Manual Setup

1. **Copy environment template:**
   ```bash
   cp .env.template .env
   ```

2. **Edit configuration:**
   ```bash
   nano .env
   ```

3. **Build and start:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

## Service Management

- **View logs:** `docker-compose logs -f`
- **Stop service:** `docker-compose down`
- **Restart service:** `docker-compose restart`
- **Update service:** `docker-compose pull && docker-compose up -d`

## Accessing the Service

- **Main API:** http://localhost:8000
- **Health Check:** http://localhost:8000/health
- **API Documentation:** http://localhost:8000/docs

## Troubleshooting

1. **Check service status:**
   ```bash
   docker-compose ps
   ```

2. **View detailed logs:**
   ```bash
   docker-compose logs proxmox-mcp-server
   ```

3. **Test connectivity:**
   ```bash
   curl http://localhost:8000/health
   ```

For more troubleshooting, see the main documentation.
