
"""VM operations module for VMware MCP Server."""

import logging
from typing import Dict, List, Any, Optional
from pyVmomi import vim
from .auth import auth_manager, RBACManager
from .exceptions import VMOperationError, AuthorizationError, ValidationError
from .utils import (
    async_retry, timeout_handler, audit_log, wait_for_task_async,
    get_vm_by_name, get_all_vms, format_vm_info, validate_vm_name
)

logger = logging.getLogger(__name__)


class VMOperations:
    """Handles all VM-related operations."""
    
    def __init__(self):
        self.auth_manager = auth_manager
    
    @audit_log("list_vms", "vm")
    @timeout_handler()
    async def list_vms(self, user_role: str = "viewer") -> List[Dict[str, Any]]:
        """List all VMs with their basic information."""
        if not RBACManager.check_permission(user_role, "vm:list"):
            raise AuthorizationError("Insufficient permissions to list VMs")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise VMOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vms = get_all_vms(content)
            
            vm_list = []
            for vm in vms:
                vm_info = format_vm_info(vm)
                vm_list.append(vm_info)
            
            logger.info(f"Listed {len(vm_list)} VMs")
            return vm_list
            
        except Exception as e:
            logger.error(f"Failed to list VMs: {str(e)}")
            raise VMOperationError(f"Failed to list VMs: {str(e)}")
    
    @audit_log("get_vm_details", "vm")
    @timeout_handler()
    async def get_vm_details(self, vm_name: str, user_role: str = "viewer") -> Dict[str, Any]:
        """Get detailed information about a specific VM."""
        if not RBACManager.check_permission(user_role, "vm:list"):
            raise AuthorizationError("Insufficient permissions to view VM details")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise VMOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise VMOperationError(f"VM '{vm_name}' not found")
            
            # Get detailed VM information
            vm_details = format_vm_info(vm)
            
            # Add additional details
            if vm.config:
                vm_details.update({
                    "annotation": vm.config.annotation or "",
                    "template": vm.config.template,
                    "created": vm.config.createDate.isoformat() if vm.config.createDate else None,
                    "modified": vm.config.modified.isoformat() if vm.config.modified else None,
                    "files": {
                        "vmx_path": vm.config.files.vmPathName if vm.config.files else None,
                        "log_directory": vm.config.files.logDirectory if vm.config.files else None,
                    }
                })
            
            # Add snapshot information
            if vm.snapshot:
                vm_details["snapshots"] = self._format_snapshot_tree(vm.snapshot.rootSnapshotList)
            else:
                vm_details["snapshots"] = []
            
            logger.info(f"Retrieved details for VM: {vm_name}")
            return vm_details
            
        except Exception as e:
            logger.error(f"Failed to get VM details for {vm_name}: {str(e)}")
            raise VMOperationError(f"Failed to get VM details: {str(e)}")
    
    @audit_log("start_vm", "vm")
    @async_retry(max_retries=2)
    @timeout_handler()
    async def start_vm(self, vm_name: str, user_role: str = "operator") -> Dict[str, Any]:
        """Start a VM."""
        if not RBACManager.check_permission(user_role, "vm:start"):
            raise AuthorizationError("Insufficient permissions to start VM")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise VMOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise VMOperationError(f"VM '{vm_name}' not found")
            
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                return {"status": "already_running", "vm_name": vm_name}
            
            task = vm.PowerOnVM_Task()
            result = await wait_for_task_async(task)
            
            logger.info(f"Successfully started VM: {vm_name}")
            return {"status": "started", "vm_name": vm_name, "task_result": str(result)}
            
        except Exception as e:
            logger.error(f"Failed to start VM {vm_name}: {str(e)}")
            raise VMOperationError(f"Failed to start VM: {str(e)}")
    
    @audit_log("stop_vm", "vm")
    @async_retry(max_retries=2)
    @timeout_handler()
    async def stop_vm(self, vm_name: str, force: bool = False, user_role: str = "operator") -> Dict[str, Any]:
        """Stop a VM gracefully or forcefully."""
        if not RBACManager.check_permission(user_role, "vm:stop"):
            raise AuthorizationError("Insufficient permissions to stop VM")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise VMOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise VMOperationError(f"VM '{vm_name}' not found")
            
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
                return {"status": "already_stopped", "vm_name": vm_name}
            
            if force:
                task = vm.PowerOffVM_Task()
                method = "force_stop"
            else:
                # Try graceful shutdown first
                try:
                    vm.ShutdownGuest()
                    method = "graceful_shutdown"
                    # Wait a bit for graceful shutdown
                    import asyncio
                    await asyncio.sleep(5)
                    
                    # Check if it's still running
                    if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                        # Fall back to power off
                        task = vm.PowerOffVM_Task()
                        method = "force_stop_fallback"
                    else:
                        return {"status": "stopped", "vm_name": vm_name, "method": method}
                except:
                    # If graceful shutdown fails, force power off
                    task = vm.PowerOffVM_Task()
                    method = "force_stop_fallback"
            
            if 'task' in locals():
                result = await wait_for_task_async(task)
                logger.info(f"Successfully stopped VM: {vm_name} using {method}")
                return {"status": "stopped", "vm_name": vm_name, "method": method, "task_result": str(result)}
            
        except Exception as e:
            logger.error(f"Failed to stop VM {vm_name}: {str(e)}")
            raise VMOperationError(f"Failed to stop VM: {str(e)}")
    
    @audit_log("restart_vm", "vm")
    @async_retry(max_retries=2)
    @timeout_handler()
    async def restart_vm(self, vm_name: str, force: bool = False, user_role: str = "operator") -> Dict[str, Any]:
        """Restart a VM."""
        if not RBACManager.check_permission(user_role, "vm:start"):
            raise AuthorizationError("Insufficient permissions to restart VM")
        
        try:
            # Stop the VM first
            stop_result = await self.stop_vm(vm_name, force, user_role)
            
            # Wait a moment
            import asyncio
            await asyncio.sleep(2)
            
            # Start the VM
            start_result = await self.start_vm(vm_name, user_role)
            
            logger.info(f"Successfully restarted VM: {vm_name}")
            return {
                "status": "restarted",
                "vm_name": vm_name,
                "stop_result": stop_result,
                "start_result": start_result
            }
            
        except Exception as e:
            logger.error(f"Failed to restart VM {vm_name}: {str(e)}")
            raise VMOperationError(f"Failed to restart VM: {str(e)}")
    
    @audit_log("clone_vm", "vm")
    @timeout_handler(timeout_seconds=600)  # Cloning can take longer
    async def clone_vm(self, source_vm_name: str, clone_name: str, 
                      datastore_name: str = None, user_role: str = "operator") -> Dict[str, Any]:
        """Clone a VM."""
        if not RBACManager.check_permission(user_role, "vm:clone"):
            raise AuthorizationError("Insufficient permissions to clone VM")
        
        if not validate_vm_name(source_vm_name) or not validate_vm_name(clone_name):
            raise ValidationError("Invalid VM name format")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise VMOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            source_vm = get_vm_by_name(content, source_vm_name)
            
            if not source_vm:
                raise VMOperationError(f"Source VM '{source_vm_name}' not found")
            
            # Check if clone name already exists
            existing_vm = get_vm_by_name(content, clone_name)
            if existing_vm:
                raise VMOperationError(f"VM with name '{clone_name}' already exists")
            
            # Get the folder where the source VM resides
            vm_folder = source_vm.parent
            
            # Create clone specification
            clone_spec = vim.vm.CloneSpec()
            clone_spec.location = vim.vm.RelocateSpec()
            
            # Set datastore if specified
            if datastore_name:
                from .utils import get_datastore_by_name
                datastore = get_datastore_by_name(content, datastore_name)
                if not datastore:
                    raise VMOperationError(f"Datastore '{datastore_name}' not found")
                clone_spec.location.datastore = datastore
            
            # Power off the clone by default
            clone_spec.powerOn = False
            clone_spec.template = False
            
            # Start the clone task
            task = source_vm.CloneVM_Task(folder=vm_folder, name=clone_name, spec=clone_spec)
            result = await wait_for_task_async(task, timeout=600)
            
            logger.info(f"Successfully cloned VM {source_vm_name} to {clone_name}")
            return {
                "status": "cloned",
                "source_vm": source_vm_name,
                "clone_name": clone_name,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to clone VM {source_vm_name} to {clone_name}: {str(e)}")
            raise VMOperationError(f"Failed to clone VM: {str(e)}")
    
    @audit_log("delete_vm", "vm")
    @timeout_handler()
    async def delete_vm(self, vm_name: str, user_role: str = "admin") -> Dict[str, Any]:
        """Delete a VM (destroy from disk)."""
        if not RBACManager.check_permission(user_role, "vm:delete"):
            raise AuthorizationError("Insufficient permissions to delete VM")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise VMOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise VMOperationError(f"VM '{vm_name}' not found")
            
            # Power off VM if it's running
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                power_off_task = vm.PowerOffVM_Task()
                await wait_for_task_async(power_off_task)
            
            # Delete the VM
            task = vm.Destroy_Task()
            result = await wait_for_task_async(task)
            
            logger.info(f"Successfully deleted VM: {vm_name}")
            return {"status": "deleted", "vm_name": vm_name, "task_result": str(result)}
            
        except Exception as e:
            logger.error(f"Failed to delete VM {vm_name}: {str(e)}")
            raise VMOperationError(f"Failed to delete VM: {str(e)}")
    
    @audit_log("migrate_vm", "vm")
    @timeout_handler(timeout_seconds=600)
    async def migrate_vm(self, vm_name: str, target_host: str = None, 
                        target_datastore: str = None, user_role: str = "admin") -> Dict[str, Any]:
        """Migrate a VM to a different host or datastore."""
        if not RBACManager.check_permission(user_role, "vm:migrate"):
            raise AuthorizationError("Insufficient permissions to migrate VM")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise VMOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise VMOperationError(f"VM '{vm_name}' not found")
            
            # Create relocate spec
            relocate_spec = vim.vm.RelocateSpec()
            
            if target_host:
                from .utils import get_host_by_name
                host = get_host_by_name(content, target_host)
                if not host:
                    raise VMOperationError(f"Target host '{target_host}' not found")
                relocate_spec.host = host
            
            if target_datastore:
                from .utils import get_datastore_by_name
                datastore = get_datastore_by_name(content, target_datastore)
                if not datastore:
                    raise VMOperationError(f"Target datastore '{target_datastore}' not found")
                relocate_spec.datastore = datastore
            
            # Start migration task
            task = vm.RelocateVM_Task(spec=relocate_spec)
            result = await wait_for_task_async(task, timeout=600)
            
            logger.info(f"Successfully migrated VM: {vm_name}")
            return {
                "status": "migrated",
                "vm_name": vm_name,
                "target_host": target_host,
                "target_datastore": target_datastore,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to migrate VM {vm_name}: {str(e)}")
            raise VMOperationError(f"Failed to migrate VM: {str(e)}")
    
    def _format_snapshot_tree(self, snapshots: List[vim.vm.SnapshotTree]) -> List[Dict[str, Any]]:
        """Format snapshot tree for API response."""
        result = []
        for snapshot in snapshots:
            snap_info = {
                "name": snapshot.name,
                "description": snapshot.description,
                "create_time": snapshot.createTime.isoformat() if snapshot.createTime else None,
                "state": str(snapshot.state),
                "quiesced": snapshot.quiesced,
                "backup_manifest": snapshot.backupManifest,
                "children": self._format_snapshot_tree(snapshot.childSnapshotList)
            }
            result.append(snap_info)
        return result


# Global VM operations instance
vm_ops = VMOperations()
