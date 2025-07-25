# Proxmox MCP Server

A beginner-friendly Model Context Protocol (MCP) server for Proxmox Virtual Environment integration with AI workflows.

LXC model full tested 
Docker is not tested yet

<img width="1129" height="794" alt="image" src="https://github.com/user-attachments/assets/bf1fb08a-e11a-4187-8790-8dc0dcb1d7d3" />

## Features

- **Core Proxmox Operations**: VM/CT management, resource monitoring, snapshot operations
- **AI Integration**: Direct integration with Ollama for intelligent infrastructure management
- **Workflow Automation**: N8N integration for automated workflows
- **Multiple Deployment Options**: Docker containers and LXC containers
- **Beginner-Friendly**: Comprehensive documentation and setup scripts

## Quick Start

Choose your preferred deployment method:

### Docker Deployment
```bash
cd docker
./setup-docker.sh
```

### LXC Deployment
```bash
cd lxc
./setup-lxc.sh
```

## Network Requirements

- **Proxmox Server**: 172.32.0.11
- **Ollama Server**: 172.32.2.71
- **Local Network**: 172.32.0.0/22

## Documentation

- [Docker Deployment Guide](docs/docker-deployment.md)
- [LXC Deployment Guide](docs/lxc-deployment.md)
- [Configuration Guide](docs/configuration.md)
- [N8N Integration](docs/n8n-integration.md)
- [Troubleshooting](docs/troubleshooting.md)

## Project Structure

```
proxmox-mcp-server/
├── docker/                 # Docker deployment files
├── lxc/                    # LXC deployment files
├── docs/                   # Documentation
├── scripts/                # Setup and utility scripts
├── examples/               # Example configurations and workflows
├── testing/                # Testing scripts and tools
└── configs/                # Configuration templates
```

## Support

For issues and feature requests, please check the documentation first, then create an issue on GitHub.

## License

MIT License - see LICENSE file for details.
