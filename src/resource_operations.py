
"""Resource management operations module for VMware MCP Server."""

import logging
from typing import Dict, List, Any, Optional
from pyVmomi import vim
from .auth import auth_manager, RBACManager
from .exceptions import ResourceOperationError, AuthorizationError, ValidationError
from .utils import (
    async_retry, timeout_handler, audit_log, wait_for_task_async,
    get_vm_by_name, get_all_vms, get_all_hosts, validate_vm_name, bytes_to_human_readable
)

logger = logging.getLogger(__name__)


class ResourceOperations:
    """Handles all resource management operations."""
    
    def __init__(self):
        self.auth_manager = auth_manager
    
    @audit_log("get_cluster_resources", "resource")
    @timeout_handler()
    async def get_cluster_resources(self, user_role: str = "viewer") -> Dict[str, Any]:
        """Get cluster resource utilization summary."""
        if not RBACManager.check_permission(user_role, "resource:monitor"):
            raise AuthorizationError("Insufficient permissions to view cluster resources")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise ResourceOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            
            # Get all hosts and VMs
            hosts = get_all_hosts(content)
            vms = get_all_vms(content)
            
            # Calculate totals
            total_cpu_cores = 0
            total_cpu_mhz = 0
            total_memory_mb = 0
            used_cpu_mhz = 0
            used_memory_mb = 0
            
            host_count = len(hosts)
            vm_count = len(vms)
            powered_on_vms = 0
            
            # Process hosts
            for host in hosts:
                if host.hardware and host.hardware.cpuInfo:
                    total_cpu_cores += host.hardware.cpuInfo.numCpuCores
                    total_cpu_mhz += (host.hardware.cpuInfo.numCpuCores * 
                                    host.hardware.cpuInfo.hz // 1000000)
                
                if host.hardware and host.hardware.memorySize:
                    total_memory_mb += host.hardware.memorySize // (1024 * 1024)
                
                if host.summary and host.summary.quickStats:
                    used_cpu_mhz += host.summary.quickStats.overallCpuUsage or 0
                    used_memory_mb += host.summary.quickStats.overallMemoryUsage or 0
            
            # Process VMs
            for vm in vms:
                if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                    powered_on_vms += 1
            
            # Calculate utilization percentages
            cpu_utilization = (used_cpu_mhz / total_cpu_mhz * 100) if total_cpu_mhz > 0 else 0
            memory_utilization = (used_memory_mb / total_memory_mb * 100) if total_memory_mb > 0 else 0
            
            logger.info("Retrieved cluster resource summary")
            return {
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                "cluster_summary": {
                    "hosts": {
                        "total": host_count,
                        "connected": len([h for h in hosts if h.runtime.connectionState == vim.HostSystem.ConnectionState.connected])
                    },
                    "vms": {
                        "total": vm_count,
                        "powered_on": powered_on_vms,
                        "powered_off": vm_count - powered_on_vms
                    }
                },
                "resources": {
                    "cpu": {
                        "total_cores": total_cpu_cores,
                        "total_mhz": total_cpu_mhz,
                        "used_mhz": used_cpu_mhz,
                        "utilization_percent": round(cpu_utilization, 2)
                    },
                    "memory": {
                        "total_mb": total_memory_mb,
                        "total_gb": round(total_memory_mb / 1024, 2),
                        "used_mb": used_memory_mb,
                        "used_gb": round(used_memory_mb / 1024, 2),
                        "utilization_percent": round(memory_utilization, 2)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster resources: {str(e)}")
            raise ResourceOperationError(f"Failed to get cluster resources: {str(e)}")
    
    @audit_log("modify_vm_resources", "resource")
    @timeout_handler()
    async def modify_vm_resources(self, vm_name: str, cpu_count: int = None, 
                                memory_mb: int = None, user_role: str = "admin") -> Dict[str, Any]:
        """Modify VM CPU and memory resources."""
        if not RBACManager.check_permission(user_role, "resource:allocate"):
            raise AuthorizationError("Insufficient permissions to modify VM resources")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        if cpu_count is not None and (cpu_count < 1 or cpu_count > 128):
            raise ValidationError("CPU count must be between 1 and 128")
        
        if memory_mb is not None and (memory_mb < 4 or memory_mb > 1048576):
            raise ValidationError("Memory must be between 4 MB and 1 TB")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise ResourceOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise ResourceOperationError(f"VM '{vm_name}' not found")
            
            # Create VM config spec
            config_spec = vim.vm.ConfigSpec()
            changes_made = []
            
            if cpu_count is not None:
                config_spec.numCPUs = cpu_count
                changes_made.append(f"CPU count: {cpu_count}")
            
            if memory_mb is not None:
                config_spec.memoryMB = memory_mb
                changes_made.append(f"Memory: {memory_mb} MB")
            
            if not changes_made:
                return {
                    "status": "no_changes",
                    "vm_name": vm_name,
                    "message": "No resource changes specified"
                }
            
            # Apply configuration
            task = vm.ReconfigVM_Task(spec=config_spec)
            result = await wait_for_task_async(task)
            
            logger.info(f"Successfully modified resources for VM '{vm_name}': {', '.join(changes_made)}")
            return {
                "status": "modified",
                "vm_name": vm_name,
                "changes": changes_made,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to modify resources for VM {vm_name}: {str(e)}")
            raise ResourceOperationError(f"Failed to modify VM resources: {str(e)}")
    
    @audit_log("get_vm_resource_usage", "resource")
    @timeout_handler()
    async def get_vm_resource_usage(self, vm_name: str, user_role: str = "viewer") -> Dict[str, Any]:
        """Get detailed resource usage for a specific VM."""
        if not RBACManager.check_permission(user_role, "resource:monitor"):
            raise AuthorizationError("Insufficient permissions to view VM resource usage")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise ResourceOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise ResourceOperationError(f"VM '{vm_name}' not found")
            
            resource_usage = {
                "vm_name": vm_name,
                "power_state": str(vm.runtime.powerState),
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }
            
            # Get configured resources
            if vm.config and vm.config.hardware:
                resource_usage["configured"] = {
                    "cpu_count": vm.config.hardware.numCPU,
                    "memory_mb": vm.config.hardware.memoryMB,
                    "memory_gb": round(vm.config.hardware.memoryMB / 1024, 2)
                }
            
            # Get current usage (only available when VM is powered on)
            if vm.summary and vm.summary.quickStats:
                qs = vm.summary.quickStats
                resource_usage["current_usage"] = {
                    "cpu_usage_mhz": qs.overallCpuUsage or 0,
                    "memory_usage_mb": qs.guestMemoryUsage or 0,
                    "memory_usage_gb": round((qs.guestMemoryUsage or 0) / 1024, 2),
                    "host_memory_usage_mb": qs.hostMemoryUsage or 0,
                    "uptime_seconds": qs.uptimeSeconds or 0
                }
                
                # Calculate utilization percentages
                if vm.config and vm.config.hardware:
                    cpu_utilization = 0
                    memory_utilization = 0
                    
                    if vm.config.hardware.numCPU > 0 and vm.runtime.host:
                        # Get host CPU frequency for calculation
                        host = vm.runtime.host
                        if host.hardware and host.hardware.cpuInfo:
                            cpu_mhz_per_core = host.hardware.cpuInfo.hz // 1000000
                            total_vm_cpu_mhz = vm.config.hardware.numCPU * cpu_mhz_per_core
                            cpu_utilization = (qs.overallCpuUsage or 0) / total_vm_cpu_mhz * 100
                    
                    if vm.config.hardware.memoryMB > 0:
                        memory_utilization = (qs.guestMemoryUsage or 0) / vm.config.hardware.memoryMB * 100
                    
                    resource_usage["utilization"] = {
                        "cpu_percent": round(cpu_utilization, 2),
                        "memory_percent": round(memory_utilization, 2)
                    }
            
            # Get storage usage
            if vm.storage:
                storage_info = {
                    "committed_gb": round(vm.storage.committed / (1024**3), 2),
                    "uncommitted_gb": round(vm.storage.uncommitted / (1024**3), 2),
                    "unshared_gb": round(vm.storage.unshared / (1024**3), 2)
                }
                resource_usage["storage"] = storage_info
            
            logger.info(f"Retrieved resource usage for VM: {vm_name}")
            return resource_usage
            
        except Exception as e:
            logger.error(f"Failed to get resource usage for VM {vm_name}: {str(e)}")
            raise ResourceOperationError(f"Failed to get VM resource usage: {str(e)}")
    
    @audit_log("get_datastore_usage", "resource")
    @timeout_handler()
    async def get_datastore_usage(self, user_role: str = "viewer") -> List[Dict[str, Any]]:
        """Get storage usage for all datastores."""
        if not RBACManager.check_permission(user_role, "resource:monitor"):
            raise AuthorizationError("Insufficient permissions to view datastore usage")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise ResourceOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            
            # Get all datastores
            container = content.rootFolder
            view_type = [vim.Datastore]
            recursive = True
            
            container_view = content.viewManager.CreateContainerView(
                container, view_type, recursive
            )
            
            datastores = []
            try:
                for ds in container_view.view:
                    if ds.summary:
                        capacity_gb = ds.summary.capacity / (1024**3)
                        free_space_gb = ds.summary.freeSpace / (1024**3)
                        used_space_gb = capacity_gb - free_space_gb
                        utilization_percent = (used_space_gb / capacity_gb * 100) if capacity_gb > 0 else 0
                        
                        ds_info = {
                            "name": ds.name,
                            "type": ds.summary.type,
                            "capacity_gb": round(capacity_gb, 2),
                            "free_space_gb": round(free_space_gb, 2),
                            "used_space_gb": round(used_space_gb, 2),
                            "utilization_percent": round(utilization_percent, 2),
                            "accessible": ds.summary.accessible,
                            "multiple_host_access": ds.summary.multipleHostAccess,
                            "url": ds.summary.url
                        }
                        
                        # Add VM count
                        vm_count = len(ds.vm) if ds.vm else 0
                        ds_info["vm_count"] = vm_count
                        
                        datastores.append(ds_info)
                        
            finally:
                container_view.Destroy()
            
            logger.info(f"Retrieved usage for {len(datastores)} datastores")
            return datastores
            
        except Exception as e:
            logger.error(f"Failed to get datastore usage: {str(e)}")
            raise ResourceOperationError(f"Failed to get datastore usage: {str(e)}")
    
    @audit_log("create_resource_pool", "resource")
    @timeout_handler()
    async def create_resource_pool(self, pool_name: str, parent_pool: str = None,
                                 cpu_shares: int = 1000, cpu_reservation: int = 0,
                                 cpu_limit: int = -1, memory_shares: int = 1000,
                                 memory_reservation: int = 0, memory_limit: int = -1,
                                 user_role: str = "admin") -> Dict[str, Any]:
        """Create a resource pool."""
        if not RBACManager.check_permission(user_role, "resource:allocate"):
            raise AuthorizationError("Insufficient permissions to create resource pool")
        
        if not pool_name or len(pool_name) > 80:
            raise ValidationError("Resource pool name must be 1-80 characters")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise ResourceOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            
            # Find parent resource pool or use root
            parent = None
            if parent_pool:
                # Find the specified parent pool
                container = content.rootFolder
                view_type = [vim.ResourcePool]
                recursive = True
                
                container_view = content.viewManager.CreateContainerView(
                    container, view_type, recursive
                )
                
                try:
                    for rp in container_view.view:
                        if rp.name == parent_pool:
                            parent = rp
                            break
                finally:
                    container_view.Destroy()
                
                if not parent:
                    raise ResourceOperationError(f"Parent resource pool '{parent_pool}' not found")
            else:
                # Use the first cluster's root resource pool
                for datacenter in content.rootFolder.childEntity:
                    if hasattr(datacenter, 'hostFolder'):
                        for entity in datacenter.hostFolder.childEntity:
                            if hasattr(entity, 'resourcePool'):
                                parent = entity.resourcePool
                                break
                        if parent:
                            break
            
            if not parent:
                raise ResourceOperationError("Could not find parent resource pool")
            
            # Create resource pool specification
            rp_spec = vim.ResourceConfigSpec()
            
            # CPU allocation
            rp_spec.cpuAllocation = vim.ResourceAllocationInfo()
            rp_spec.cpuAllocation.shares = vim.SharesInfo()
            rp_spec.cpuAllocation.shares.level = vim.SharesInfo.Level.custom
            rp_spec.cpuAllocation.shares.shares = cpu_shares
            rp_spec.cpuAllocation.reservation = cpu_reservation
            rp_spec.cpuAllocation.limit = cpu_limit if cpu_limit > 0 else None
            rp_spec.cpuAllocation.expandableReservation = True
            
            # Memory allocation
            rp_spec.memoryAllocation = vim.ResourceAllocationInfo()
            rp_spec.memoryAllocation.shares = vim.SharesInfo()
            rp_spec.memoryAllocation.shares.level = vim.SharesInfo.Level.custom
            rp_spec.memoryAllocation.shares.shares = memory_shares
            rp_spec.memoryAllocation.reservation = memory_reservation
            rp_spec.memoryAllocation.limit = memory_limit if memory_limit > 0 else None
            rp_spec.memoryAllocation.expandableReservation = True
            
            # Create the resource pool
            task = parent.CreateResourcePool(name=pool_name, spec=rp_spec)
            result = await wait_for_task_async(task)
            
            logger.info(f"Successfully created resource pool: {pool_name}")
            return {
                "status": "created",
                "pool_name": pool_name,
                "parent_pool": parent_pool or "root",
                "cpu_config": {
                    "shares": cpu_shares,
                    "reservation": cpu_reservation,
                    "limit": cpu_limit
                },
                "memory_config": {
                    "shares": memory_shares,
                    "reservation": memory_reservation,
                    "limit": memory_limit
                },
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to create resource pool {pool_name}: {str(e)}")
            raise ResourceOperationError(f"Failed to create resource pool: {str(e)}")


# Global resource operations instance
resource_ops = ResourceOperations()
