
"""Cluster management service for Proxmox VE."""

import logging
from typing import Dict, List, Any, Optional
from ..proxmox_client import proxmox_client
from ..exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)


class ClusterService:
    """Service for managing Proxmox cluster operations."""
    
    def __init__(self):
        self.client = proxmox_client
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status and information."""
        try:
            status = await self.client.get_cluster_status()
            
            # Parse cluster information
            cluster_info = {}
            nodes = []
            
            for item in status:
                if item['type'] == 'cluster':
                    cluster_info = {
                        'name': item.get('name'),
                        'version': item.get('version'),
                        'quorate': item.get('quorate', 0),
                        'nodes': item.get('nodes', 0)
                    }
                elif item['type'] == 'node':
                    nodes.append({
                        'name': item.get('name'),
                        'id': item.get('id'),
                        'online': item.get('online', 0),
                        'local': item.get('local', 0),
                        'ip': item.get('ip'),
                        'level': item.get('level')
                    })
            
            return {
                'cluster': cluster_info,
                'nodes': nodes,
                'status': 'healthy' if cluster_info.get('quorate') else 'unhealthy'
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster status: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get cluster status: {str(e)}")
    
    async def get_cluster_resources(self, resource_type: str = None) -> List[Dict[str, Any]]:
        """Get cluster resources."""
        try:
            resources = await self.client.get_cluster_resources(resource_type)
            
            # Organize resources by type
            organized_resources = {
                'nodes': [],
                'vms': [],
                'containers': [],
                'storages': [],
                'pools': []
            }
            
            for resource in resources:
                res_type = resource.get('type')
                
                if res_type == 'node':
                    organized_resources['nodes'].append({
                        'node': resource.get('node'),
                        'status': resource.get('status'),
                        'cpu': resource.get('cpu', 0),
                        'maxcpu': resource.get('maxcpu', 0),
                        'mem': resource.get('mem', 0),
                        'maxmem': resource.get('maxmem', 0),
                        'disk': resource.get('disk', 0),
                        'maxdisk': resource.get('maxdisk', 0),
                        'uptime': resource.get('uptime', 0),
                        'level': resource.get('level', '')
                    })
                elif res_type == 'qemu':
                    organized_resources['vms'].append({
                        'vmid': resource.get('vmid'),
                        'name': resource.get('name'),
                        'node': resource.get('node'),
                        'status': resource.get('status'),
                        'cpu': resource.get('cpu', 0),
                        'maxcpu': resource.get('maxcpu', 0),
                        'mem': resource.get('mem', 0),
                        'maxmem': resource.get('maxmem', 0),
                        'disk': resource.get('disk', 0),
                        'maxdisk': resource.get('maxdisk', 0),
                        'uptime': resource.get('uptime', 0),
                        'template': resource.get('template', 0)
                    })
                elif res_type == 'lxc':
                    organized_resources['containers'].append({
                        'vmid': resource.get('vmid'),
                        'name': resource.get('name'),
                        'node': resource.get('node'),
                        'status': resource.get('status'),
                        'cpu': resource.get('cpu', 0),
                        'maxcpu': resource.get('maxcpu', 0),
                        'mem': resource.get('mem', 0),
                        'maxmem': resource.get('maxmem', 0),
                        'disk': resource.get('disk', 0),
                        'maxdisk': resource.get('maxdisk', 0),
                        'uptime': resource.get('uptime', 0),
                        'template': resource.get('template', 0)
                    })
                elif res_type == 'storage':
                    organized_resources['storages'].append({
                        'storage': resource.get('storage'),
                        'node': resource.get('node'),
                        'status': resource.get('status'),
                        'content': resource.get('content'),
                        'type': resource.get('plugintype'),
                        'used': resource.get('used', 0),
                        'avail': resource.get('avail', 0),
                        'total': resource.get('total', 0),
                        'used_fraction': resource.get('used_fraction', 0)
                    })
                elif res_type == 'pool':
                    organized_resources['pools'].append({
                        'poolid': resource.get('poolid'),
                        'comment': resource.get('comment', '')
                    })
            
            if resource_type:
                type_mapping = {
                    'node': 'nodes',
                    'vm': 'vms',
                    'qemu': 'vms',
                    'lxc': 'containers',
                    'storage': 'storages',
                    'pool': 'pools'
                }
                return organized_resources.get(type_mapping.get(resource_type, resource_type), [])
            
            return organized_resources
            
        except Exception as e:
            logger.error(f"Failed to get cluster resources: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get cluster resources: {str(e)}")
    
    async def get_cluster_config(self) -> Dict[str, Any]:
        """Get cluster configuration."""
        try:
            config = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.config.get()
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get cluster config: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get cluster config: {str(e)}")
    
    async def get_cluster_options(self) -> Dict[str, Any]:
        """Get cluster options."""
        try:
            options = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.options.get()
            )
            
            return options
            
        except Exception as e:
            logger.error(f"Failed to get cluster options: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get cluster options: {str(e)}")
    
    async def get_ha_resources(self) -> List[Dict[str, Any]]:
        """Get HA managed resources."""
        try:
            resources = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.ha.resources.get()
            )
            
            return resources
            
        except Exception as e:
            logger.error(f"Failed to get HA resources: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get HA resources: {str(e)}")
    
    async def get_ha_groups(self) -> List[Dict[str, Any]]:
        """Get HA groups."""
        try:
            groups = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.ha.groups.get()
            )
            
            return groups
            
        except Exception as e:
            logger.error(f"Failed to get HA groups: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get HA groups: {str(e)}")
    
    async def add_ha_resource(self, sid: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Add resource to HA management."""
        try:
            ha_config = {
                'sid': sid,
                **config
            }
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.ha.resources.post(**ha_config)
            )
            
            return {
                'sid': sid,
                'action': 'add_ha_resource',
                'status': 'added',
                'config': ha_config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to add HA resource {sid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to add HA resource: {str(e)}")
    
    async def remove_ha_resource(self, sid: str) -> Dict[str, Any]:
        """Remove resource from HA management."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.ha.resources(sid).delete()
            )
            
            return {
                'sid': sid,
                'action': 'remove_ha_resource',
                'status': 'removed',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to remove HA resource {sid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to remove HA resource: {str(e)}")
    
    async def get_cluster_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get cluster log entries."""
        try:
            log_entries = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.log.get(limit=limit)
            )
            
            return log_entries
            
        except Exception as e:
            logger.error(f"Failed to get cluster log: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get cluster log: {str(e)}")
    
    async def get_cluster_backup_schedule(self) -> List[Dict[str, Any]]:
        """Get cluster backup schedule."""
        try:
            backup_jobs = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.backup.get()
            )
            
            return backup_jobs
            
        except Exception as e:
            logger.error(f"Failed to get cluster backup schedule: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get cluster backup schedule: {str(e)}")
    
    async def get_cluster_firewall_rules(self) -> List[Dict[str, Any]]:
        """Get cluster firewall rules."""
        try:
            rules = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.firewall.rules.get()
            )
            
            return rules
            
        except Exception as e:
            logger.error(f"Failed to get cluster firewall rules: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get cluster firewall rules: {str(e)}")
    
    async def get_resource_pools(self) -> List[Dict[str, Any]]:
        """Get resource pools."""
        try:
            pools = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.pools.get()
            )
            
            return pools
            
        except Exception as e:
            logger.error(f"Failed to get resource pools: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get resource pools: {str(e)}")
    
    async def create_resource_pool(self, poolid: str, comment: str = None) -> Dict[str, Any]:
        """Create a resource pool."""
        try:
            pool_config = {'poolid': poolid}
            if comment:
                pool_config['comment'] = comment
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.pools.post(**pool_config)
            )
            
            return {
                'poolid': poolid,
                'comment': comment,
                'action': 'create_pool',
                'status': 'created',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create resource pool {poolid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create resource pool: {str(e)}")
    
    async def delete_resource_pool(self, poolid: str) -> Dict[str, Any]:
        """Delete a resource pool."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.pools(poolid).delete()
            )
            
            return {
                'poolid': poolid,
                'action': 'delete_pool',
                'status': 'deleted',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete resource pool {poolid}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to delete resource pool: {str(e)}")
