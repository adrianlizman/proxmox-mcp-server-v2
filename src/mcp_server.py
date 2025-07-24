
"""MCP Server implementation for Proxmox VE management."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

from .auth import auth_manager
from .services import (
    VMService, LXCService, ClusterService, StorageService,
    NetworkService, NodeService, BackupService
)
from .exceptions import ProxmoxMCPException
from .config import settings

logger = logging.getLogger(__name__)


class ProxmoxMCPServer:
    """MCP Server for Proxmox VE management."""
    
    def __init__(self):
        self.server = Server("proxmox-mcp-server")
        self.vm_service = VMService()
        self.lxc_service = LXCService()
        self.cluster_service = ClusterService()
        self.storage_service = StorageService()
        self.network_service = NetworkService()
        self.node_service = NodeService()
        self.backup_service = BackupService()
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers."""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri="proxmox://cluster/status",
                    name="Cluster Status",
                    description="Current cluster status and node information",
                    mimeType="application/json"
                ),
                Resource(
                    uri="proxmox://cluster/resources",
                    name="Cluster Resources",
                    description="All cluster resources (VMs, containers, storage, etc.)",
                    mimeType="application/json"
                ),
                Resource(
                    uri="proxmox://nodes/summary",
                    name="Nodes Summary",
                    description="Summary of all cluster nodes",
                    mimeType="application/json"
                ),
                Resource(
                    uri="proxmox://vms/list",
                    name="Virtual Machines",
                    description="List of all virtual machines",
                    mimeType="application/json"
                ),
                Resource(
                    uri="proxmox://containers/list",
                    name="LXC Containers",
                    description="List of all LXC containers",
                    mimeType="application/json"
                ),
                Resource(
                    uri="proxmox://storage/summary",
                    name="Storage Summary",
                    description="Storage usage and configuration summary",
                    mimeType="application/json"
                ),
                Resource(
                    uri="proxmox://network/summary",
                    name="Network Summary",
                    description="Network configuration summary",
                    mimeType="application/json"
                ),
                Resource(
                    uri="proxmox://backups/summary",
                    name="Backup Summary",
                    description="Backup status and summary",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read a specific resource."""
            try:
                if uri == "proxmox://cluster/status":
                    status = await self.cluster_service.get_cluster_status()
                    return str(status)
                
                elif uri == "proxmox://cluster/resources":
                    resources = await self.cluster_service.get_cluster_resources()
                    return str(resources)
                
                elif uri == "proxmox://nodes/summary":
                    summary = await self.node_service.get_node_summary()
                    return str(summary)
                
                elif uri == "proxmox://vms/list":
                    vms = await self.vm_service.list_vms()
                    return str(vms)
                
                elif uri == "proxmox://containers/list":
                    containers = await self.lxc_service.list_containers()
                    return str(containers)
                
                elif uri == "proxmox://storage/summary":
                    summary = await self.storage_service.get_storage_summary()
                    return str(summary)
                
                elif uri == "proxmox://network/summary":
                    summary = await self.network_service.get_network_summary()
                    return str(summary)
                
                elif uri == "proxmox://backups/summary":
                    summary = await self.backup_service.get_backup_summary()
                    return str(summary)
                
                else:
                    raise ProxmoxMCPException(f"Unknown resource URI: {uri}")
                    
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {str(e)}")
                raise ProxmoxMCPException(f"Failed to read resource: {str(e)}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools."""
            return [
                # VM Management Tools
                Tool(
                    name="list_vms",
                    description="List all virtual machines with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Filter by node name"},
                            "status": {"type": "string", "description": "Filter by VM status"}
                        }
                    }
                ),
                Tool(
                    name="get_vm_details",
                    description="Get detailed information about a specific VM",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "VM ID"}
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="create_vm",
                    description="Create a new virtual machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "VM ID"},
                            "config": {"type": "object", "description": "VM configuration"}
                        },
                        "required": ["node", "vmid", "config"]
                    }
                ),
                Tool(
                    name="start_vm",
                    description="Start a virtual machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "VM ID"}
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="stop_vm",
                    description="Stop a virtual machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "VM ID"},
                            "force": {"type": "boolean", "description": "Force stop"}
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="delete_vm",
                    description="Delete a virtual machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "VM ID"},
                            "purge": {"type": "boolean", "description": "Purge VM data"}
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="clone_vm",
                    description="Clone a virtual machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "Source VM ID"},
                            "newid": {"type": "integer", "description": "New VM ID"},
                            "config": {"type": "object", "description": "Clone configuration"}
                        },
                        "required": ["node", "vmid", "newid"]
                    }
                ),
                Tool(
                    name="migrate_vm",
                    description="Migrate a virtual machine to another node",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Source node name"},
                            "vmid": {"type": "integer", "description": "VM ID"},
                            "target_node": {"type": "string", "description": "Target node name"},
                            "config": {"type": "object", "description": "Migration configuration"}
                        },
                        "required": ["node", "vmid", "target_node"]
                    }
                ),
                
                # LXC Container Management Tools
                Tool(
                    name="list_containers",
                    description="List all LXC containers with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Filter by node name"},
                            "status": {"type": "string", "description": "Filter by container status"}
                        }
                    }
                ),
                Tool(
                    name="get_container_details",
                    description="Get detailed information about a specific container",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "Container ID"}
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="create_container",
                    description="Create a new LXC container",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "Container ID"},
                            "config": {"type": "object", "description": "Container configuration"}
                        },
                        "required": ["node", "vmid", "config"]
                    }
                ),
                Tool(
                    name="start_container",
                    description="Start an LXC container",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "Container ID"}
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="stop_container",
                    description="Stop an LXC container",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "Container ID"},
                            "force": {"type": "boolean", "description": "Force stop"}
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="delete_container",
                    description="Delete an LXC container",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "Container ID"},
                            "purge": {"type": "boolean", "description": "Purge container data"}
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="clone_container",
                    description="Clone an LXC container",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "Source container ID"},
                            "newid": {"type": "integer", "description": "New container ID"},
                            "config": {"type": "object", "description": "Clone configuration"}
                        },
                        "required": ["node", "vmid", "newid"]
                    }
                ),
                
                # Cluster Management Tools
                Tool(
                    name="get_cluster_status",
                    description="Get cluster status and node information",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="get_cluster_resources",
                    description="Get all cluster resources",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "description": "Filter by resource type"}
                        }
                    }
                ),
                Tool(
                    name="get_ha_resources",
                    description="Get HA managed resources",
                    inputSchema={"type": "object", "properties": {}}
                ),
                
                # Storage Management Tools
                Tool(
                    name="list_storages",
                    description="List storage configurations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Filter by node name"}
                        }
                    }
                ),
                Tool(
                    name="get_storage_status",
                    description="Get storage status and usage",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "storage": {"type": "string", "description": "Storage name"}
                        },
                        "required": ["node", "storage"]
                    }
                ),
                Tool(
                    name="get_storage_content",
                    description="Get storage content (volumes, ISOs, templates)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "storage": {"type": "string", "description": "Storage name"},
                            "content_type": {"type": "string", "description": "Content type filter"}
                        },
                        "required": ["node", "storage"]
                    }
                ),
                
                # Network Management Tools
                Tool(
                    name="get_network_config",
                    description="Get network configuration for a node",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"}
                        },
                        "required": ["node"]
                    }
                ),
                Tool(
                    name="create_bridge",
                    description="Create a network bridge",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "bridge_name": {"type": "string", "description": "Bridge name"},
                            "config": {"type": "object", "description": "Bridge configuration"}
                        },
                        "required": ["node", "bridge_name"]
                    }
                ),
                
                # Node Management Tools
                Tool(
                    name="list_nodes",
                    description="List all cluster nodes",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="get_node_status",
                    description="Get detailed node status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"}
                        },
                        "required": ["node"]
                    }
                ),
                Tool(
                    name="get_node_services",
                    description="Get node services status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"}
                        },
                        "required": ["node"]
                    }
                ),
                
                # Backup Management Tools
                Tool(
                    name="create_backup",
                    description="Create a backup of VM or container",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "VM/Container ID"},
                            "config": {"type": "object", "description": "Backup configuration"}
                        },
                        "required": ["node", "vmid", "config"]
                    }
                ),
                Tool(
                    name="list_backups",
                    description="List available backups",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Filter by node name"},
                            "storage": {"type": "string", "description": "Filter by storage name"}
                        }
                    }
                ),
                Tool(
                    name="restore_backup",
                    description="Restore VM or container from backup",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "Node name"},
                            "vmid": {"type": "integer", "description": "VM/Container ID"},
                            "archive": {"type": "string", "description": "Backup archive path"},
                            "config": {"type": "object", "description": "Restore configuration"}
                        },
                        "required": ["node", "vmid", "archive"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                result = await self._execute_tool(name, arguments)
                return [TextContent(type="text", text=str(result))]
                
            except Exception as e:
                logger.error(f"Error executing tool {name}: {str(e)}")
                error_msg = f"Tool execution failed: {str(e)}"
                return [TextContent(type="text", text=error_msg)]
    
    async def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a specific tool."""
        
        # VM Management Tools
        if name == "list_vms":
            filters = {}
            if "status" in arguments:
                filters["status"] = arguments["status"]
            return await self.vm_service.list_vms(arguments.get("node"), filters)
        
        elif name == "get_vm_details":
            return await self.vm_service.get_vm_details(arguments["node"], arguments["vmid"])
        
        elif name == "create_vm":
            return await self.vm_service.create_vm(arguments["node"], arguments["vmid"], arguments["config"])
        
        elif name == "start_vm":
            return await self.vm_service.start_vm(arguments["node"], arguments["vmid"])
        
        elif name == "stop_vm":
            return await self.vm_service.stop_vm(arguments["node"], arguments["vmid"], arguments.get("force", False))
        
        elif name == "delete_vm":
            return await self.vm_service.delete_vm(arguments["node"], arguments["vmid"], arguments.get("purge", False))
        
        elif name == "clone_vm":
            return await self.vm_service.clone_vm(arguments["node"], arguments["vmid"], arguments["newid"], arguments.get("config"))
        
        elif name == "migrate_vm":
            return await self.vm_service.migrate_vm(arguments["node"], arguments["vmid"], arguments["target_node"], arguments.get("config"))
        
        # LXC Container Management Tools
        elif name == "list_containers":
            filters = {}
            if "status" in arguments:
                filters["status"] = arguments["status"]
            return await self.lxc_service.list_containers(arguments.get("node"), filters)
        
        elif name == "get_container_details":
            return await self.lxc_service.get_container_details(arguments["node"], arguments["vmid"])
        
        elif name == "create_container":
            return await self.lxc_service.create_container(arguments["node"], arguments["vmid"], arguments["config"])
        
        elif name == "start_container":
            return await self.lxc_service.start_container(arguments["node"], arguments["vmid"])
        
        elif name == "stop_container":
            return await self.lxc_service.stop_container(arguments["node"], arguments["vmid"], arguments.get("force", False))
        
        elif name == "delete_container":
            return await self.lxc_service.delete_container(arguments["node"], arguments["vmid"], arguments.get("purge", False))
        
        elif name == "clone_container":
            return await self.lxc_service.clone_container(arguments["node"], arguments["vmid"], arguments["newid"], arguments.get("config"))
        
        # Cluster Management Tools
        elif name == "get_cluster_status":
            return await self.cluster_service.get_cluster_status()
        
        elif name == "get_cluster_resources":
            return await self.cluster_service.get_cluster_resources(arguments.get("type"))
        
        elif name == "get_ha_resources":
            return await self.cluster_service.get_ha_resources()
        
        # Storage Management Tools
        elif name == "list_storages":
            return await self.storage_service.list_storages(arguments.get("node"))
        
        elif name == "get_storage_status":
            return await self.storage_service.get_storage_status(arguments["node"], arguments["storage"])
        
        elif name == "get_storage_content":
            return await self.storage_service.get_storage_content(arguments["node"], arguments["storage"], arguments.get("content_type"))
        
        # Network Management Tools
        elif name == "get_network_config":
            return await self.network_service.get_network_config(arguments["node"])
        
        elif name == "create_bridge":
            return await self.network_service.create_bridge(arguments["node"], arguments["bridge_name"], arguments.get("config"))
        
        # Node Management Tools
        elif name == "list_nodes":
            return await self.node_service.list_nodes()
        
        elif name == "get_node_status":
            return await self.node_service.get_node_status(arguments["node"])
        
        elif name == "get_node_services":
            return await self.node_service.get_node_services(arguments["node"])
        
        # Backup Management Tools
        elif name == "create_backup":
            return await self.backup_service.create_backup(arguments["node"], arguments["vmid"], arguments["config"])
        
        elif name == "list_backups":
            return await self.backup_service.list_backups(arguments.get("node"), arguments.get("storage"))
        
        elif name == "restore_backup":
            return await self.backup_service.restore_backup(arguments["node"], arguments["vmid"], arguments["archive"], arguments.get("config"))
        
        else:
            raise ProxmoxMCPException(f"Unknown tool: {name}")
    
    async def start(self):
        """Start the MCP server."""
        try:
            # Connect to Proxmox
            if not await auth_manager.connect():
                raise ProxmoxMCPException("Failed to connect to Proxmox VE")
            
            logger.info("Proxmox MCP Server started successfully")
            return self.server
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the MCP server."""
        try:
            await auth_manager.disconnect()
            logger.info("Proxmox MCP Server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping MCP server: {str(e)}")


# Global server instance
mcp_server = ProxmoxMCPServer()


async def main():
    """Main entry point for stdio server."""
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="proxmox-mcp-server",
                server_version="1.0.0",
                capabilities=mcp_server.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
