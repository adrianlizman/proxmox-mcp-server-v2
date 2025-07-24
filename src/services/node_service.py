
"""Node management service for Proxmox VE."""

import logging
from typing import Dict, List, Any, Optional
from ..proxmox_client import proxmox_client
from ..exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)


class NodeService:
    """Service for managing Proxmox nodes."""
    
    def __init__(self):
        self.client = proxmox_client
    
    async def list_nodes(self) -> List[Dict[str, Any]]:
        """List all cluster nodes."""
        try:
            nodes = await self.client.get_nodes()
            
            # Enhance node information
            enhanced_nodes = []
            for node in nodes:
                enhanced_node = {
                    'node': node.get('node'),
                    'status': node.get('status'),
                    'cpu': node.get('cpu', 0),
                    'maxcpu': node.get('maxcpu', 0),
                    'mem': node.get('mem', 0),
                    'maxmem': node.get('maxmem', 0),
                    'disk': node.get('disk', 0),
                    'maxdisk': node.get('maxdisk', 0),
                    'uptime': node.get('uptime', 0),
                    'level': node.get('level', ''),
                    'id': node.get('id'),
                    'type': node.get('type', 'node'),
                    'ssl_fingerprint': node.get('ssl_fingerprint')
                }
                enhanced_nodes.append(enhanced_node)
            
            return enhanced_nodes
            
        except Exception as e:
            logger.error(f"Failed to list nodes: {str(e)}")
            raise ProxmoxMCPException(f"Failed to list nodes: {str(e)}")
    
    async def get_node_status(self, node: str) -> Dict[str, Any]:
        """Get detailed node status."""
        try:
            status = await self.client.get_node_status(node)
            
            return {
                'node': node,
                'uptime': status.get('uptime', 0),
                'loadavg': status.get('loadavg', []),
                'cpu': status.get('cpu', 0),
                'cpuinfo': status.get('cpuinfo', {}),
                'memory': {
                    'total': status.get('memory', {}).get('total', 0),
                    'used': status.get('memory', {}).get('used', 0),
                    'free': status.get('memory', {}).get('free', 0)
                },
                'swap': {
                    'total': status.get('swap', {}).get('total', 0),
                    'used': status.get('swap', {}).get('used', 0),
                    'free': status.get('swap', {}).get('free', 0)
                },
                'rootfs': {
                    'total': status.get('rootfs', {}).get('total', 0),
                    'used': status.get('rootfs', {}).get('used', 0),
                    'avail': status.get('rootfs', {}).get('avail', 0)
                },
                'pveversion': status.get('pveversion'),
                'kversion': status.get('kversion'),
                'wait': status.get('wait', 0),
                'idle': status.get('idle', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get node {node} status: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node status: {str(e)}")
    
    async def get_node_version(self, node: str) -> Dict[str, Any]:
        """Get node version information."""
        try:
            version = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).version.get()
            )
            
            return version
            
        except Exception as e:
            logger.error(f"Failed to get node {node} version: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node version: {str(e)}")
    
    async def get_node_time(self, node: str) -> Dict[str, Any]:
        """Get node time information."""
        try:
            time_info = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).time.get()
            )
            
            return time_info
            
        except Exception as e:
            logger.error(f"Failed to get node {node} time: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node time: {str(e)}")
    
    async def set_node_time(self, node: str, timezone: str) -> Dict[str, Any]:
        """Set node timezone."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).time.put(timezone=timezone)
            )
            
            return {
                'node': node,
                'timezone': timezone,
                'action': 'set_timezone',
                'status': 'updated',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to set node {node} timezone: {str(e)}")
            raise ProxmoxMCPException(f"Failed to set node timezone: {str(e)}")
    
    async def get_node_dns(self, node: str) -> Dict[str, Any]:
        """Get node DNS configuration."""
        try:
            dns_config = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).dns.get()
            )
            
            return dns_config
            
        except Exception as e:
            logger.error(f"Failed to get node {node} DNS config: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node DNS config: {str(e)}")
    
    async def update_node_dns(self, node: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update node DNS configuration."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).dns.put(**config)
            )
            
            return {
                'node': node,
                'action': 'update_dns',
                'status': 'updated',
                'config': config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to update node {node} DNS config: {str(e)}")
            raise ProxmoxMCPException(f"Failed to update node DNS config: {str(e)}")
    
    async def get_node_hosts(self, node: str) -> Dict[str, Any]:
        """Get node hosts file content."""
        try:
            hosts = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).hosts.get()
            )
            
            return hosts
            
        except Exception as e:
            logger.error(f"Failed to get node {node} hosts: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node hosts: {str(e)}")
    
    async def update_node_hosts(self, node: str, data: str, digest: str = None) -> Dict[str, Any]:
        """Update node hosts file."""
        try:
            params = {'data': data}
            if digest:
                params['digest'] = digest
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).hosts.post(**params)
            )
            
            return {
                'node': node,
                'action': 'update_hosts',
                'status': 'updated',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to update node {node} hosts: {str(e)}")
            raise ProxmoxMCPException(f"Failed to update node hosts: {str(e)}")
    
    async def get_node_services(self, node: str) -> List[Dict[str, Any]]:
        """Get node services status."""
        try:
            services = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).services.get()
            )
            
            return services
            
        except Exception as e:
            logger.error(f"Failed to get node {node} services: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node services: {str(e)}")
    
    async def get_node_service_status(self, node: str, service: str) -> Dict[str, Any]:
        """Get specific service status."""
        try:
            status = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).services(service).state.get()
            )
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get service {service} status on node {node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get service status: {str(e)}")
    
    async def control_node_service(self, node: str, service: str, action: str) -> Dict[str, Any]:
        """Control node service (start, stop, restart, reload)."""
        try:
            valid_actions = ['start', 'stop', 'restart', 'reload']
            if action not in valid_actions:
                raise ProxmoxMCPException(f"Invalid action. Must be one of: {valid_actions}")
            
            result = await self.client._execute_with_retry(
                lambda: getattr(self.client.api.nodes(node).services(service), action).post()
            )
            
            return {
                'node': node,
                'service': service,
                'action': action,
                'status': 'executed',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to {action} service {service} on node {node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to {action} service: {str(e)}")
    
    async def get_node_tasks(self, node: str, limit: int = 50, running: bool = None) -> List[Dict[str, Any]]:
        """Get node tasks."""
        try:
            params = {'limit': limit}
            if running is not None:
                params['running'] = 1 if running else 0
            
            tasks = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).tasks.get(**params)
            )
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get node {node} tasks: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node tasks: {str(e)}")
    
    async def get_node_rrd_data(self, node: str, timeframe: str = 'hour') -> Dict[str, Any]:
        """Get node RRD (performance) data."""
        try:
            rrd_data = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).rrd.get(timeframe=timeframe)
            )
            
            return {
                'node': node,
                'timeframe': timeframe,
                'data': rrd_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get node {node} RRD data: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node RRD data: {str(e)}")
    
    async def get_node_subscription(self, node: str) -> Dict[str, Any]:
        """Get node subscription information."""
        try:
            subscription = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).subscription.get()
            )
            
            return subscription
            
        except Exception as e:
            logger.error(f"Failed to get node {node} subscription: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node subscription: {str(e)}")
    
    async def update_node_subscription(self, node: str, key: str) -> Dict[str, Any]:
        """Update node subscription key."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).subscription.post(key=key)
            )
            
            return {
                'node': node,
                'action': 'update_subscription',
                'status': 'updated',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to update node {node} subscription: {str(e)}")
            raise ProxmoxMCPException(f"Failed to update node subscription: {str(e)}")
    
    async def get_node_certificates(self, node: str) -> List[Dict[str, Any]]:
        """Get node SSL certificates."""
        try:
            certificates = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).certificates.info.get()
            )
            
            return certificates
            
        except Exception as e:
            logger.error(f"Failed to get node {node} certificates: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node certificates: {str(e)}")
    
    async def shutdown_node(self, node: str, force: bool = False) -> Dict[str, Any]:
        """Shutdown a node."""
        try:
            params = {}
            if force:
                params['forceStop'] = 1
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).status.post(command='shutdown', **params)
            )
            
            return {
                'node': node,
                'action': 'shutdown',
                'force': force,
                'status': 'initiated',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to shutdown node {node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to shutdown node: {str(e)}")
    
    async def reboot_node(self, node: str, force: bool = False) -> Dict[str, Any]:
        """Reboot a node."""
        try:
            params = {}
            if force:
                params['forceStop'] = 1
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).status.post(command='reboot', **params)
            )
            
            return {
                'node': node,
                'action': 'reboot',
                'force': force,
                'status': 'initiated',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to reboot node {node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to reboot node: {str(e)}")
    
    async def get_node_summary(self) -> Dict[str, Any]:
        """Get summary of all nodes."""
        try:
            nodes = await self.list_nodes()
            
            summary = {
                'total_nodes': len(nodes),
                'online_nodes': 0,
                'offline_nodes': 0,
                'total_cpu': 0,
                'used_cpu': 0,
                'total_memory': 0,
                'used_memory': 0,
                'total_storage': 0,
                'used_storage': 0,
                'nodes': []
            }
            
            for node in nodes:
                node_summary = {
                    'node': node['node'],
                    'status': node['status'],
                    'cpu_usage': (node['cpu'] / node['maxcpu'] * 100) if node['maxcpu'] > 0 else 0,
                    'memory_usage': (node['mem'] / node['maxmem'] * 100) if node['maxmem'] > 0 else 0,
                    'storage_usage': (node['disk'] / node['maxdisk'] * 100) if node['maxdisk'] > 0 else 0,
                    'uptime': node['uptime']
                }
                
                summary['nodes'].append(node_summary)
                
                if node['status'] == 'online':
                    summary['online_nodes'] += 1
                else:
                    summary['offline_nodes'] += 1
                
                summary['total_cpu'] += node['maxcpu']
                summary['used_cpu'] += node['cpu']
                summary['total_memory'] += node['maxmem']
                summary['used_memory'] += node['mem']
                summary['total_storage'] += node['maxdisk']
                summary['used_storage'] += node['disk']
            
            # Calculate overall usage percentages
            if summary['total_cpu'] > 0:
                summary['cpu_usage_percent'] = (summary['used_cpu'] / summary['total_cpu']) * 100
            else:
                summary['cpu_usage_percent'] = 0
            
            if summary['total_memory'] > 0:
                summary['memory_usage_percent'] = (summary['used_memory'] / summary['total_memory']) * 100
            else:
                summary['memory_usage_percent'] = 0
            
            if summary['total_storage'] > 0:
                summary['storage_usage_percent'] = (summary['used_storage'] / summary['total_storage']) * 100
            else:
                summary['storage_usage_percent'] = 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get node summary: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get node summary: {str(e)}")
