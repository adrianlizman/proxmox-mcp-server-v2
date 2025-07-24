
"""VM management service for Proxmox VE."""

import logging
from typing import Dict, List, Any, Optional
from ..proxmox_client import proxmox_client
from ..exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)


class VMService:
    """Service for managing Proxmox VMs."""
    
    def __init__(self):
        self.client = proxmox_client
    
    async def list_vms(self, node: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """List VMs with optional filtering."""
        try:
            vms = await self.client.get_vms(node)
            
            if filters:
                filtered_vms = []
                for vm in vms:
                    match = True
                    for key, value in filters.items():
                        if key in vm and vm[key] != value:
                            match = False
                            break
                    if match:
                        filtered_vms.append(vm)
                return filtered_vms
            
            return vms
            
        except Exception as e:
            logger.error(f"Failed to list VMs: {str(e)}")
            raise ProxmoxMCPException(f"Failed to list VMs: {str(e)}")
    
    async def get_vm_details(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get detailed VM information."""
        try:
            config = await self.client.get_vm_config(node, vmid)
            
            # Get current status
            vms = await self.client.get_vms(node)
            vm_status = next((vm for vm in vms if vm['vmid'] == vmid), {})
            
            return {
                'vmid': vmid,
                'node': node,
                'config': config,
                'status': vm_status.get('status', 'unknown'),
                'name': config.get('name', f'vm-{vmid}'),
                'memory': config.get('memory', 0),
                'cores': config.get('cores', 0),
                'sockets': config.get('sockets', 1),
                'cpu': config.get('cpu', 'kvm64'),
                'ostype': config.get('ostype', 'other'),
                'boot': config.get('boot', ''),
                'uptime': vm_status.get('uptime', 0),
                'pid': vm_status.get('pid'),
                'cpus': vm_status.get('cpus', 0),
                'maxmem': vm_status.get('maxmem', 0),
                'mem': vm_status.get('mem', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get VM {vmid} details: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get VM details: {str(e)}")
    
    async def create_vm(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new VM."""
        try:
            # Validate required parameters
            if not config.get('memory'):
                raise ProxmoxMCPException("Memory configuration is required")
            
            # Set default values
            vm_config = {
                'memory': config['memory'],
                'cores': config.get('cores', 1),
                'sockets': config.get('sockets', 1),
                'cpu': config.get('cpu', 'kvm64'),
                'ostype': config.get('ostype', 'l26'),
                'boot': config.get('boot', 'cdn'),
                'net0': config.get('net0', 'virtio,bridge=vmbr0'),
                **config
            }
            
            # Remove None values
            vm_config = {k: v for k, v in vm_config.items() if v is not None}
            
            task_id = await self.client.create_vm(node, vmid, **vm_config)
            
            # Wait for task completion
            task_result = await self.client.wait_for_task(node, task_id)
            
            if task_result.get('exitstatus') != 'OK':
                raise ProxmoxMCPException(f"VM creation failed: {task_result.get('exitstatus')}")
            
            return {
                'vmid': vmid,
                'node': node,
                'task_id': task_id,
                'status': 'created',
                'config': vm_config
            }
            
        except Exception as e:
            logger.error(f"Failed to create VM {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create VM: {str(e)}")
    
    async def start_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """Start a VM."""
        try:
            task_id = await self.client.start_vm(node, vmid)
            
            return {
                'vmid': vmid,
                'node': node,
                'task_id': task_id,
                'action': 'start',
                'status': 'started'
            }
            
        except Exception as e:
            logger.error(f"Failed to start VM {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to start VM: {str(e)}")
    
    async def stop_vm(self, node: str, vmid: int, force: bool = False) -> Dict[str, Any]:
        """Stop a VM."""
        try:
            task_id = await self.client.stop_vm(node, vmid, force)
            
            return {
                'vmid': vmid,
                'node': node,
                'task_id': task_id,
                'action': 'stop',
                'force': force,
                'status': 'stopped'
            }
            
        except Exception as e:
            logger.error(f"Failed to stop VM {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to stop VM: {str(e)}")
    
    async def delete_vm(self, node: str, vmid: int, purge: bool = False) -> Dict[str, Any]:
        """Delete a VM."""
        try:
            task_id = await self.client.delete_vm(node, vmid, purge)
            
            # Wait for task completion
            task_result = await self.client.wait_for_task(node, task_id)
            
            if task_result.get('exitstatus') != 'OK':
                raise ProxmoxMCPException(f"VM deletion failed: {task_result.get('exitstatus')}")
            
            return {
                'vmid': vmid,
                'node': node,
                'task_id': task_id,
                'action': 'delete',
                'purge': purge,
                'status': 'deleted'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete VM {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to delete VM: {str(e)}")
    
    async def clone_vm(self, node: str, vmid: int, newid: int, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Clone a VM."""
        try:
            clone_config = config or {}
            
            # Set default clone parameters
            clone_params = {
                'name': clone_config.get('name', f'clone-of-{vmid}'),
                'full': clone_config.get('full', 1),  # Full clone by default
                'target': clone_config.get('target', node),  # Clone to same node by default
                **clone_config
            }
            
            task_id = await self.client.clone_vm(node, vmid, newid, **clone_params)
            
            # Wait for task completion
            task_result = await self.client.wait_for_task(node, task_id)
            
            if task_result.get('exitstatus') != 'OK':
                raise ProxmoxMCPException(f"VM cloning failed: {task_result.get('exitstatus')}")
            
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
            logger.error(f"Failed to clone VM {vmid} to {newid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to clone VM: {str(e)}")
    
    async def migrate_vm(self, node: str, vmid: int, target_node: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Migrate a VM to another node."""
        try:
            migrate_config = config or {}
            
            # Set default migration parameters
            migrate_params = {
                'online': migrate_config.get('online', 1),  # Online migration by default
                'with-local-disks': migrate_config.get('with_local_disks', 0),
                **migrate_config
            }
            
            task_id = await self.client.migrate_vm(node, vmid, target_node, **migrate_params)
            
            return {
                'vmid': vmid,
                'source_node': node,
                'target_node': target_node,
                'task_id': task_id,
                'action': 'migrate',
                'online': migrate_params.get('online', 1),
                'status': 'migrating'
            }
            
        except Exception as e:
            logger.error(f"Failed to migrate VM {vmid} from {node} to {target_node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to migrate VM: {str(e)}")
    
    async def update_vm_config(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update VM configuration."""
        try:
            # Get current config for digest
            current_config = await self.client.get_vm_config(node, vmid)
            digest = current_config.get('digest')
            
            # Add digest to config for concurrency control
            update_config = {**config}
            if digest:
                update_config['digest'] = digest
            
            # Update configuration
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).qemu(vmid).config.put(**update_config)
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
            logger.error(f"Failed to update VM {vmid} config: {str(e)}")
            raise ProxmoxMCPException(f"Failed to update VM config: {str(e)}")
    
    async def get_vm_snapshots(self, node: str, vmid: int) -> List[Dict[str, Any]]:
        """Get VM snapshots."""
        try:
            snapshots = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).qemu(vmid).snapshot.get()
            )
            
            return snapshots
            
        except Exception as e:
            logger.error(f"Failed to get VM {vmid} snapshots: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get VM snapshots: {str(e)}")
    
    async def create_vm_snapshot(self, node: str, vmid: int, snapname: str, description: str = None) -> Dict[str, Any]:
        """Create VM snapshot."""
        try:
            params = {'snapname': snapname}
            if description:
                params['description'] = description
            
            task_id = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).qemu(vmid).snapshot.post(**params)
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
            logger.error(f"Failed to create VM {vmid} snapshot: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create VM snapshot: {str(e)}")
