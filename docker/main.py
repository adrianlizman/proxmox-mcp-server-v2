#!/usr/bin/env python3
"""
Proxmox MCP Server - Main Application
A beginner-friendly MCP server for Proxmox integration
"""

import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from proxmoxer import ProxmoxAPI
import requests

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Proxmox MCP Server",
    description="MCP Server for Proxmox Virtual Environment",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
proxmox = None
ollama_host = os.getenv('OLLAMA_HOST', '172.32.2.71')
ollama_port = os.getenv('OLLAMA_PORT', '11434')

def initialize_proxmox():
    """Initialize Proxmox connection"""
    global proxmox
    try:
        proxmox = ProxmoxAPI(
            os.getenv('PROXMOX_HOST', '172.32.0.11'),
            user=os.getenv('PROXMOX_USER', 'root@pam'),
            password=os.getenv('PROXMOX_PASSWORD'),
            verify_ssl=os.getenv('PROXMOX_VERIFY_SSL', 'false').lower() == 'true'
        )
        logger.info("Proxmox connection initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Proxmox connection: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting Proxmox MCP Server...")
    if not initialize_proxmox():
        logger.warning("Proxmox connection failed, some features may not work")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Proxmox MCP Server is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "proxmox-mcp-server"}

@app.get("/proxmox/nodes")
async def get_nodes():
    """Get Proxmox nodes"""
    if not proxmox:
        raise HTTPException(status_code=500, detail="Proxmox connection not available")

    try:
        nodes = proxmox.nodes.get()
        return {"nodes": nodes}
    except Exception as e:
        logger.error(f"Error getting nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/proxmox/node/{node}/vms")
async def get_vms(node: str):
    """Get VMs for a specific node"""
    if not proxmox:
        raise HTTPException(status_code=500, detail="Proxmox connection not available")

    try:
        vms = proxmox.nodes(node).qemu.get()
        return {"vms": vms}
    except Exception as e:
        logger.error(f"Error getting VMs for node {node}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ollama/models")
async def get_ollama_models():
    """Get available Ollama models"""
    try:
        response = requests.get(f"http://{ollama_host}:{ollama_port}/api/tags")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting Ollama models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ollama/generate")
async def generate_ollama_response(request: dict):
    """Generate response using Ollama"""
    try:
        response = requests.post(
            f"http://{ollama_host}:{ollama_port}/api/generate",
            json=request
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error generating Ollama response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)

    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv('MCP_SERVER_PORT', 8000)),
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )
