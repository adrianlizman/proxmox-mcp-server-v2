# Configuration Guide

This guide covers all configuration options for the Proxmox MCP Server.

## Environment Variables

### Proxmox Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXMOX_HOST` | `172.32.0.11` | Proxmox server hostname or IP |
| `PROXMOX_USER` | `root@pam` | Proxmox username and realm |
| `PROXMOX_PASSWORD` | - | Proxmox user password (required) |
| `PROXMOX_VERIFY_SSL` | `false` | Whether to verify SSL certificates |

### Ollama Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `172.32.2.71` | Ollama server hostname or IP |
| `OLLAMA_PORT` | `11434` | Ollama server port |

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_PORT` | `8000` | Port for the MCP server to listen on |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Network Configuration

The server is designed to work within the `172.32.0.0/22` network range:

- **Proxmox Server**: 172.32.0.11
- **Ollama Server**: 172.32.2.71
- **MCP Server (Docker)**: Uses host networking or mapped ports
- **MCP Server (LXC)**: 172.32.0.200

### Firewall Rules

Ensure these ports are accessible:

- **MCP Server**: Port 8000 (HTTP)
- **Proxmox**: Port 8006 (HTTPS)
- **Ollama**: Port 11434 (HTTP)

## Security Considerations

1. **Use strong passwords** for Proxmox accounts
2. **Enable SSL verification** in production (`PROXMOX_VERIFY_SSL=true`)
3. **Restrict network access** using firewall rules
4. **Use dedicated service accounts** instead of root when possible
5. **Regularly update** container images and dependencies

## Customization

### Adding Custom Endpoints

To add custom API endpoints, modify the main application file:

```python
@app.get("/custom/endpoint")
async def custom_endpoint():
    return {"message": "Custom functionality"}
```

### Modifying Logging

Adjust logging configuration in the application startup:

```python
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

## Performance Tuning

### Docker Deployment

- Adjust memory limits in `docker-compose.yml`
- Use volume mounts for persistent data
- Enable Docker BuildKit for faster builds

### LXC Deployment

- Allocate appropriate CPU cores and memory
- Enable nesting if running containers inside LXC
- Use local storage for better performance

## Troubleshooting Common Issues

### Connection Issues

1. **Cannot connect to Proxmox**
   - Verify `PROXMOX_HOST` and credentials
   - Check network connectivity
   - Ensure Proxmox API is enabled

2. **Cannot connect to Ollama**
   - Verify `OLLAMA_HOST` and `OLLAMA_PORT`
   - Check if Ollama service is running
   - Test with curl: `curl http://172.32.2.71:11434/api/tags`

3. **Service not accessible**
   - Check port bindings
   - Verify firewall rules
   - Ensure service is running

### Performance Issues

1. **Slow responses**
   - Increase container memory
   - Check network latency
   - Review application logs

2. **High resource usage**
   - Monitor with `docker stats` or `pct exec`
   - Adjust logging levels
   - Optimize API calls
