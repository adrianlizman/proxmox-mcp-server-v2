
"""LXC container management service for Proxmox VE."""

import logging
from typing import Dict, List, Any, Optional
from ..proxmox_client import proxmox_client
from ..exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)


class LXCService:
    """Service for managing Proxmox LXC containers."""
    
    def __init__(self):
        self.client = proxmox_client
    
    async def list_containers(self, node: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """List LXC containers with optional filtering."""
        try:
            containers = await self.client.get_containers(node)
            
            if filters:
                filtered_containers = []
                for container in containers:
                    match = True
                    for key, value in filters.items():
                        if key in container and container[key] != value:
                            match = False
                            break
                    if match:
                        filtered_containers.append(container)
                return filtered_containers
            
            return containers
            
        except Exception as e:
            logger.error(f"Failed to list containers: {str(e)}")
            raise ProxmoxMCPException(f"Failed to list containers: {str(e)}")
    
    async def get_container_details(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get detailed container information."""
        try:
            config = await self.client.get_container_config(node, vmid)
            
            # Get current status
            containers = await self.client.get_containers(node)
            container_status = next((ct for ct in containers if ct['vmid'] == vmid), {})
            
            return {
                'vmid': vmid,
                'node': node,
                'config': config,
                'status': container_status.get('status', 'unknown'),
                'name': config.get('hostname', f'ct-{vmid}'),
                'memory': config.get('memory', 0),
                'swap': config.get('swap', 0),
                'cores': config.get('cores', 1),
                'ostype': config.get('ostype', 'unmanaged'),
                'arch': config.get('arch', 'amd64'),
                'uptime': container_status.get('uptime', 0),
                'cpus': container_status.get('cpus', 0),
                'maxmem': container_status.get('maxmem', 0),
                'mem': container_status.get('mem', 0),
                'maxswap': container_status.get('maxswap', 0),
                'swap_used': container_status.get('swap', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get container {vmid} details: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get container details: {str(e)}")
    
    async def create_container(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new LXC container."""
        try:
            # Validate required parameters
            if not config.get('ostemplate'):
                raise ProxmoxMCPException("OS template is required")
            
            if not config.get('memory'):
                raise ProxmoxMCPException("Memory configuration is required")
            
            # Set default values
            container_config = {
                'ostemplate': config['ostemplate'],
                'memory': config['memory'],
                'swap': config.get('swap', config['memory']),
                'cores': config.get('cores', 1),
                'hostname': config.get('hostname', f'ct-{vmid}'),
                'storage': config.get('storage', 'local'),
                'net0': config.get('net0', 'name=eth0,bridge=vmbr0,ip=dhcp'),
                'ostype': config.get('ostype', 'unmanaged'),
                'arch': config.get('arch', 'amd64'),
                'unprivileged': config.get('unprivileged', 1),
                **config
            }
            
            # Remove None values
            container_config = {k: v for k, v in container_config.items() if v is not None}
            
            task_id = await self.client.create_container(node, vmid, **container_config)
            
            # Wait for task completion
            task_result = await self.client.wait_for_task(node, task_id)
            
            if task_result.get('exitstatus') != 'OK':
                raise ProxmoxMCPException(f"Container creation failed: {task_result.get('exitstatus')}")
            
            return {
                'vmid': vmid,
                'node': node,
                'task_id': task_id,
                'status': 'created',
                'config': container_config
            }
            
        except Exception as e:
            logger.error(f"Failed to create container {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create container: {str(e)}")
    
    async def start_container(self, node: str, vmid: int) -> Dict[str, Any]:
        """Start a container."""
        try:
            task_id = await self.client.start_container(node, vmid)
            
            return {
                'vmid': vmid,
                'node': node,
                'task_id': task_id,
                'action': 'start',
                'status': 'started'
            }
            
        except Exception as e:
            logger.error(f"Failed to start container {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to start container: {str(e)}")
    
    async def stop_container(self, node: str, vmid: int, force: bool = False) -> Dict[str, Any]:
        """Stop a container."""
        try:
            task_id = await self.client.stop_container(node, vmid, force)
            
            return {
                'vmid': vmid,
                'node': node,
                'task_id': task_id,
                'action': 'stop',
                'force': force,
                'status': 'stopped'
            }
            
        except Exception as e:
            logger.error(f"Failed to stop container {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to stop container: {str(e)}")
    
    async def delete_container(self, node: str, vmid: int, purge: bool = False) -> Dict[str, Any]:
        """Delete a container."""
        try:
            task_id = await self.client.delete_container(node, vmid, purge)
            
            # Wait for task completion
            task_result = await self.client.wait_for_task(node, task_id)
            
            if task_result.get('exitstatus') != 'OK':
                raise ProxmoxMCPException(f"Container deletion failed: {task_result.get('exitstatus')}")
            
            return {
                'vmid': vmid,
                'node': node,
                'task_id': task_id,
                'action': 'delete',
                'purge': purge,
                'status': 'deleted'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete container {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to delete container: {str(e)}")
    
    async def clone_container(self, node: str, vmid: int, newid: int, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Clone a container."""
        try:
            clone_config = config or {}
            
            # Set default clone parameters
            clone_params = {
                'hostname': clone_config.get('hostname', f'clone-of-ct-{vmid}'),
                'full': clone_config.get('full', 1),  # Full clone by default
                'target': clone_config.get('target', node),  # Clone to same node by default
                **clone_config
            }
            
            task_id = await self.client.clone_container(node, vmid, newid, **clone_params)
            
            # Wait for task completion
            task_result = await self.client.wait_for_task(node, task_id)
            
            if task_result.get('exitstatus') != 'OK':
                raise ProxmoxMCPException(f"Container cloning failed: {task_result.get('exitstatus')}")
            
            return {
                'source_vmid': vmid,
                'new_vmid': newid,
                'node': node,
                'target_node': clone_params.get('target', node),
                'task_id': task_id,
                'action': 'clone',
                'status': 'cloned',
                'config': clone_params
            }
            
        except Exception as e:
            logger.error(f"Failed to clone container {vmid} to {newid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to clone container: {str(e)}")
    
    async def update_container_config(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update container configuration."""
        try:
            # Get current config for digest
            current_config = await self.client.get_container_config(node, vmid)
            digest = current_config.get('digest')
            
            # Add digest to config for concurrency control
            update_config = {**config}
            if digest:
                update_config['digest'] = digest
            
            # Update configuration
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).lxc(vmid).config.put(**update_config)
            )
            
            return {
                'vmid': vmid,
                'node': node,
                'action': 'update_config',
                'status': 'updated',
                'config': config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to update container {vmid} config: {str(e)}")
            raise ProxmoxMCPException(f"Failed to update container config: {str(e)}")
    
    async def get_container_snapshots(self, node: str, vmid: int) -> List[Dict[str, Any]]:
        """Get container snapshots."""
        try:
            snapshots = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).lxc(vmid).snapshot.get()
            )
            
            return snapshots
            
        except Exception as e:
            logger.error(f"Failed to get container {vmid} snapshots: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get container snapshots: {str(e)}")
    
    async def create_container_snapshot(self, node: str, vmid: int, snapname: str, description: str = None) -> Dict[str, Any]:
        """Create container snapshot."""
        try:
            params = {'snapname': snapname}
            if description:
                params['description'] = description
            
            task_id = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).lxc(vmid).snapshot.post(**params)
            )
            
            return {
                'vmid': vmid,
                'node': node,
                'snapshot_name': snapname,
                'description': description,
                'task_id': task_id,
                'action': 'create_snapshot',
                'status': 'created'
            }
            
        except Exception as e:
            logger.error(f"Failed to create container {vmid} snapshot: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create container snapshot: {str(e)}")
    
    async def execute_command(self, node: str, vmid: int, command: str) -> Dict[str, Any]:
        """Execute command in container."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).lxc(vmid).status.exec.post(command=command)
            )
            
            return {
                'vmid': vmid,
                'node': node,
                'command': command,
                'result': result,
                'action': 'exec',
                'status': 'executed'
            }
            
        except Exception as e:
            logger.error(f"Failed to execute command in container {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to execute command: {str(e)}")
    
    async def get_container_templates(self, node: str, storage: str = None) -> List[Dict[str, Any]]:
        """Get available container templates."""
        try:
            if storage:
                templates = await self.client.get_storage_content(node, storage, 'vztmpl')
            else:
                # Get templates from all storages
                storages = await self.client.get_storages()
                all_templates = []
                
                for storage_info in storages:
                    storage_name = storage_info['storage']
                    content_types = storage_info.get('content', '').split(',')
                    
                    if 'vztmpl' in content_types:
                        try:
                            templates = await self.client.get_storage_content(node, storage_name, 'vztmpl')
                            for template in templates:
                                template['storage'] = storage_name
                            all_templates.extend(templates)
                        except Exception as e:
                            logger.warning(f"Failed to get templates from storage {storage_name}: {str(e)}")
                
                templates = all_templates
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get container templates: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get container templates: {str(e)}")
