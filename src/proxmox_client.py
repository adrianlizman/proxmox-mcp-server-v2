
"""Proxmox VE client wrapper using proxmoxer."""

import ssl
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from proxmoxer import ProxmoxAPI
from proxmoxer.core import ProxmoxHTTPSConnection
import requests
import urllib3
from .config import settings
from .exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)

# Disable SSL warnings for development (configure properly in production)
if not settings.proxmox_verify_ssl:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProxmoxClient:
    """Proxmox VE API client wrapper with connection management and retry logic."""
    
    def __init__(self):
        self.api: Optional[ProxmoxAPI] = None
        self.session: Optional[requests.Session] = None
        self._connection_cache: Dict[str, Any] = {}
        self._last_connection_check = None
        
    async def connect(self) -> bool:
        """Establish connection to Proxmox VE."""
        try:
            # Create session for connection pooling
            self.session = requests.Session()
            self.session.verify = settings.proxmox_verify_ssl
            
            # Configure SSL context if needed
            if not settings.proxmox_verify_ssl:
                self.session.verify = False
            
            # Create Proxmox API client
            self.api = ProxmoxAPI(
                host=settings.proxmox_host,
                user=settings.proxmox_username,
                password=settings.proxmox_password,
                port=settings.proxmox_port,
                verify_ssl=settings.proxmox_verify_ssl,
                timeout=settings.proxmox_timeout,
                session=self.session
            )
            
            # Test connection
            version_info = await self._execute_with_retry(
                lambda: self.api.version.get()
            )
            
            if not version_info:
                logger.error("Failed to retrieve Proxmox version information")
                return False
            
            logger.info(f"Successfully connected to Proxmox VE: {version_info.get('version', 'Unknown')}")
            self._last_connection_check = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox VE: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from Proxmox VE."""
        try:
            if self.session:
                self.session.close()
                self.session = None
                
            self.api = None
            self._connection_cache.clear()
            logger.info("Disconnected from Proxmox VE")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
    
    async def validate_connection(self) -> bool:
        """Validate the current connection."""
        try:
            if not self.api:
                return False
            
            # Check connection every 5 minutes
            now = datetime.now()
            if (self._last_connection_check and 
                (now - self._last_connection_check).seconds < 300):
                return True
            
            # Test connection with a simple API call
            version_info = await self._execute_with_retry(
                lambda: self.api.version.get()
            )
            
            if version_info:
                self._last_connection_check = now
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"Connection validation failed: {str(e)}")
            return False
    
    async def _execute_with_retry(self, operation, max_retries: int = 3, delay: float = 1.0):
        """Execute an operation with retry logic."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation()
                else:
                    # Run synchronous operation in thread pool
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, operation)
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Operation failed after {max_retries} attempts")
        
        raise ProxmoxMCPException(f"Operation failed after {max_retries} attempts: {str(last_exception)}")
    
    # Node operations
    async def get_nodes(self) -> List[Dict[str, Any]]:
        """Get list of cluster nodes."""
        return await self._execute_with_retry(
            lambda: self.api.nodes.get()
        )
    
    async def get_node_status(self, node: str) -> Dict[str, Any]:
        """Get node status information."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).status.get()
        )
    
    # VM operations
    async def get_vms(self, node: str = None) -> List[Dict[str, Any]]:
        """Get list of VMs."""
        if node:
            return await self._execute_with_retry(
                lambda: self.api.nodes(node).qemu.get()
            )
        else:
            # Get VMs from all nodes
            nodes = await self.get_nodes()
            all_vms = []
            for node_info in nodes:
                node_name = node_info['node']
                vms = await self._execute_with_retry(
                    lambda: self.api.nodes(node_name).qemu.get()
                )
                for vm in vms:
                    vm['node'] = node_name
                all_vms.extend(vms)
            return all_vms
    
    async def get_vm_config(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get VM configuration."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).qemu(vmid).config.get()
        )
    
    async def create_vm(self, node: str, vmid: int, **kwargs) -> str:
        """Create a new VM."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).qemu.create(vmid=vmid, **kwargs)
        )
    
    async def start_vm(self, node: str, vmid: int) -> str:
        """Start a VM."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).qemu(vmid).status.start.post()
        )
    
    async def stop_vm(self, node: str, vmid: int, force: bool = False) -> str:
        """Stop a VM."""
        if force:
            return await self._execute_with_retry(
                lambda: self.api.nodes(node).qemu(vmid).status.stop.post()
            )
        else:
            return await self._execute_with_retry(
                lambda: self.api.nodes(node).qemu(vmid).status.shutdown.post()
            )
    
    async def delete_vm(self, node: str, vmid: int, purge: bool = False) -> str:
        """Delete a VM."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).qemu(vmid).delete(purge=1 if purge else 0)
        )
    
    async def clone_vm(self, node: str, vmid: int, newid: int, **kwargs) -> str:
        """Clone a VM."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).qemu(vmid).clone.post(newid=newid, **kwargs)
        )
    
    async def migrate_vm(self, node: str, vmid: int, target: str, **kwargs) -> str:
        """Migrate a VM to another node."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).qemu(vmid).migrate.post(target=target, **kwargs)
        )
    
    # LXC Container operations
    async def get_containers(self, node: str = None) -> List[Dict[str, Any]]:
        """Get list of LXC containers."""
        if node:
            return await self._execute_with_retry(
                lambda: self.api.nodes(node).lxc.get()
            )
        else:
            # Get containers from all nodes
            nodes = await self.get_nodes()
            all_containers = []
            for node_info in nodes:
                node_name = node_info['node']
                containers = await self._execute_with_retry(
                    lambda: self.api.nodes(node_name).lxc.get()
                )
                for container in containers:
                    container['node'] = node_name
                all_containers.extend(containers)
            return all_containers
    
    async def get_container_config(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get container configuration."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).lxc(vmid).config.get()
        )
    
    async def create_container(self, node: str, vmid: int, **kwargs) -> str:
        """Create a new LXC container."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).lxc.create(vmid=vmid, **kwargs)
        )
    
    async def start_container(self, node: str, vmid: int) -> str:
        """Start a container."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).lxc(vmid).status.start.post()
        )
    
    async def stop_container(self, node: str, vmid: int, force: bool = False) -> str:
        """Stop a container."""
        if force:
            return await self._execute_with_retry(
                lambda: self.api.nodes(node).lxc(vmid).status.stop.post()
            )
        else:
            return await self._execute_with_retry(
                lambda: self.api.nodes(node).lxc(vmid).status.shutdown.post()
            )
    
    async def delete_container(self, node: str, vmid: int, purge: bool = False) -> str:
        """Delete a container."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).lxc(vmid).delete(purge=1 if purge else 0)
        )
    
    async def clone_container(self, node: str, vmid: int, newid: int, **kwargs) -> str:
        """Clone a container."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).lxc(vmid).clone.post(newid=newid, **kwargs)
        )
    
    # Storage operations
    async def get_storages(self) -> List[Dict[str, Any]]:
        """Get list of storage configurations."""
        return await self._execute_with_retry(
            lambda: self.api.storage.get()
        )
    
    async def get_storage_content(self, node: str, storage: str, content_type: str = None) -> List[Dict[str, Any]]:
        """Get storage content."""
        params = {}
        if content_type:
            params['content'] = content_type
        
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).storage(storage).content.get(**params)
        )
    
    async def get_storage_status(self, node: str, storage: str) -> Dict[str, Any]:
        """Get storage status."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).storage(storage).status.get()
        )
    
    # Cluster operations
    async def get_cluster_status(self) -> List[Dict[str, Any]]:
        """Get cluster status."""
        return await self._execute_with_retry(
            lambda: self.api.cluster.status.get()
        )
    
    async def get_cluster_resources(self, resource_type: str = None) -> List[Dict[str, Any]]:
        """Get cluster resources."""
        params = {}
        if resource_type:
            params['type'] = resource_type
        
        return await self._execute_with_retry(
            lambda: self.api.cluster.resources.get(**params)
        )
    
    # Task operations
    async def get_task_status(self, node: str, upid: str) -> Dict[str, Any]:
        """Get task status."""
        return await self._execute_with_retry(
            lambda: self.api.nodes(node).tasks(upid).status.get()
        )
    
    async def wait_for_task(self, node: str, upid: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for a task to complete."""
        start_time = datetime.now()
        
        while True:
            status = await self.get_task_status(node, upid)
            
            if status['status'] != 'running':
                return status
            
            # Check timeout
            if (datetime.now() - start_time).seconds > timeout:
                raise ProxmoxMCPException(f"Task {upid} timed out after {timeout} seconds")
            
            await asyncio.sleep(2)


# Global client instance
proxmox_client = ProxmoxClient()
