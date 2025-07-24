
"""Network management service for Proxmox VE."""

import logging
from typing import Dict, List, Any, Optional
from ..proxmox_client import proxmox_client
from ..exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)


class NetworkService:
    """Service for managing Proxmox network operations."""
    
    def __init__(self):
        self.client = proxmox_client
    
    async def get_network_config(self, node: str) -> List[Dict[str, Any]]:
        """Get network configuration for a node."""
        try:
            network_config = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).network.get()
            )
            
            return network_config
            
        except Exception as e:
            logger.error(f"Failed to get network config for node {node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get network config: {str(e)}")
    
    async def get_network_interface(self, node: str, iface: str) -> Dict[str, Any]:
        """Get specific network interface configuration."""
        try:
            interface_config = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).network(iface).get()
            )
            
            return interface_config
            
        except Exception as e:
            logger.error(f"Failed to get interface {iface} config: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get interface config: {str(e)}")
    
    async def create_network_interface(self, node: str, iface: str, interface_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a network interface."""
        try:
            interface_config = {
                'iface': iface,
                'type': interface_type,
                **config
            }
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).network.post(**interface_config)
            )
            
            return {
                'node': node,
                'interface': iface,
                'type': interface_type,
                'action': 'create',
                'status': 'created',
                'config': interface_config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create interface {iface}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create interface: {str(e)}")
    
    async def update_network_interface(self, node: str, iface: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update network interface configuration."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).network(iface).put(**config)
            )
            
            return {
                'node': node,
                'interface': iface,
                'action': 'update',
                'status': 'updated',
                'config': config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to update interface {iface}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to update interface: {str(e)}")
    
    async def delete_network_interface(self, node: str, iface: str) -> Dict[str, Any]:
        """Delete a network interface."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).network(iface).delete()
            )
            
            return {
                'node': node,
                'interface': iface,
                'action': 'delete',
                'status': 'deleted',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete interface {iface}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to delete interface: {str(e)}")
    
    async def apply_network_config(self, node: str) -> Dict[str, Any]:
        """Apply pending network configuration changes."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).network.put()
            )
            
            return {
                'node': node,
                'action': 'apply_network_config',
                'status': 'applied',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to apply network config on node {node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to apply network config: {str(e)}")
    
    async def revert_network_config(self, node: str) -> Dict[str, Any]:
        """Revert pending network configuration changes."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).network.delete()
            )
            
            return {
                'node': node,
                'action': 'revert_network_config',
                'status': 'reverted',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to revert network config on node {node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to revert network config: {str(e)}")
    
    async def create_bridge(self, node: str, bridge_name: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a network bridge."""
        try:
            bridge_config = {
                'iface': bridge_name,
                'type': 'bridge',
                'autostart': config.get('autostart', 1) if config else 1,
                'bridge_ports': config.get('bridge_ports', '') if config else '',
                'bridge_stp': config.get('bridge_stp', 'off') if config else 'off',
                'bridge_fd': config.get('bridge_fd', 0) if config else 0,
                **(config or {})
            }
            
            return await self.create_network_interface(node, bridge_name, 'bridge', bridge_config)
            
        except Exception as e:
            logger.error(f"Failed to create bridge {bridge_name}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create bridge: {str(e)}")
    
    async def create_vlan(self, node: str, vlan_name: str, raw_device: str, vlan_id: int, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a VLAN interface."""
        try:
            vlan_config = {
                'iface': vlan_name,
                'type': 'vlan',
                'vlan-raw-device': raw_device,
                'vlan-id': vlan_id,
                'autostart': config.get('autostart', 1) if config else 1,
                **(config or {})
            }
            
            return await self.create_network_interface(node, vlan_name, 'vlan', vlan_config)
            
        except Exception as e:
            logger.error(f"Failed to create VLAN {vlan_name}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create VLAN: {str(e)}")
    
    async def create_bond(self, node: str, bond_name: str, slaves: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a network bond."""
        try:
            bond_config = {
                'iface': bond_name,
                'type': 'bond',
                'slaves': ' '.join(slaves),
                'bond_mode': config.get('bond_mode', 'balance-rr') if config else 'balance-rr',
                'bond_miimon': config.get('bond_miimon', 100) if config else 100,
                'autostart': config.get('autostart', 1) if config else 1,
                **(config or {})
            }
            
            return await self.create_network_interface(node, bond_name, 'bond', bond_config)
            
        except Exception as e:
            logger.error(f"Failed to create bond {bond_name}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create bond: {str(e)}")
    
    async def get_sdn_config(self) -> Dict[str, Any]:
        """Get Software Defined Network (SDN) configuration."""
        try:
            sdn_config = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.sdn.get()
            )
            
            return sdn_config
            
        except Exception as e:
            logger.error(f"Failed to get SDN config: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get SDN config: {str(e)}")
    
    async def get_sdn_zones(self) -> List[Dict[str, Any]]:
        """Get SDN zones."""
        try:
            zones = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.sdn.zones.get()
            )
            
            return zones
            
        except Exception as e:
            logger.error(f"Failed to get SDN zones: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get SDN zones: {str(e)}")
    
    async def get_sdn_vnets(self) -> List[Dict[str, Any]]:
        """Get SDN virtual networks."""
        try:
            vnets = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.sdn.vnets.get()
            )
            
            return vnets
            
        except Exception as e:
            logger.error(f"Failed to get SDN vnets: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get SDN vnets: {str(e)}")
    
    async def create_sdn_zone(self, zone_id: str, zone_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create an SDN zone."""
        try:
            zone_config = {
                'zone': zone_id,
                'type': zone_type,
                **config
            }
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.sdn.zones.post(**zone_config)
            )
            
            return {
                'zone': zone_id,
                'type': zone_type,
                'action': 'create_sdn_zone',
                'status': 'created',
                'config': zone_config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create SDN zone {zone_id}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create SDN zone: {str(e)}")
    
    async def create_sdn_vnet(self, vnet_id: str, zone: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create an SDN virtual network."""
        try:
            vnet_config = {
                'vnet': vnet_id,
                'zone': zone,
                **(config or {})
            }
            
            result = await self.client._execute_with_retry(
                lambda: self.client.api.cluster.sdn.vnets.post(**vnet_config)
            )
            
            return {
                'vnet': vnet_id,
                'zone': zone,
                'action': 'create_sdn_vnet',
                'status': 'created',
                'config': vnet_config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create SDN vnet {vnet_id}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create SDN vnet: {str(e)}")
    
    async def get_firewall_options(self, node: str) -> Dict[str, Any]:
        """Get node firewall options."""
        try:
            options = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).firewall.options.get()
            )
            
            return options
            
        except Exception as e:
            logger.error(f"Failed to get firewall options for node {node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get firewall options: {str(e)}")
    
    async def get_firewall_rules(self, node: str) -> List[Dict[str, Any]]:
        """Get node firewall rules."""
        try:
            rules = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).firewall.rules.get()
            )
            
            return rules
            
        except Exception as e:
            logger.error(f"Failed to get firewall rules for node {node}: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get firewall rules: {str(e)}")
    
    async def create_firewall_rule(self, node: str, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a firewall rule."""
        try:
            result = await self.client._execute_with_retry(
                lambda: self.client.api.nodes(node).firewall.rules.post(**rule_config)
            )
            
            return {
                'node': node,
                'action': 'create_firewall_rule',
                'status': 'created',
                'config': rule_config,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create firewall rule: {str(e)}")
            raise ProxmoxMCPException(f"Failed to create firewall rule: {str(e)}")
    
    async def get_network_summary(self) -> Dict[str, Any]:
        """Get network summary across all nodes."""
        try:
            nodes = await self.client.get_nodes()
            
            network_summary = {
                'total_interfaces': 0,
                'interfaces_by_type': {},
                'interfaces_by_node': {},
                'bridges': [],
                'vlans': [],
                'bonds': []
            }
            
            for node_info in nodes:
                node_name = node_info['node']
                network_summary['interfaces_by_node'][node_name] = []
                
                try:
                    interfaces = await self.get_network_config(node_name)
                    
                    for interface in interfaces:
                        iface_name = interface.get('iface')
                        iface_type = interface.get('type', 'unknown')
                        
                        interface_info = {
                            'interface': iface_name,
                            'type': iface_type,
                            'method': interface.get('method'),
                            'address': interface.get('address'),
                            'netmask': interface.get('netmask'),
                            'gateway': interface.get('gateway'),
                            'active': interface.get('active', 0),
                            'autostart': interface.get('autostart', 0)
                        }
                        
                        network_summary['interfaces_by_node'][node_name].append(interface_info)
                        network_summary['total_interfaces'] += 1
                        
                        # Count by type
                        if iface_type not in network_summary['interfaces_by_type']:
                            network_summary['interfaces_by_type'][iface_type] = 0
                        network_summary['interfaces_by_type'][iface_type] += 1
                        
                        # Categorize special interface types
                        if iface_type == 'bridge':
                            network_summary['bridges'].append({
                                'node': node_name,
                                'name': iface_name,
                                'ports': interface.get('bridge_ports', ''),
                                'stp': interface.get('bridge_stp', 'off')
                            })
                        elif iface_type == 'vlan':
                            network_summary['vlans'].append({
                                'node': node_name,
                                'name': iface_name,
                                'raw_device': interface.get('vlan-raw-device'),
                                'vlan_id': interface.get('vlan-id')
                            })
                        elif iface_type == 'bond':
                            network_summary['bonds'].append({
                                'node': node_name,
                                'name': iface_name,
                                'slaves': interface.get('slaves', ''),
                                'mode': interface.get('bond_mode')
                            })
                            
                except Exception as e:
                    logger.warning(f"Failed to get network config for node {node_name}: {str(e)}")
            
            return network_summary
            
        except Exception as e:
            logger.error(f"Failed to get network summary: {str(e)}")
            raise ProxmoxMCPException(f"Failed to get network summary: {str(e)}")
