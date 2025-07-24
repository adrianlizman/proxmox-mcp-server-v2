
"""Snapshot operations module for VMware MCP Server."""

import logging
from typing import Dict, List, Any, Optional
from pyVmomi import vim
from .auth import auth_manager, RBACManager
from .exceptions import SnapshotOperationError, AuthorizationError, ValidationError
from .utils import (
    async_retry, timeout_handler, audit_log, wait_for_task_async,
    get_vm_by_name, validate_vm_name
)

logger = logging.getLogger(__name__)


class SnapshotOperations:
    """Handles all snapshot-related operations."""
    
    def __init__(self):
        self.auth_manager = auth_manager
    
    @audit_log("create_snapshot", "snapshot")
    @timeout_handler(timeout_seconds=600)
    async def create_snapshot(self, vm_name: str, snapshot_name: str, 
                            description: str = "", memory: bool = False, 
                            quiesce: bool = True, user_role: str = "operator") -> Dict[str, Any]:
        """Create a snapshot of a VM."""
        if not RBACManager.check_permission(user_role, "snapshot:create"):
            raise AuthorizationError("Insufficient permissions to create snapshot")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        if not snapshot_name or len(snapshot_name) > 80:
            raise ValidationError("Snapshot name must be 1-80 characters")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise SnapshotOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise SnapshotOperationError(f"VM '{vm_name}' not found")
            
            # Check if snapshot with same name already exists
            if vm.snapshot:
                existing_snapshots = self._get_all_snapshot_names(vm.snapshot.rootSnapshotList)
                if snapshot_name in existing_snapshots:
                    raise SnapshotOperationError(f"Snapshot '{snapshot_name}' already exists")
            
            # Create snapshot
            task = vm.CreateSnapshot_Task(
                name=snapshot_name,
                description=description,
                memory=memory,
                quiesce=quiesce
            )
            
            result = await wait_for_task_async(task, timeout=600)
            
            logger.info(f"Successfully created snapshot '{snapshot_name}' for VM: {vm_name}")
            return {
                "status": "created",
                "vm_name": vm_name,
                "snapshot_name": snapshot_name,
                "description": description,
                "memory": memory,
                "quiesce": quiesce,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to create snapshot '{snapshot_name}' for VM {vm_name}: {str(e)}")
            raise SnapshotOperationError(f"Failed to create snapshot: {str(e)}")
    
    @audit_log("list_snapshots", "snapshot")
    @timeout_handler()
    async def list_snapshots(self, vm_name: str, user_role: str = "viewer") -> Dict[str, Any]:
        """List all snapshots for a VM."""
        if not RBACManager.check_permission(user_role, "vm:list"):
            raise AuthorizationError("Insufficient permissions to list snapshots")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise SnapshotOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise SnapshotOperationError(f"VM '{vm_name}' not found")
            
            if not vm.snapshot:
                return {
                    "vm_name": vm_name,
                    "snapshots": [],
                    "current_snapshot": None
                }
            
            # Format snapshot tree
            snapshots = self._format_snapshot_tree(vm.snapshot.rootSnapshotList)
            current_snapshot = None
            
            if vm.snapshot.currentSnapshot:
                current_snapshot = {
                    "name": vm.snapshot.currentSnapshot.name,
                    "description": vm.snapshot.currentSnapshot.description,
                    "create_time": vm.snapshot.currentSnapshot.createTime.isoformat() if vm.snapshot.currentSnapshot.createTime else None
                }
            
            logger.info(f"Listed snapshots for VM: {vm_name}")
            return {
                "vm_name": vm_name,
                "snapshots": snapshots,
                "current_snapshot": current_snapshot
            }
            
        except Exception as e:
            logger.error(f"Failed to list snapshots for VM {vm_name}: {str(e)}")
            raise SnapshotOperationError(f"Failed to list snapshots: {str(e)}")
    
    @audit_log("revert_snapshot", "snapshot")
    @timeout_handler(timeout_seconds=600)
    async def revert_snapshot(self, vm_name: str, snapshot_name: str, 
                            user_role: str = "operator") -> Dict[str, Any]:
        """Revert VM to a specific snapshot."""
        if not RBACManager.check_permission(user_role, "snapshot:revert"):
            raise AuthorizationError("Insufficient permissions to revert snapshot")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise SnapshotOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise SnapshotOperationError(f"VM '{vm_name}' not found")
            
            if not vm.snapshot:
                raise SnapshotOperationError(f"VM '{vm_name}' has no snapshots")
            
            # Find the snapshot
            snapshot = self._find_snapshot_by_name(vm.snapshot.rootSnapshotList, snapshot_name)
            if not snapshot:
                raise SnapshotOperationError(f"Snapshot '{snapshot_name}' not found")
            
            # Revert to snapshot
            task = snapshot.RevertToSnapshot_Task()
            result = await wait_for_task_async(task, timeout=600)
            
            logger.info(f"Successfully reverted VM '{vm_name}' to snapshot '{snapshot_name}'")
            return {
                "status": "reverted",
                "vm_name": vm_name,
                "snapshot_name": snapshot_name,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to revert VM {vm_name} to snapshot {snapshot_name}: {str(e)}")
            raise SnapshotOperationError(f"Failed to revert snapshot: {str(e)}")
    
    @audit_log("delete_snapshot", "snapshot")
    @timeout_handler(timeout_seconds=600)
    async def delete_snapshot(self, vm_name: str, snapshot_name: str, 
                            remove_children: bool = False, user_role: str = "operator") -> Dict[str, Any]:
        """Delete a specific snapshot."""
        if not RBACManager.check_permission(user_role, "snapshot:delete"):
            raise AuthorizationError("Insufficient permissions to delete snapshot")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise SnapshotOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise SnapshotOperationError(f"VM '{vm_name}' not found")
            
            if not vm.snapshot:
                raise SnapshotOperationError(f"VM '{vm_name}' has no snapshots")
            
            # Find the snapshot
            snapshot = self._find_snapshot_by_name(vm.snapshot.rootSnapshotList, snapshot_name)
            if not snapshot:
                raise SnapshotOperationError(f"Snapshot '{snapshot_name}' not found")
            
            # Delete snapshot
            task = snapshot.RemoveSnapshot_Task(removeChildren=remove_children)
            result = await wait_for_task_async(task, timeout=600)
            
            logger.info(f"Successfully deleted snapshot '{snapshot_name}' from VM '{vm_name}'")
            return {
                "status": "deleted",
                "vm_name": vm_name,
                "snapshot_name": snapshot_name,
                "remove_children": remove_children,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to delete snapshot {snapshot_name} from VM {vm_name}: {str(e)}")
            raise SnapshotOperationError(f"Failed to delete snapshot: {str(e)}")
    
    @audit_log("delete_all_snapshots", "snapshot")
    @timeout_handler(timeout_seconds=900)
    async def delete_all_snapshots(self, vm_name: str, user_role: str = "operator") -> Dict[str, Any]:
        """Delete all snapshots for a VM."""
        if not RBACManager.check_permission(user_role, "snapshot:delete"):
            raise AuthorizationError("Insufficient permissions to delete snapshots")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise SnapshotOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise SnapshotOperationError(f"VM '{vm_name}' not found")
            
            if not vm.snapshot:
                return {
                    "status": "no_snapshots",
                    "vm_name": vm_name,
                    "message": "VM has no snapshots to delete"
                }
            
            # Count snapshots before deletion
            snapshot_count = len(self._get_all_snapshot_names(vm.snapshot.rootSnapshotList))
            
            # Delete all snapshots
            task = vm.RemoveAllSnapshots_Task()
            result = await wait_for_task_async(task, timeout=900)
            
            logger.info(f"Successfully deleted all {snapshot_count} snapshots from VM '{vm_name}'")
            return {
                "status": "all_deleted",
                "vm_name": vm_name,
                "snapshots_deleted": snapshot_count,
                "task_result": str(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to delete all snapshots from VM {vm_name}: {str(e)}")
            raise SnapshotOperationError(f"Failed to delete all snapshots: {str(e)}")
    
    @audit_log("consolidate_snapshots", "snapshot")
    @timeout_handler(timeout_seconds=900)
    async def consolidate_snapshots(self, vm_name: str, user_role: str = "operator") -> Dict[str, Any]:
        """Consolidate VM snapshots (merge snapshot files)."""
        if not RBACManager.check_permission(user_role, "snapshot:delete"):
            raise AuthorizationError("Insufficient permissions to consolidate snapshots")
        
        if not validate_vm_name(vm_name):
            raise ValidationError(f"Invalid VM name: {vm_name}")
        
        try:
            si = self.auth_manager.get_service_instance()
            if not si:
                raise SnapshotOperationError("No active VMware connection")
            
            content = si.RetrieveContent()
            vm = get_vm_by_name(content, vm_name)
            
            if not vm:
                raise SnapshotOperationError(f"VM '{vm_name}' not found")
            
            # Check if consolidation is needed
            if vm.runtime.consolidationNeeded:
                task = vm.ConsolidateVMDisks_Task()
                result = await wait_for_task_async(task, timeout=900)
                
                logger.info(f"Successfully consolidated snapshots for VM '{vm_name}'")
                return {
                    "status": "consolidated",
                    "vm_name": vm_name,
                    "task_result": str(result)
                }
            else:
                return {
                    "status": "no_consolidation_needed",
                    "vm_name": vm_name,
                    "message": "VM does not require snapshot consolidation"
                }
            
        except Exception as e:
            logger.error(f"Failed to consolidate snapshots for VM {vm_name}: {str(e)}")
            raise SnapshotOperationError(f"Failed to consolidate snapshots: {str(e)}")
    
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
                "id": snapshot.id,
                "children": self._format_snapshot_tree(snapshot.childSnapshotList)
            }
            result.append(snap_info)
        return result
    
    def _find_snapshot_by_name(self, snapshots: List[vim.vm.SnapshotTree], 
                              snapshot_name: str) -> Optional[vim.vm.Snapshot]:
        """Find a snapshot by name in the snapshot tree."""
        for snapshot in snapshots:
            if snapshot.name == snapshot_name:
                return snapshot.snapshot
            
            # Search in children
            child_result = self._find_snapshot_by_name(snapshot.childSnapshotList, snapshot_name)
            if child_result:
                return child_result
        
        return None
    
    def _get_all_snapshot_names(self, snapshots: List[vim.vm.SnapshotTree]) -> List[str]:
        """Get all snapshot names from the snapshot tree."""
        names = []
        for snapshot in snapshots:
            names.append(snapshot.name)
            names.extend(self._get_all_snapshot_names(snapshot.childSnapshotList))
        return names


# Global snapshot operations instance
snapshot_ops = SnapshotOperations()
