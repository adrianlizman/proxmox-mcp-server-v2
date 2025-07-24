
"""Storage management service for Proxmox VE."""

import logging
from typing import Dict, List, Any, Optional
from ..proxmox_client import proxmox_client
from ..exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing Proxmox storage operations."""
    
    def __init__(self):
        self.client = proxmox_client
    
    async def list_storages(self, node: str = None) -> List[Dict[str, Any]]:
        """List storage configurations."""
        try:
            if node:
                storages = await self.client._execute_with_retry(
                    lambda: self.client.api.nodes(node).storage.get()
                )
            else:
                storages = await self.client.get_storages()
            
            return storages
            
        except Exception as e:
            logger.error(f"Failed to list storages: {str(e)}")
            raise ProxmoxMCPException(f"Failed to list storages: {str(e)}")
    
    async def get_storage_status(self, node: str, storage: str) -> Dict[str, Any]:
        """Get storage status and usage information."""
        try:
            status = await self.client.get_storage_status(node, storage)
            
            return {
                'storage': storage,
                'node': node,
                'type': status.get('type'),
                'content': status.get('content'),
                'total': status.get('total', 0),
                'used': status.get('used', 0),
                'avail': status.get('avail', 0),
                'used_fraction': status.get('used_fraction', 0),
                'enabled': status.get('enabled', 1),
                'active': status.get('active', 1)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage {storage} status: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get storage status: {str(e)}")
    
    async def get_storage_content(self, node: str, storage: str, content_type: str = None) -> List[Dict[str, Any]]:
        """Get storage content (volumes, ISOs, templates, etc.)."""
        try:
            content = await self.client.get_storage_content(node, storage, content_type)
            
            # Enhance content information
            enhanced_content = []
            for item in content:
                enhanced_item = {
                    'volid': item.get('volid'),
                    'content': item.get('content'),
                    'format': item.get('format'),
                    'size': item.get('size', 0),
                    'used': item.get('used', 0),
                    'vmid': item.get('vmid'),
                    'ctime': item.get('ctime'),
                    'notes': item.get('notes', ''),
                    'protected': item.get('protected', 0),
                    'storage': storage,
                    'node': node
                }
                enhanced_content.append(enhanced_item)
            
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Failed to get storage {storage} content: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get storage content: {str(e)}")
    
    async def create_storage(self, storage_id: str, storage_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new storage configuration."""
        try:
            storage_config = {
                'storage': storage_id,
                'type': storage_type,
                **config
            }
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.storage.post(**storage_config)
            )
            
            return {
                'storage': storage_id,
                'type': storage_type,
                'action': 'create',
                'status': 'created',
                'config': storage_config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create storage {storage_id}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create storage: {str(e)}")
    
    async def update_storage(self, storage_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update storage configuration."""
        try:
            # Get current config for digest
            current_config = await self.client._execute_with_retry(
                lambda: self.client.api.storage(storage_id).get()
            )
            digest = current_config.get('digest')
            
            # Add digest to config for concurrency control
            update_config = {**config}
            if digest:
                update_config['digest'] = digest
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.storage(storage_id).put(**update_config)
            )
            
            return {
                'storage': storage_id,
                'action': 'update',
                'status': 'updated',
                'config': config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to update storage {storage_id}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to update storage: {str(e)}")
    
    async def delete_storage(self, storage_id: str) -> Dict[str, Any]:
        """Delete storage configuration."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.storage(storage_id).delete()
            )
            
            return {
                'storage': storage_id,
                'action': 'delete',
                'status': 'deleted',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete storage {storage_id}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to delete storage: {str(e)}")
    
    async def upload_file(self, node: str, storage: str, filename: str, content_type: str, file_data: bytes) -> Dict[str, Any]:
        """Upload file to storage."""
        try:
            # This is a simplified version - actual implementation would handle file upload
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).storage(storage).upload.post(
                    content=content_type,
                    filename=filename
                )
            )
            
            return {
                'storage': storage,
                'node': node,
                'filename': filename,
                'content_type': content_type,
                'action': 'upload',
                'status': 'uploaded',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to upload file: {str(e)}")
    
    async def delete_volume(self, node: str, storage: str, volid: str) -> Dict[str, Any]:
        """Delete a volume from storage."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).storage(storage).content(volid).delete()
            )
            
            return {
                'volid': volid,
                'storage': storage,
                'node': node,
                'action': 'delete_volume',
                'status': 'deleted',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete volume {volid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to delete volume: {str(e)}")
    
    async def get_storage_rrd_data(self, node: str, storage: str, timeframe: str = 'hour') -> Dict[str, Any]:
        """Get storage RRD (performance) data."""
        try:
            rrd_data = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).storage(storage).rrd.get(timeframe=timeframe)
            )
            
            return {
                'storage': storage,
                'node': node,
                'timeframe': timeframe,
                'data': rrd_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage {storage} RRD data: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get storage RRD data: {str(e)}")
    
    async def scan_storage(self, node: str, storage_type: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan for available storage resources."""
        try:
            scan_config = {
                'type': storage_type,
                **config
            }
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).scan.get(**scan_config)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to scan storage: {str(e)}")
            raise ProxmoxMCPException(f"Failed to scan storage: {str(e)}")
    
    async def get_storage_types(self) -> List[Dict[str, Any]]:
        """Get available storage types and their capabilities."""
        storage_types = [
            {
                'type': 'dir',
                'name': 'Directory',
                'description': 'Local directory storage',
                'content': ['images', 'iso', 'vztmpl', 'backup', 'snippets'],
                'shared': False
            },
            {
                'type': 'nfs',
                'name': 'NFS',
                'description': 'Network File System',
                'content': ['images', 'iso', 'vztmpl', 'backup', 'snippets'],
                'shared': True
            },
            {
                'type': 'cifs',
                'name': 'CIFS/SMB',
                'description': 'Common Internet File System',
                'content': ['images', 'iso', 'vztmpl', 'backup', 'snippets'],
                'shared': True
            },
            {
                'type': 'lvm',
                'name': 'LVM',
                'description': 'Logical Volume Manager',
                'content': ['images'],
                'shared': False
            },
            {
                'type': 'lvmthin',
                'name': 'LVM-Thin',
                'description': 'LVM Thin Provisioning',
                'content': ['images'],
                'shared': False
            },
            {
                'type': 'zfs',
                'name': 'ZFS',
                'description': 'ZFS filesystem',
                'content': ['images'],
                'shared': False
            },
            {
                'type': 'cephfs',
                'name': 'CephFS',
                'description': 'Ceph Filesystem',
                'content': ['images', 'iso', 'vztmpl', 'backup', 'snippets'],
                'shared': True
            },
            {
                'type': 'rbd',
                'name': 'RBD',
                'description': 'Ceph RADOS Block Device',
                'content': ['images'],
                'shared': True
            },
            {
                'type': 'glusterfs',
                'name': 'GlusterFS',
                'description': 'GlusterFS distributed filesystem',
                'content': ['images', 'iso', 'vztmpl', 'backup', 'snippets'],
                'shared': True
            }
        ]
        
        return storage_types
    
    async def get_storage_summary(self) -> Dict[str, Any]:
        """Get storage summary across all nodes."""
        try:
            # Get all nodes
            nodes = await self.client.get_nodes()
            
            storage_summary = {
                'total_storages': 0,
                'total_space': 0,
                'used_space': 0,
                'available_space': 0,
                'storages_by_type': {},
                'storages_by_node': {}
            }
            
            for node_info in nodes:
                node_name = node_info['node']
                storage_summary['storages_by_node'][node_name] = []
                
                try:
                    storages = await self.list_storages(node_name)
                    
                    for storage in storages:
                        storage_name = storage['storage']
                        storage_type = storage.get('type', 'unknown')
                        
                        # Get storage status
                        try:
                            status = await self.get_storage_status(node_name, storage_name)
                            
                            storage_info = {
                                'storage': storage_name,
                                'type': storage_type,
                                'total': status.get('total', 0),
                                'used': status.get('used', 0),
                                'avail': status.get('avail', 0),
                                'enabled': status.get('enabled', 1)
                            }
                            
                            storage_summary['storages_by_node'][node_name].append(storage_info)
                            storage_summary['total_storages'] += 1
                            storage_summary['total_space'] += status.get('total', 0)
                            storage_summary['used_space'] += status.get('used', 0)
                            storage_summary['available_space'] += status.get('avail', 0)
                            
                            # Count by type
                            if storage_type not in storage_summary['storages_by_type']:
                                storage_summary['storages_by_type'][storage_type] = 0
                            storage_summary['storages_by_type'][storage_type] += 1
                            
                        except Exception as e:
                            logger.warning(f"Failed to get status for storage {storage_name}: {str(e)}")
                            
                except Exception as e:
                    logger.warning(f"Failed to get storages for node {node_name}: {str(e)}")
            
            # Calculate usage percentage
            if storage_summary['total_space'] > 0:
                storage_summary['usage_percentage'] = (storage_summary['used_space'] / storage_summary['total_space']) * 100
            else:
                storage_summary['usage_percentage'] = 0
            
            return storage_summary
            
        except Exception as e:
            logger.error(f"Failed to get storage summary: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get storage summary: {str(e)}")
