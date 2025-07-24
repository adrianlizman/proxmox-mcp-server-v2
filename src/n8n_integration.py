
"""n8n workflow automation integration for Proxmox MCP Server."""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
import httpx
from datetime import datetime

from .config import settings
from .exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)


class N8NIntegration:
    """Integration with n8n for workflow automation."""
    
    def __init__(self):
        self.n8n_host = settings.n8n_host
        self.webhook_url = settings.n8n_webhook_url
        self.enabled = settings.enable_n8n_integration
        
    async def trigger_webhook(self, webhook_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger an n8n webhook with data."""
        if not self.enabled:
            return {"status": "disabled", "message": "n8n integration is disabled"}
        
        try:
            webhook_url = f"{self.webhook_url}/{webhook_name}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook_url,
                    json={
                        "timestamp": datetime.now().isoformat(),
                        "source": "proxmox-mcp-server",
                        "data": data
                    }
                )
                
                if response.status_code == 200:
                    return {
                        "status": "success",
                        "webhook": webhook_name,
                        "response": response.json() if response.content else {}
                    }
                else:
                    logger.error(f"n8n webhook error: {response.status_code} - {response.text}")
                    return {
                        "status": "error",
                        "webhook": webhook_name,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error triggering n8n webhook {webhook_name}: {str(e)}")
            return {
                "status": "error",
                "webhook": webhook_name,
                "error": str(e)
            }
    
    async def notify_vm_lifecycle_event(self, event_type: str, vm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notify n8n about VM lifecycle events."""
        return await self.trigger_webhook("vm-lifecycle", {
            "event_type": event_type,
            "vm": vm_data
        })
    
    async def notify_container_lifecycle_event(self, event_type: str, container_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notify n8n about container lifecycle events."""
        return await self.trigger_webhook("container-lifecycle", {
            "event_type": event_type,
            "container": container_data
        })
    
    async def notify_backup_event(self, event_type: str, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notify n8n about backup events."""
        return await self.trigger_webhook("backup-event", {
            "event_type": event_type,
            "backup": backup_data
        })
    
    async def notify_performance_alert(self, alert_type: str, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notify n8n about performance alerts."""
        return await self.trigger_webhook("performance-alert", {
            "alert_type": alert_type,
            "resource": resource_data,
            "severity": self._determine_alert_severity(alert_type, resource_data)
        })
    
    async def notify_cluster_event(self, event_type: str, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notify n8n about cluster events."""
        return await self.trigger_webhook("cluster-event", {
            "event_type": event_type,
            "cluster": cluster_data
        })
    
    async def notify_storage_alert(self, alert_type: str, storage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notify n8n about storage alerts."""
        return await self.trigger_webhook("storage-alert", {
            "alert_type": alert_type,
            "storage": storage_data,
            "severity": self._determine_storage_severity(storage_data)
        })
    
    async def trigger_maintenance_workflow(self, maintenance_type: str, target_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger maintenance workflows."""
        return await self.trigger_webhook("maintenance-workflow", {
            "maintenance_type": maintenance_type,
            "target": target_data,
            "scheduled_time": datetime.now().isoformat()
        })
    
    async def trigger_backup_workflow(self, backup_config: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger automated backup workflows."""
        return await self.trigger_webhook("backup-workflow", {
            "backup_config": backup_config,
            "trigger_time": datetime.now().isoformat()
        })
    
    async def send_custom_notification(self, notification_type: str, message: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send custom notifications through n8n."""
        return await self.trigger_webhook("custom-notification", {
            "notification_type": notification_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        })
    
    def _determine_alert_severity(self, alert_type: str, resource_data: Dict[str, Any]) -> str:
        """Determine alert severity based on metrics."""
        if alert_type == "high_cpu_usage":
            cpu_usage = resource_data.get('cpu_usage_percent', 0)
            if cpu_usage > 95:
                return "critical"
            elif cpu_usage > 85:
                return "warning"
            else:
                return "info"
        
        elif alert_type == "high_memory_usage":
            memory_usage = resource_data.get('memory_usage_percent', 0)
            if memory_usage > 95:
                return "critical"
            elif memory_usage > 85:
                return "warning"
            else:
                return "info"
        
        elif alert_type == "node_offline":
            return "critical"
        
        elif alert_type == "vm_stopped":
            return "warning"
        
        else:
            return "info"
    
    def _determine_storage_severity(self, storage_data: Dict[str, Any]) -> str:
        """Determine storage alert severity."""
        usage_percent = storage_data.get('usage_percentage', 0)
        
        if usage_percent > 95:
            return "critical"
        elif usage_percent > 85:
            return "warning"
        else:
            return "info"
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of a specific n8n workflow."""
        if not self.enabled:
            return {"status": "disabled", "message": "n8n integration is disabled"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.n8n_host}/api/v1/workflows/{workflow_id}")
                
                if response.status_code == 200:
                    return {
                        "status": "success",
                        "workflow": response.json()
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error getting workflow status: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def list_active_workflows(self) -> Dict[str, Any]:
        """List all active n8n workflows."""
        if not self.enabled:
            return {"status": "disabled", "message": "n8n integration is disabled"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.n8n_host}/api/v1/workflows")
                
                if response.status_code == 200:
                    workflows = response.json()
                    active_workflows = [w for w in workflows if w.get('active', False)]
                    
                    return {
                        "status": "success",
                        "total_workflows": len(workflows),
                        "active_workflows": len(active_workflows),
                        "workflows": active_workflows
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error listing workflows: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


# Global n8n integration instance
n8n_integration = N8NIntegration()


class ProxmoxWorkflowTrigger:
    """Helper class to trigger workflows based on Proxmox events."""
    
    def __init__(self):
        self.n8n = n8n_integration
    
    async def on_vm_created(self, vm_data: Dict[str, Any]):
        """Trigger workflows when VM is created."""
        await self.n8n.notify_vm_lifecycle_event("created", vm_data)
        
        # Trigger additional workflows based on VM type or configuration
        if vm_data.get('template'):
            await self.n8n.trigger_webhook("template-deployed", vm_data)
    
    async def on_vm_started(self, vm_data: Dict[str, Any]):
        """Trigger workflows when VM is started."""
        await self.n8n.notify_vm_lifecycle_event("started", vm_data)
    
    async def on_vm_stopped(self, vm_data: Dict[str, Any]):
        """Trigger workflows when VM is stopped."""
        await self.n8n.notify_vm_lifecycle_event("stopped", vm_data)
        await self.n8n.notify_performance_alert("vm_stopped", vm_data)
    
    async def on_vm_deleted(self, vm_data: Dict[str, Any]):
        """Trigger workflows when VM is deleted."""
        await self.n8n.notify_vm_lifecycle_event("deleted", vm_data)
    
    async def on_container_created(self, container_data: Dict[str, Any]):
        """Trigger workflows when container is created."""
        await self.n8n.notify_container_lifecycle_event("created", container_data)
    
    async def on_container_started(self, container_data: Dict[str, Any]):
        """Trigger workflows when container is started."""
        await self.n8n.notify_container_lifecycle_event("started", container_data)
    
    async def on_container_stopped(self, container_data: Dict[str, Any]):
        """Trigger workflows when container is stopped."""
        await self.n8n.notify_container_lifecycle_event("stopped", container_data)
    
    async def on_backup_completed(self, backup_data: Dict[str, Any]):
        """Trigger workflows when backup is completed."""
        await self.n8n.notify_backup_event("completed", backup_data)
        
        # Trigger cleanup workflows if needed
        if backup_data.get('cleanup_required'):
            await self.n8n.trigger_webhook("backup-cleanup", backup_data)
    
    async def on_backup_failed(self, backup_data: Dict[str, Any]):
        """Trigger workflows when backup fails."""
        await self.n8n.notify_backup_event("failed", backup_data)
        await self.n8n.send_custom_notification("backup_failure", 
            f"Backup failed for VM/CT {backup_data.get('vmid')}", backup_data)
    
    async def on_high_resource_usage(self, resource_type: str, resource_data: Dict[str, Any]):
        """Trigger workflows for high resource usage."""
        await self.n8n.notify_performance_alert(f"high_{resource_type}_usage", resource_data)
        
        # Trigger auto-scaling workflows if configured
        if resource_data.get('auto_scale_enabled'):
            await self.n8n.trigger_webhook("auto-scale", {
                "resource_type": resource_type,
                "resource_data": resource_data
            })
    
    async def on_node_offline(self, node_data: Dict[str, Any]):
        """Trigger workflows when node goes offline."""
        await self.n8n.notify_cluster_event("node_offline", node_data)
        await self.n8n.notify_performance_alert("node_offline", node_data)
    
    async def on_storage_full(self, storage_data: Dict[str, Any]):
        """Trigger workflows when storage is full."""
        await self.n8n.notify_storage_alert("storage_full", storage_data)
        
        # Trigger cleanup workflows
        await self.n8n.trigger_webhook("storage-cleanup", storage_data)
    
    async def schedule_maintenance(self, maintenance_type: str, target_data: Dict[str, Any], schedule_time: str):
        """Schedule maintenance workflows."""
        await self.n8n.trigger_maintenance_workflow(maintenance_type, {
            **target_data,
            "schedule_time": schedule_time
        })


# Global workflow trigger instance
workflow_trigger = ProxmoxWorkflowTrigger()
