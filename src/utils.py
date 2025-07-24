
"""Utility functions for VMware MCP Server."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from pyVmomi import vim
from pyVim.task import WaitForTask
from .exceptions import TimeoutError, VMwareMCPException
from .config import settings

logger = logging.getLogger(__name__)


def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying async functions with exponential backoff."""
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {current_delay}s..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


def timeout_handler(timeout_seconds: int = None):
    """Decorator to add timeout to functions."""
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            timeout = timeout_seconds or settings.operation_timeout
            
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Operation {func.__name__} timed out after {timeout}s")
        
        return wrapper
    return decorator


def audit_log(operation: str, resource_type: str = None):
    """Decorator for audit logging."""
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            audit_logger = logging.getLogger("vmware_mcp.audit")
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                audit_logger.info({
                    "operation": operation,
                    "resource_type": resource_type,
                    "status": "success",
                    "duration": duration,
                    "timestamp": time.time()
                })
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                audit_logger.error({
                    "operation": operation,
                    "resource_type": resource_type,
                    "status": "failed",
                    "error": str(e),
                    "duration": duration,
                    "timestamp": time.time()
                })
                
                raise
        
        return wrapper
    return decorator


async def wait_for_task_async(task: vim.Task, timeout: int = None) -> Any:
    """Asynchronously wait for a VMware task to complete."""
    timeout = timeout or settings.operation_timeout
    start_time = time.time()
    
    while task.info.state in [vim.TaskInfo.State.running, vim.TaskInfo.State.queued]:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Task {task.info.key} timed out after {timeout}s")
        
        await asyncio.sleep(1)
    
    if task.info.state == vim.TaskInfo.State.success:
        return task.info.result
    elif task.info.state == vim.TaskInfo.State.error:
        raise VMwareMCPException(f"Task failed: {task.info.error.msg}")
    else:
        raise VMwareMCPException(f"Task ended with unexpected state: {task.info.state}")


def get_vm_by_name(content: vim.ServiceContent, vm_name: str) -> Optional[vim.VirtualMachine]:
    """Find a VM by name."""
    container = content.rootFolder
    view_type = [vim.VirtualMachine]
    recursive = True
    
    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )
    
    try:
        for vm in container_view.view:
            if vm.name == vm_name:
                return vm
        return None
    finally:
        container_view.Destroy()


def get_host_by_name(content: vim.ServiceContent, host_name: str) -> Optional[vim.HostSystem]:
    """Find a host by name."""
    container = content.rootFolder
    view_type = [vim.HostSystem]
    recursive = True
    
    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )
    
    try:
        for host in container_view.view:
            if host.name == host_name:
                return host
        return None
    finally:
        container_view.Destroy()


def get_datastore_by_name(content: vim.ServiceContent, ds_name: str) -> Optional[vim.Datastore]:
    """Find a datastore by name."""
    container = content.rootFolder
    view_type = [vim.Datastore]
    recursive = True
    
    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )
    
    try:
        for ds in container_view.view:
            if ds.name == ds_name:
                return ds
        return None
    finally:
        container_view.Destroy()


def get_all_vms(content: vim.ServiceContent) -> List[vim.VirtualMachine]:
    """Get all VMs in the inventory."""
    container = content.rootFolder
    view_type = [vim.VirtualMachine]
    recursive = True
    
    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )
    
    try:
        return list(container_view.view)
    finally:
        container_view.Destroy()


def get_all_hosts(content: vim.ServiceContent) -> List[vim.HostSystem]:
    """Get all hosts in the inventory."""
    container = content.rootFolder
    view_type = [vim.HostSystem]
    recursive = True
    
    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )
    
    try:
        return list(container_view.view)
    finally:
        container_view.Destroy()


def format_vm_info(vm: vim.VirtualMachine) -> Dict[str, Any]:
    """Format VM information for API responses."""
    try:
        return {
            "name": vm.name,
            "uuid": vm.config.uuid if vm.config else None,
            "power_state": str(vm.runtime.powerState) if vm.runtime else "unknown",
            "guest_os": vm.config.guestFullName if vm.config else "unknown",
            "cpu_count": vm.config.hardware.numCPU if vm.config and vm.config.hardware else 0,
            "memory_mb": vm.config.hardware.memoryMB if vm.config and vm.config.hardware else 0,
            "host": vm.runtime.host.name if vm.runtime and vm.runtime.host else "unknown",
            "datastore": [ds.name for ds in vm.datastore] if vm.datastore else [],
            "network": [net.name for net in vm.network] if vm.network else [],
            "tools_status": str(vm.guest.toolsStatus) if vm.guest else "unknown",
            "ip_address": vm.guest.ipAddress if vm.guest else None,
        }
    except Exception as e:
        logger.error(f"Error formatting VM info: {str(e)}")
        return {"name": vm.name, "error": str(e)}


def format_host_info(host: vim.HostSystem) -> Dict[str, Any]:
    """Format host information for API responses."""
    try:
        return {
            "name": host.name,
            "connection_state": str(host.runtime.connectionState) if host.runtime else "unknown",
            "power_state": str(host.runtime.powerState) if host.runtime else "unknown",
            "maintenance_mode": host.runtime.inMaintenanceMode if host.runtime else False,
            "cpu_cores": host.hardware.cpuInfo.numCpuCores if host.hardware and host.hardware.cpuInfo else 0,
            "cpu_threads": host.hardware.cpuInfo.numCpuThreads if host.hardware and host.hardware.cpuInfo else 0,
            "memory_mb": host.hardware.memorySize // (1024 * 1024) if host.hardware else 0,
            "version": host.config.product.version if host.config and host.config.product else "unknown",
            "build": host.config.product.build if host.config and host.config.product else "unknown",
            "vendor": host.hardware.systemInfo.vendor if host.hardware and host.hardware.systemInfo else "unknown",
            "model": host.hardware.systemInfo.model if host.hardware and host.hardware.systemInfo else "unknown",
        }
    except Exception as e:
        logger.error(f"Error formatting host info: {str(e)}")
        return {"name": host.name, "error": str(e)}


def validate_vm_name(vm_name: str) -> bool:
    """Validate VM name format."""
    if not vm_name or len(vm_name) < 1 or len(vm_name) > 80:
        return False
    
    # Check for invalid characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    return not any(char in vm_name for char in invalid_chars)


def validate_host_name(host_name: str) -> bool:
    """Validate host name format."""
    if not host_name or len(host_name) < 1 or len(host_name) > 253:
        return False
    
    # Basic hostname validation
    import re
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(pattern, host_name))


def bytes_to_human_readable(bytes_value: int) -> str:
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"
