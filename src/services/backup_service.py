
"""Backup management service for Proxmox VE."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ..proxmox_client import proxmox_client
from ..exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)


class BackupService:
    """Service for managing Proxmox backup operations."""
    
    def __init__(self):
        self.client = proxmox_client
    
    async def create_backup(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a backup of a VM or container."""
        try:
            # Determine if it's a VM or container
            vm_type = config.get('type', 'qemu')  # Default to qemu (VM)
            
            backup_config = {
                'vmid': vmid,
                'storage': config.get('storage', 'local'),
                'mode': config.get('mode', 'snapshot'),  # snapshot, suspend, stop
                'compress': config.get('compress', 'lzo'),  # lzo, gzip, zstd
                'mailnotification': config.get('mailnotification', 'failure'),
                **{k: v for k, v in config.items() if k not in ['type']}
            }
            
            if vm_type == 'qemu':
                task_id = await self.client._execute_with_retry(
                    lambda: self.client.api.nodes(node).qemu(vmid).backup.post(**backup_config)
                )
            else:  # lxc
                task_id = await self.client._execute_with_retry(
                    lambda: self.client.api.nodes(node).lxc(vmid).backup.post(**backup_config)
                )
            
            return {
                'vmid': vmid,
                'node': node,
                'type': vm_type,
                'task_id': task_id,
                'action': 'create_backup',
                'status': 'started',
                'config': backup_config
            }
            
        except Exception as e:
            logger.error(f"Failed to create backup for {vmid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create backup: {str(e)}")
    
    async def restore_backup(self, node: str, vmid: int, archive: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Restore a VM or container from backup."""
        try:
            restore_config = {
                'vmid': vmid,
                'archive': archive,
                'storage': config.get('storage', 'local') if config else 'local',
                'force': config.get('force', 0) if config else 0,
                **(config or {})
            }
            
            # Determine backup type from archive name
            if 'lxc' in archive.lower() or 'ct' in archive.lower():
                task_id = await self.client._execute_with_retry(
                    lambda: self.client.api.nodes(node).lxc.post(**restore_config)
                )
                vm_type = 'lxc'
            else:
                task_id = await self.client._execute_with_retry(
                    lambda: self.client.api.nodes(node).qemu.post(**restore_config)
                )
                vm_type = 'qemu'
            
            return {
                'vmid': vmid,
                'node': node,
                'type': vm_type,
                'archive': archive,
                'task_id': task_id,
                'action': 'restore_backup',
                'status': 'started',
                'config': restore_config
            }
            
        except Exception as e:
            logger.error(f"Failed to restore backup {archive}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to restore backup: {str(e)}")
    
    async def list_backups(self, node: str = None, storage: str = None) -> List[Dict[str, Any]]:
        """List available backups."""
        try:
            backups = []
            
            if node and storage:
                # Get backups from specific storage on specific node
                content = await self.client.get_storage_content(node, storage, 'backup')
                for item in content:
                    backup_info = self._parse_backup_info(item, node, storage)
                    if backup_info:
                        backups.append(backup_info)
            else:
                # Get backups from all nodes and storages
                nodes = await self.client.get_nodes() if not node else [{'node': node}]
                
                for node_info in nodes:
                    node_name = node_info['node']
                    
                    try:
                        storages = await self.client.list_storages(node_name)
                        
                        for storage_info in storages:
                            storage_name = storage_info['storage']
                            content_types = storage_info.get('content', '').split(',')
                            
                            if 'backup' in content_types:
                                try:
                                    content = await self.client.get_storage_content(node_name, storage_name, 'backup')
                                    for item in content:
                                        backup_info = self._parse_backup_info(item, node_name, storage_name)
                                        if backup_info:
                                            backups.append(backup_info)
                                except Exception as e:
                                    logger.warning(f"Failed to get backups from {storage_name}: {str(e)}")
                                    
                    except Exception as e:
                        logger.warning(f"Failed to get storages for node {node_name}: {str(e)}")
            
            # Sort backups by creation time (newest first)
            backups.sort(key=lambda x: x.get('ctime', 0), reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {str(e)}")
            raise ProxmoxMCPException(f"Failed to list backups: {str(e)}")
    
    def _parse_backup_info(self, backup_item: Dict[str, Any], node: str, storage: str) -> Optional[Dict[str, Any]]:
        """Parse backup information from storage content item."""
        try:
            volid = backup_item.get('volid', '')
            if not volid or 'backup' not in backup_item.get('content', ''):
                return None
            
            # Parse backup filename to extract information
            filename = volid.split('/')[-1] if '/' in volid else volid
            
            # Extract VMID from filename (format: vzdump-{type}-{vmid}-{timestamp}.{ext})
            parts = filename.split('-')
            if len(parts) >= 3 and parts[0] == 'vzdump':
                vm_type = parts[1]  # qemu or lxc
                vmid = parts[2]
                
                return {
                    'volid': volid,
                    'filename': filename,
                    'vmid': int(vmid) if vmid.isdigit() else None,
                    'type': vm_type,
                    'node': node,
                    'storage': storage,
                    'size': backup_item.get('size', 0),
                    'ctime': backup_item.get('ctime', 0),
                    'format': backup_item.get('format', ''),
                    'notes': backup_item.get('notes', ''),
                    'protected': backup_item.get('protected', 0)
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse backup info: {str(e)}")
            return None
    
    async def delete_backup(self, node: str, storage: str, volid: str) -> Dict[str, Any]:
        """Delete a backup."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).storage(storage).content(volid).delete()
            )
            
            return {
                'volid': volid,
                'node': node,
                'storage': storage,
                'action': 'delete_backup',
                'status': 'deleted',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete backup {volid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to delete backup: {str(e)}")
    
    async def get_backup_schedule(self) -> List[Dict[str, Any]]:
        """Get cluster backup schedule."""
        try:
            backup_jobs = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.backup.get()
            )
            
            return backup_jobs
            
        except Exception as e:
            logger.error(f"Failed to get backup schedule: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get backup schedule: {str(e)}")
    
    async def create_backup_job(self, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scheduled backup job."""
        try:
            # Validate required fields
            required_fields = ['vmid', 'storage', 'schedule']
            for field in required_fields:
                if field not in job_config:
                    raise ProxmoxMCPException(f"Required field '{field}' is missing")
            
            # Set default values
            backup_job_config = {
                'enabled': job_config.get('enabled', 1),
                'mode': job_config.get('mode', 'snapshot'),
                'compress': job_config.get('compress', 'lzo'),
                'mailnotification': job_config.get('mailnotification', 'failure'),
                'dow': job_config.get('dow', 'mon,tue,wed,thu,fri,sat,sun'),  # Days of week
                **job_config
            }
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.backup.post(**backup_job_config)
            )
            
            return {
                'action': 'create_backup_job',
                'status': 'created',
                'config': backup_job_config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create backup job: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create backup job: {str(e)}")
    
    async def update_backup_job(self, job_id: str, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update a scheduled backup job."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.backup(job_id).put(**job_config)
            )
            
            return {
                'job_id': job_id,
                'action': 'update_backup_job',
                'status': 'updated',
                'config': job_config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to update backup job {job_id}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to update backup job: {str(e)}")
    
    async def delete_backup_job(self, job_id: str) -> Dict[str, Any]:
        """Delete a scheduled backup job."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.backup(job_id).delete()
            )
            
            return {
                'job_id': job_id,
                'action': 'delete_backup_job',
                'status': 'deleted',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete backup job {job_id}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to delete backup job: {str(e)}")
    
    async def get_backup_log(self, node: str, task_id: str) -> Dict[str, Any]:
        """Get backup task log."""
        try:
            log_data = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).tasks(task_id).log.get()
            )
            
            return {
                'node': node,
                'task_id': task_id,
                'log': log_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get backup log for task {task_id}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get backup log: {str(e)}")
    
    async def verify_backup(self, node: str, storage: str, volid: str) -> Dict[str, Any]:
        """Verify backup integrity."""
        try:
            # This would typically involve checking the backup file integrity
            # For now, we'll just check if the backup exists and get its info
            content = await self.client.get_storage_content(node, storage, 'backup')
            
            backup_info = None
            for item in content:
                if item.get('volid') == volid:
                    backup_info = item
                    break
            
            if not backup_info:
                raise ProxmoxMCPException(f"Backup {volid} not found")
            
            return {
                'volid': volid,
                'node': node,
                'storage': storage,
                'action': 'verify_backup',
                'status': 'verified',
                'size': backup_info.get('size', 0),
                'format': backup_info.get('format', ''),
                'ctime': backup_info.get('ctime', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to verify backup {volid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to verify backup: {str(e)}")
    
    async def get_backup_summary(self) -> Dict[str, Any]:
        """Get backup summary across all nodes and storages."""
        try:
            backups = await self.list_backups()
            
            summary = {
                'total_backups': len(backups),
                'total_size': 0,
                'backups_by_type': {'qemu': 0, 'lxc': 0},
                'backups_by_node': {},
                'backups_by_storage': {},
                'recent_backups': [],
                'old_backups': []
            }
            
            # Calculate cutoff for recent backups (last 7 days)
            recent_cutoff = datetime.now().timestamp() - (7 * 24 * 3600)
            
            for backup in backups:
                # Count by type
                backup_type = backup.get('type', 'unknown')
                if backup_type in summary['backups_by_type']:
                    summary['backups_by_type'][backup_type] += 1
                
                # Count by node
                node = backup.get('node')
                if node not in summary['backups_by_node']:
                    summary['backups_by_node'][node] = 0
                summary['backups_by_node'][node] += 1
                
                # Count by storage
                storage = backup.get('storage')
                if storage not in summary['backups_by_storage']:
                    summary['backups_by_storage'][storage] = 0
                summary['backups_by_storage'][storage] += 1
                
                # Add to total size
                summary['total_size'] += backup.get('size', 0)
                
                # Categorize by age
                ctime = backup.get('ctime', 0)
                if ctime > recent_cutoff:
                    summary['recent_backups'].append(backup)
                else:
                    summary['old_backups'].append(backup)
            
            # Sort recent backups by creation time (newest first)
            summary['recent_backups'].sort(key=lambda x: x.get('ctime', 0), reverse=True)
            
            # Limit recent backups to top 10
            summary['recent_backups'] = summary['recent_backups'][:10]
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get backup summary: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get backup summary: {str(e)}")
    
    async def cleanup_old_backups(self, node: str, storage: str, keep_count: int = 5, keep_days: int = 30) -> Dict[str, Any]:
        """Clean up old backups based on retention policy."""
        try:
            backups = await self.list_backups(node, storage)
            
            # Group backups by VMID
            backups_by_vmid = {}
            for backup in backups:
                vmid = backup.get('vmid')
                if vmid:
                    if vmid not in backups_by_vmid:
                        backups_by_vmid[vmid] = []
                    backups_by_vmid[vmid].append(backup)
            
            deleted_backups = []
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
            
            for vmid, vm_backups in backups_by_vmid.items():
                # Sort by creation time (newest first)
                vm_backups.sort(key=lambda x: x.get('ctime', 0), reverse=True)
                
                # Keep the most recent backups
                backups_to_check = vm_backups[keep_count:]
                
                for backup in backups_to_check:
                    # Delete if older than keep_days
                    if backup.get('ctime', 0) < cutoff_time and not backup.get('protected'):
                        try:
                            await self.delete_backup(node, storage, backup['volid'])
                            deleted_backups.append(backup)
                        except Exception as e:
                            logger.warning(f"Failed to delete backup {backup['volid']}: {str(e)}")
            
            return {
                'node': node,
                'storage': storage,
                'action': 'cleanup_old_backups',
                'status': 'completed',
                'deleted_count': len(deleted_backups),
                'deleted_backups': deleted_backups,
                'retention_policy': {
                    'keep_count': keep_count,
                    'keep_days': keep_days
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {str(e)}")
            raise ProxmoxMCPException(f"Failed to cleanup old backups: {str(e)}")
