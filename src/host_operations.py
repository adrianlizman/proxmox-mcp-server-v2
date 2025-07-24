
"""Host operations module for VMware MCP Server."""

import logging
from typing import Dict, List, Any, Optional
from pyVmomi import vim
from .auth import auth_manager, RBACManager
from .exceptions import HostOperationError, AuthorizationError, ValidationError
from .utils import (
    async_retry, timeout_handler, audit_log, wait_for_task_async,
    get_host_by_name, get_all_hosts, format_host_info, validate_host_name
)

logger = logging.getLogger(__name__)


class HostOperations:
    """Handles all host-related operations."""
    
    def __init__(self):
        self.auth_manager = auth_manager
    
    @audit_log("list_hosts", "host")
    @timeout_handler()
    async def list_hosts(self, user_role: str = "viewer") -> List[Dict[str, Any]]:
        """List all hosts with their basic information."""
        if not RBACManager.check_permission(user_role, "host:monitor"):
            raise AuthorizationError("Insufficient permissions to list hosts")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise HostOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            hosts = get_all_hosts(content)
            
            host_list = []
            for host in hosts:
                host_info = format_host_info(host)
                host_list.append(host_info)
            
            logger.info(f"Listed {len(host_list)} hosts")
            return host_list
            
        except Exception as e:
            logger.error(f"Failed to list hosts: {str(e)}")
            raise HostOperationError(f"Failed to list hosts: {str(e)}")
    
    @audit_log("get_host_details", "host")
    @timeout_handler()
    async def get_host_details(self, host_name: str, user_role: str = "viewer") -> Dict[str, Any]:
        """Get detailed information about a specific host."""
        if not RBACManager.check_permission(user_role, "host:monitor"):
            raise AuthorizationError("Insufficient permissions to view host details")
        
        if not validate_host_name(host_name):
            raise ValidationError(f"Invalid host name: {host_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise HostOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            host = get_host_by_name(content, host_name)
            
            if not host:
                raise HostOperationError(f"Host '{host_name}' not found")
            
            # Get detailed host information
            host_details = format_host_info(host)
            
            # Add additional details
            if host.config:
                host_details.update({
                    "uuid": host.hardware.systemInfo.uuid if host.hardware and host.hardware.systemInfo else None,
                    "bios_version": host.hardware.biosInfo.biosVersion if host.hardware and host.hardware.biosInfo else None,
                    "boot_time": host.runtime.bootTime.isoformat() if host.runtime and host.runtime.bootTime else None,
                    "uptime_seconds": host.summary.quickStats.uptime if host.summary and host.summary.quickStats else 0,
                })
            
            # Add network information
            if host.config and host.config.network:
                host_details["network"] = {
                    "vnics": [
                        {
                            "device": vnic.device,
                            "portgroup": vnic.portgroup,
                            "dhcp": vnic.spec.ip.dhcp if vnic.spec and vnic.spec.ip else False,
                            "ip_address": vnic.spec.ip.ipAddress if vnic.spec and vnic.spec.ip else None,
                            "subnet_mask": vnic.spec.ip.subnetMask if vnic.spec and vnic.spec.ip else None,
                        }
                        for vnic in host.config.network.vnic
                    ] if host.config.network.vnic else [],
                    "pnics": [
                        {
                            "device": pnic.device,
                            "driver": pnic.driver,
                            "link_speed": pnic.linkSpeed.speedMb if pnic.linkSpeed else None,
                            "mac": pnic.mac,
                        }
                        for pnic in host.config.network.pnic
                    ] if host.config.network.pnic else []
                }
            
            # Add datastore information
            if host.datastore:
                host_details["datastores"] = [
                    {
                        "name": ds.name,
                        "type": ds.summary.type,
                        "capacity_gb": ds.summary.capacity // (1024**3),
                        "free_space_gb": ds.summary.freeSpace // (1024**3),
                        "accessible": ds.summary.accessible,
                    }
                    for ds in host.datastore
                ]
            
            # Add VM information
            if host.vm:
                host_details["vms"] = [
                    {
                        "name": vm.name,
                        "power_state": str(vm.runtime.powerState),
                        "cpu_usage": vm.summary.quickStats.overallCpuUsage if vm.summary and vm.summary.quickStats else 0,
                        "memory_usage_mb": vm.summary.quickStats.guestMemoryUsage if vm.summary and vm.summary.quickStats else 0,
                    }
                    for vm in host.vm
                ]
            
            logger.info(f"Retrieved details for host: {host_name}")
            return host_details
            
        except Exception as e:
            logger.error(f"Failed to get host details for {host_name}: {str(e)}")
            raise HostOperationError(f"Failed to get host details: {str(e)}")
    
    @audit_log("enter_maintenance_mode", "host")
    @timeout_handler(timeout_seconds=600)
    async def enter_maintenance_mode(self, host_name: str, evacuate_powered_off_vms: bool = True,
                                   timeout_seconds: int = 300, user_role: str = "admin") -> Dict[str, Any]:
        """Put a host into maintenance mode."""
        if not RBACManager.check_permission(user_role, "host:maintenance"):
            raise AuthorizationError("Insufficient permissions to enter maintenance mode")
        
        if not validate_host_name(host_name):
            raise ValidationError(f"Invalid host name: {host_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise HostOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            host = get_host_by_name(content, host_name)
            
            if not host:
                raise HostOperationError(f"Host '{host_name}' not found")
            
            if host.runtime.inMaintenanceMode:
                return {"status": "already_in_maintenance", "host_name": host_name}
            
            # Create maintenance mode spec
            maintenance_spec = vim.host.MaintenanceSpec()
            maintenance_spec.vsanMode = vim.vsan.host.DecommissionMode()
            maintenance_spec.vsanMode.objectAction = vim.vsan.host.DecommissionMode.ObjectAction.evacuateAllData
            
            task = host.EnterMaintenanceMode_Task(
                timeout=timeout_seconds,
                evacuatePoweredOffVms=evacuate_powered_off_vms,
                maintenanceSpec=maintenance_spec
            )
            
            result = await wait_for_task_async(task, timeout=600)
            
            logger.info(f"Successfully entered maintenance mode for host: {host_name}")
            return {
                "status": "maintenance_mode_entered",
                "host_name": host_name,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to enter maintenance mode for host {host_name}: {str(e)}")
            raise HostOperationError(f"Failed to enter maintenance mode: {str(e)}")
    
    @audit_log("exit_maintenance_mode", "host")
    @timeout_handler()
    async def exit_maintenance_mode(self, host_name: str, timeout_seconds: int = 300,
                                  user_role: str = "admin") -> Dict[str, Any]:
        """Exit maintenance mode for a host."""
        if not RBACManager.check_permission(user_role, "host:maintenance"):
            raise AuthorizationError("Insufficient permissions to exit maintenance mode")
        
        if not validate_host_name(host_name):
            raise ValidationError(f"Invalid host name: {host_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise HostOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            host = get_host_by_name(content, host_name)
            
            if not host:
                raise HostOperationError(f"Host '{host_name}' not found")
            
            if not host.runtime.inMaintenanceMode:
                return {"status": "not_in_maintenance", "host_name": host_name}
            
            task = host.ExitMaintenanceMode_Task(timeout=timeout_seconds)
            result = await wait_for_task_async(task)
            
            logger.info(f"Successfully exited maintenance mode for host: {host_name}")
            return {
                "status": "maintenance_mode_exited",
                "host_name": host_name,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to exit maintenance mode for host {host_name}: {str(e)}")
            raise HostOperationError(f"Failed to exit maintenance mode: {str(e)}")
    
    @audit_log("reboot_host", "host")
    @timeout_handler(timeout_seconds=600)
    async def reboot_host(self, host_name: str, force: bool = False, user_role: str = "admin") -> Dict[str, Any]:
        """Reboot a host."""
        if not RBACManager.check_permission(user_role, "host:maintenance"):
            raise AuthorizationError("Insufficient permissions to reboot host")
        
        if not validate_host_name(host_name):
            raise ValidationError(f"Invalid host name: {host_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise HostOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            host = get_host_by_name(content, host_name)
            
            if not host:
                raise HostOperationError(f"Host '{host_name}' not found")
            
            # Check if host has running VMs and not in maintenance mode
            if not force and not host.runtime.inMaintenanceMode:
                running_vms = [vm for vm in host.vm if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn]
                if running_vms:
                    raise HostOperationError(
                        f"Host has {len(running_vms)} running VMs. "
                        "Enter maintenance mode first or use force=True"
                    )
            
            task = host.RebootHost_Task(force=force)
            result = await wait_for_task_async(task, timeout=600)
            
            logger.info(f"Successfully initiated reboot for host: {host_name}")
            return {
                "status": "reboot_initiated",
                "host_name": host_name,
                "force": force,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to reboot host {host_name}: {str(e)}")
            raise HostOperationError(f"Failed to reboot host: {str(e)}")
    
    @audit_log("get_host_performance", "host")
    @timeout_handler()
    async def get_host_performance(self, host_name: str, user_role: str = "viewer") -> Dict[str, Any]:
        """Get performance metrics for a host."""
        if not RBACManager.check_permission(user_role, "host:monitor"):
            raise AuthorizationError("Insufficient permissions to view host performance")
        
        if not validate_host_name(host_name):
            raise ValidationError(f"Invalid host name: {host_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise HostOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            host = get_host_by_name(content, host_name)
            
            if not host:
                raise HostOperationError(f"Host '{host_name}' not found")
            
            # Get performance metrics
            perf_manager = content.perfManager
            
            # Get available metrics
            counter_info = {}
            for counter in perf_manager.perfCounter:
                counter_info[counter.key] = {
                    "name": f"{counter.groupInfo.key}.{counter.nameInfo.key}",
                    "unit": counter.unitInfo.key,
                    "description": counter.nameInfo.summary
                }
            
            # Get current performance data
            metrics = {}
            if host.summary and host.summary.quickStats:
                qs = host.summary.quickStats
                metrics.update({
                    "cpu_usage_mhz": qs.overallCpuUsage or 0,
                    "memory_usage_mb": qs.overallMemoryUsage or 0,
                    "uptime_seconds": qs.uptime or 0,
                    "distributed_cpu_fairness": qs.distributedCpuFairness or 0,
                    "distributed_memory_fairness": qs.distributedMemoryFairness or 0,
                })
            
            # Calculate utilization percentages
            if host.hardware:
                total_cpu_mhz = (host.hardware.cpuInfo.numCpuCores * 
                               host.hardware.cpuInfo.hz // 1000000) if host.hardware.cpuInfo else 0
                total_memory_mb = host.hardware.memorySize // (1024 * 1024) if host.hardware.memorySize else 0
                
                metrics.update({
                    "cpu_utilization_percent": (metrics.get("cpu_usage_mhz", 0) / total_cpu_mhz * 100) if total_cpu_mhz > 0 else 0,
                    "memory_utilization_percent": (metrics.get("memory_usage_mb", 0) / total_memory_mb * 100) if total_memory_mb > 0 else 0,
                    "total_cpu_mhz": total_cpu_mhz,
                    "total_memory_mb": total_memory_mb,
                })
            
            logger.info(f"Retrieved performance metrics for host: {host_name}")
            return {
                "host_name": host_name,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics for host {host_name}: {str(e)}")
            raise HostOperationError(f"Failed to get host performance: {str(e)}")
    
    @audit_log("add_host_to_cluster", "host")
    @timeout_handler(timeout_seconds=300)
    async def add_host_to_cluster(self, host_name: str, cluster_name: str, 
                                 username: str, password: str, user_role: str = "admin") -> Dict[str, Any]:
        """Add a host to a cluster."""
        if not RBACManager.check_permission(user_role, "host:add"):
            raise AuthorizationError("Insufficient permissions to add host")
        
        if not validate_host_name(host_name):
            raise ValidationError(f"Invalid host name: {host_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise HostOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            
            # Find the cluster
            cluster = None
            for datacenter in content.rootFolder.childEntity:
                if hasattr(datacenter, 'hostFolder'):
                    for entity in datacenter.hostFolder.childEntity:
                        if hasattr(entity, 'name') and entity.name == cluster_name:
                            cluster = entity
                            break
                    if cluster:
                        break
            
            if not cluster:
                raise HostOperationError(f"Cluster '{cluster_name}' not found")
            
            # Create host connect spec
            host_spec = vim.host.ConnectSpec()
            host_spec.hostName = host_name
            host_spec.userName = username
            host_spec.password = password
            host_spec.force = False
            host_spec.sslThumbprint = None  # Will be auto-accepted in lab environments
            
            # Add host to cluster
            task = cluster.AddHost_Task(spec=host_spec, asConnected=True)
            result = await wait_for_task_async(task, timeout=300)
            
            logger.info(f"Successfully added host {host_name} to cluster {cluster_name}")
            return {
                "status": "host_added",
                "host_name": host_name,
                "cluster_name": cluster_name,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to add host {host_name} to cluster {cluster_name}: {str(e)}")
            raise HostOperationError(f"Failed to add host to cluster: {str(e)}")


# Global host operations instance
host_ops = HostOperations()
