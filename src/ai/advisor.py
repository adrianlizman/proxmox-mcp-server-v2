
"""AI-powered advisor for Proxmox VE using Ollama integration."""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
import httpx
from datetime import datetime, timedelta

from ..config import settings
from ..exceptions import ProxmoxMCPException

logger = logging.getLogger(__name__)


class ProxmoxAIAdvisor:
    """AI advisor for Proxmox VE operations using Ollama."""
    
    def __init__(self):
        self.ollama_host = settings.ollama_host
        self.model = settings.ollama_model
        self.enabled = settings.enable_ai_features
        
    async def _query_ollama(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Query Ollama with a prompt and optional context."""
        if not self.enabled:
            return "AI features are disabled"
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 1000
                    }
                }
                
                if context:
                    payload["context"] = json.dumps(context)
                
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "No response from AI model")
                else:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    return "AI service temporarily unavailable"
                    
        except Exception as e:
            logger.error(f"Error querying Ollama: {str(e)}")
            return f"AI analysis failed: {str(e)}"
    
    async def analyze_vm_performance(self, vm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze VM performance and provide recommendations."""
        try:
            prompt = f"""
            As a Proxmox VE expert, analyze the following VM performance data and provide recommendations:

            VM Information:
            - VMID: {vm_data.get('vmid')}
            - Name: {vm_data.get('name')}
            - Status: {vm_data.get('status')}
            - Memory: {vm_data.get('mem', 0)} / {vm_data.get('maxmem', 0)} bytes
            - CPU Usage: {vm_data.get('cpu', 0)} / {vm_data.get('maxcpu', 0)} cores
            - Uptime: {vm_data.get('uptime', 0)} seconds
            - Node: {vm_data.get('node')}

            Please provide:
            1. Performance assessment (Good/Warning/Critical)
            2. Specific recommendations for optimization
            3. Resource allocation suggestions
            4. Potential issues to monitor
            5. Best practices for this VM configuration

            Format your response as structured recommendations.
            """
            
            ai_response = await self._query_ollama(prompt, vm_data)
            
            # Calculate performance metrics
            memory_usage = 0
            cpu_usage = 0
            
            if vm_data.get('maxmem', 0) > 0:
                memory_usage = (vm_data.get('mem', 0) / vm_data.get('maxmem', 0)) * 100
            
            if vm_data.get('maxcpu', 0) > 0:
                cpu_usage = (vm_data.get('cpu', 0) / vm_data.get('maxcpu', 0)) * 100
            
            # Determine performance status
            status = "Good"
            if memory_usage > 90 or cpu_usage > 90:
                status = "Critical"
            elif memory_usage > 75 or cpu_usage > 75:
                status = "Warning"
            
            return {
                "vmid": vm_data.get('vmid'),
                "analysis_timestamp": datetime.now().isoformat(),
                "performance_status": status,
                "metrics": {
                    "memory_usage_percent": round(memory_usage, 2),
                    "cpu_usage_percent": round(cpu_usage, 2),
                    "uptime_hours": round(vm_data.get('uptime', 0) / 3600, 2)
                },
                "ai_recommendations": ai_response,
                "automated_suggestions": self._generate_automated_suggestions(vm_data, memory_usage, cpu_usage)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing VM performance: {str(e)}")
            raise ProxmoxMCPException(f"VM performance analysis failed: {str(e)}")
    
    async def analyze_container_performance(self, container_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze LXC container performance and provide recommendations."""
        try:
            prompt = f"""
            As a Proxmox VE expert, analyze the following LXC container performance data:

            Container Information:
            - VMID: {container_data.get('vmid')}
            - Name: {container_data.get('name')}
            - Status: {container_data.get('status')}
            - Memory: {container_data.get('mem', 0)} / {container_data.get('maxmem', 0)} bytes
            - Swap: {container_data.get('swap_used', 0)} / {container_data.get('maxswap', 0)} bytes
            - CPU Usage: {container_data.get('cpu', 0)} / {container_data.get('maxcpu', 0)} cores
            - Uptime: {container_data.get('uptime', 0)} seconds
            - Node: {container_data.get('node')}

            Please provide:
            1. Container performance assessment
            2. Resource optimization recommendations
            3. Security considerations for LXC containers
            4. Scaling suggestions
            5. Best practices for container management

            Focus on LXC-specific optimizations and considerations.
            """
            
            ai_response = await self._query_ollama(prompt, container_data)
            
            # Calculate performance metrics
            memory_usage = 0
            swap_usage = 0
            cpu_usage = 0
            
            if container_data.get('maxmem', 0) > 0:
                memory_usage = (container_data.get('mem', 0) / container_data.get('maxmem', 0)) * 100
            
            if container_data.get('maxswap', 0) > 0:
                swap_usage = (container_data.get('swap_used', 0) / container_data.get('maxswap', 0)) * 100
            
            if container_data.get('maxcpu', 0) > 0:
                cpu_usage = (container_data.get('cpu', 0) / container_data.get('maxcpu', 0)) * 100
            
            # Determine performance status
            status = "Good"
            if memory_usage > 90 or cpu_usage > 90 or swap_usage > 50:
                status = "Critical"
            elif memory_usage > 75 or cpu_usage > 75 or swap_usage > 25:
                status = "Warning"
            
            return {
                "vmid": container_data.get('vmid'),
                "analysis_timestamp": datetime.now().isoformat(),
                "performance_status": status,
                "metrics": {
                    "memory_usage_percent": round(memory_usage, 2),
                    "swap_usage_percent": round(swap_usage, 2),
                    "cpu_usage_percent": round(cpu_usage, 2),
                    "uptime_hours": round(container_data.get('uptime', 0) / 3600, 2)
                },
                "ai_recommendations": ai_response,
                "automated_suggestions": self._generate_container_suggestions(container_data, memory_usage, cpu_usage, swap_usage)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing container performance: {str(e)}")
            raise ProxmoxMCPException(f"Container performance analysis failed: {str(e)}")
    
    async def analyze_cluster_health(self, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cluster health and provide recommendations."""
        try:
            prompt = f"""
            As a Proxmox VE cluster expert, analyze the following cluster health data:

            Cluster Information:
            - Name: {cluster_data.get('cluster', {}).get('name')}
            - Quorate: {cluster_data.get('cluster', {}).get('quorate')}
            - Total Nodes: {cluster_data.get('cluster', {}).get('nodes')}
            - Online Nodes: {len([n for n in cluster_data.get('nodes', []) if n.get('online')])}
            - Node Details: {json.dumps(cluster_data.get('nodes', []), indent=2)}

            Please provide:
            1. Cluster health assessment (Healthy/Warning/Critical)
            2. High availability recommendations
            3. Load balancing suggestions
            4. Potential single points of failure
            5. Scaling and capacity planning advice
            6. Maintenance scheduling recommendations

            Focus on cluster-specific best practices and potential issues.
            """
            
            ai_response = await self._query_ollama(prompt, cluster_data)
            
            # Calculate cluster metrics
            total_nodes = len(cluster_data.get('nodes', []))
            online_nodes = len([n for n in cluster_data.get('nodes', []) if n.get('online')])
            quorate = cluster_data.get('cluster', {}).get('quorate', 0)
            
            # Determine cluster health
            health_status = "Healthy"
            if not quorate or online_nodes < total_nodes * 0.5:
                health_status = "Critical"
            elif online_nodes < total_nodes * 0.8:
                health_status = "Warning"
            
            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "cluster_health": health_status,
                "metrics": {
                    "total_nodes": total_nodes,
                    "online_nodes": online_nodes,
                    "offline_nodes": total_nodes - online_nodes,
                    "quorate": bool(quorate),
                    "availability_percent": round((online_nodes / total_nodes * 100) if total_nodes > 0 else 0, 2)
                },
                "ai_recommendations": ai_response,
                "automated_suggestions": self._generate_cluster_suggestions(cluster_data, health_status)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing cluster health: {str(e)}")
            raise ProxmoxMCPException(f"Cluster health analysis failed: {str(e)}")
    
    async def analyze_storage_usage(self, storage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze storage usage and provide recommendations."""
        try:
            prompt = f"""
            As a Proxmox VE storage expert, analyze the following storage usage data:

            Storage Summary:
            - Total Storages: {storage_data.get('total_storages')}
            - Total Space: {storage_data.get('total_space')} bytes
            - Used Space: {storage_data.get('used_space')} bytes
            - Available Space: {storage_data.get('available_space')} bytes
            - Usage Percentage: {storage_data.get('usage_percentage', 0)}%
            - Storage Types: {json.dumps(storage_data.get('storages_by_type', {}), indent=2)}

            Please provide:
            1. Storage health assessment
            2. Capacity planning recommendations
            3. Performance optimization suggestions
            4. Backup strategy advice
            5. Storage type recommendations for different use cases
            6. Cleanup and maintenance suggestions

            Focus on storage best practices and optimization strategies.
            """
            
            ai_response = await self._query_ollama(prompt, storage_data)
            
            usage_percent = storage_data.get('usage_percentage', 0)
            
            # Determine storage health
            health_status = "Good"
            if usage_percent > 90:
                health_status = "Critical"
            elif usage_percent > 80:
                health_status = "Warning"
            
            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "storage_health": health_status,
                "metrics": {
                    "usage_percentage": round(usage_percent, 2),
                    "total_space_gb": round(storage_data.get('total_space', 0) / (1024**3), 2),
                    "used_space_gb": round(storage_data.get('used_space', 0) / (1024**3), 2),
                    "available_space_gb": round(storage_data.get('available_space', 0) / (1024**3), 2),
                    "total_storages": storage_data.get('total_storages', 0)
                },
                "ai_recommendations": ai_response,
                "automated_suggestions": self._generate_storage_suggestions(storage_data, usage_percent)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing storage usage: {str(e)}")
            raise ProxmoxMCPException(f"Storage usage analysis failed: {str(e)}")
    
    async def suggest_resource_sizing(self, workload_type: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest optimal resource sizing for a workload."""
        try:
            prompt = f"""
            As a Proxmox VE resource planning expert, suggest optimal resource sizing for:

            Workload Type: {workload_type}
            Requirements: {json.dumps(requirements, indent=2)}

            Please provide:
            1. Recommended CPU allocation (cores)
            2. Recommended memory allocation (GB)
            3. Recommended storage size and type
            4. Network configuration suggestions
            5. Performance expectations
            6. Scaling considerations
            7. Cost optimization tips

            Consider both VM and LXC container options where appropriate.
            """
            
            ai_response = await self._query_ollama(prompt, {"workload_type": workload_type, "requirements": requirements})
            
            # Generate basic sizing recommendations based on workload type
            base_recommendations = self._get_base_sizing_recommendations(workload_type, requirements)
            
            return {
                "workload_type": workload_type,
                "analysis_timestamp": datetime.now().isoformat(),
                "base_recommendations": base_recommendations,
                "ai_recommendations": ai_response,
                "considerations": self._get_sizing_considerations(workload_type)
            }
            
        except Exception as e:
            logger.error(f"Error generating resource sizing suggestions: {str(e)}")
            raise ProxmoxMCPException(f"Resource sizing analysis failed: {str(e)}")
    
    async def troubleshoot_issue(self, issue_description: str, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide troubleshooting assistance for Proxmox issues."""
        try:
            prompt = f"""
            As a Proxmox VE troubleshooting expert, help diagnose and resolve this issue:

            Issue Description: {issue_description}
            System Data: {json.dumps(system_data, indent=2)}

            Please provide:
            1. Likely root causes
            2. Step-by-step troubleshooting procedure
            3. Commands to run for diagnosis
            4. Potential solutions
            5. Prevention strategies
            6. When to escalate to support

            Focus on practical, actionable troubleshooting steps.
            """
            
            ai_response = await self._query_ollama(prompt, {"issue": issue_description, "system": system_data})
            
            return {
                "issue_description": issue_description,
                "analysis_timestamp": datetime.now().isoformat(),
                "ai_troubleshooting": ai_response,
                "common_solutions": self._get_common_solutions(issue_description),
                "diagnostic_commands": self._get_diagnostic_commands(issue_description)
            }
            
        except Exception as e:
            logger.error(f"Error generating troubleshooting assistance: {str(e)}")
            raise ProxmoxMCPException(f"Troubleshooting analysis failed: {str(e)}")
    
    def _generate_automated_suggestions(self, vm_data: Dict[str, Any], memory_usage: float, cpu_usage: float) -> List[str]:
        """Generate automated suggestions based on VM metrics."""
        suggestions = []
        
        if memory_usage > 90:
            suggestions.append("Critical: Memory usage is very high. Consider increasing memory allocation or optimizing applications.")
        elif memory_usage > 75:
            suggestions.append("Warning: Memory usage is high. Monitor for potential memory pressure.")
        
        if cpu_usage > 90:
            suggestions.append("Critical: CPU usage is very high. Consider adding more CPU cores or optimizing workload.")
        elif cpu_usage > 75:
            suggestions.append("Warning: CPU usage is high. Monitor for performance bottlenecks.")
        
        if vm_data.get('uptime', 0) > 365 * 24 * 3600:  # More than a year
            suggestions.append("Info: VM has been running for over a year. Consider scheduling maintenance reboot.")
        
        if memory_usage < 25 and cpu_usage < 25:
            suggestions.append("Optimization: VM appears underutilized. Consider reducing resource allocation.")
        
        return suggestions
    
    def _generate_container_suggestions(self, container_data: Dict[str, Any], memory_usage: float, cpu_usage: float, swap_usage: float) -> List[str]:
        """Generate automated suggestions based on container metrics."""
        suggestions = []
        
        if swap_usage > 50:
            suggestions.append("Critical: High swap usage detected. Consider increasing memory allocation.")
        elif swap_usage > 25:
            suggestions.append("Warning: Moderate swap usage. Monitor memory pressure.")
        
        if memory_usage > 90:
            suggestions.append("Critical: Memory usage is very high for container. Increase memory limit.")
        elif memory_usage > 75:
            suggestions.append("Warning: High memory usage. Consider memory optimization.")
        
        if cpu_usage > 90:
            suggestions.append("Critical: CPU usage is very high. Consider increasing CPU allocation.")
        
        if memory_usage < 20 and cpu_usage < 20:
            suggestions.append("Optimization: Container appears underutilized. Consider resource reduction.")
        
        suggestions.append("Security: Ensure container is running in unprivileged mode for better security.")
        
        return suggestions
    
    def _generate_cluster_suggestions(self, cluster_data: Dict[str, Any], health_status: str) -> List[str]:
        """Generate automated suggestions based on cluster health."""
        suggestions = []
        
        if health_status == "Critical":
            suggestions.append("Critical: Cluster health is compromised. Investigate offline nodes immediately.")
            suggestions.append("Action: Check network connectivity and node status.")
        
        total_nodes = len(cluster_data.get('nodes', []))
        if total_nodes < 3:
            suggestions.append("Recommendation: Consider adding more nodes for better HA and quorum.")
        
        if not cluster_data.get('cluster', {}).get('quorate'):
            suggestions.append("Critical: Cluster has lost quorum. Investigate node connectivity.")
        
        suggestions.append("Best Practice: Ensure regular cluster configuration backups.")
        suggestions.append("Monitoring: Set up alerts for node status changes.")
        
        return suggestions
    
    def _generate_storage_suggestions(self, storage_data: Dict[str, Any], usage_percent: float) -> List[str]:
        """Generate automated suggestions based on storage usage."""
        suggestions = []
        
        if usage_percent > 90:
            suggestions.append("Critical: Storage usage is very high. Add more storage or clean up immediately.")
        elif usage_percent > 80:
            suggestions.append("Warning: Storage usage is high. Plan for capacity expansion.")
        
        if usage_percent > 75:
            suggestions.append("Action: Review and clean up old backups and unused volumes.")
            suggestions.append("Monitoring: Set up storage usage alerts.")
        
        suggestions.append("Best Practice: Implement regular backup cleanup policies.")
        suggestions.append("Optimization: Consider storage tiering for better performance.")
        
        return suggestions
    
    def _get_base_sizing_recommendations(self, workload_type: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Get base sizing recommendations for different workload types."""
        recommendations = {
            "web_server": {
                "cpu_cores": 2,
                "memory_gb": 4,
                "storage_gb": 50,
                "storage_type": "SSD",
                "container_suitable": True
            },
            "database": {
                "cpu_cores": 4,
                "memory_gb": 8,
                "storage_gb": 100,
                "storage_type": "NVMe SSD",
                "container_suitable": False
            },
            "development": {
                "cpu_cores": 2,
                "memory_gb": 4,
                "storage_gb": 30,
                "storage_type": "SSD",
                "container_suitable": True
            },
            "production": {
                "cpu_cores": 4,
                "memory_gb": 8,
                "storage_gb": 100,
                "storage_type": "SSD",
                "container_suitable": False
            }
        }
        
        return recommendations.get(workload_type.lower(), {
            "cpu_cores": 2,
            "memory_gb": 4,
            "storage_gb": 50,
            "storage_type": "SSD",
            "container_suitable": True
        })
    
    def _get_sizing_considerations(self, workload_type: str) -> List[str]:
        """Get sizing considerations for workload types."""
        considerations = [
            "Consider future growth and scaling requirements",
            "Factor in backup and snapshot storage needs",
            "Account for OS and application overhead",
            "Plan for peak usage scenarios"
        ]
        
        if workload_type.lower() == "database":
            considerations.extend([
                "Database workloads benefit from dedicated storage",
                "Consider memory requirements for buffer pools",
                "Plan for transaction log storage"
            ])
        elif workload_type.lower() == "web_server":
            considerations.extend([
                "Web servers can often use containers for better density",
                "Consider load balancing for high availability",
                "Plan for static content storage"
            ])
        
        return considerations
    
    def _get_common_solutions(self, issue_description: str) -> List[str]:
        """Get common solutions for typical issues."""
        issue_lower = issue_description.lower()
        
        if "network" in issue_lower or "connectivity" in issue_lower:
            return [
                "Check network interface configuration",
                "Verify firewall rules",
                "Test network connectivity between nodes",
                "Check DNS resolution"
            ]
        elif "storage" in issue_lower or "disk" in issue_lower:
            return [
                "Check storage mount points",
                "Verify storage permissions",
                "Check disk space availability",
                "Review storage configuration"
            ]
        elif "performance" in issue_lower or "slow" in issue_lower:
            return [
                "Check resource utilization",
                "Review VM/container resource allocation",
                "Analyze storage I/O performance",
                "Check for resource contention"
            ]
        else:
            return [
                "Check system logs for error messages",
                "Verify service status",
                "Review recent configuration changes",
                "Check resource availability"
            ]
    
    def _get_diagnostic_commands(self, issue_description: str) -> List[str]:
        """Get diagnostic commands for common issues."""
        issue_lower = issue_description.lower()
        
        if "network" in issue_lower:
            return [
                "ip addr show",
                "ping <target>",
                "netstat -tuln",
                "iptables -L"
            ]
        elif "storage" in issue_lower:
            return [
                "df -h",
                "lsblk",
                "mount | grep <storage>",
                "iostat -x 1 5"
            ]
        elif "performance" in issue_lower:
            return [
                "top",
                "htop",
                "iotop",
                "free -h",
                "vmstat 1 5"
            ]
        else:
            return [
                "systemctl status",
                "journalctl -xe",
                "dmesg | tail",
                "ps aux"
            ]


# Global AI advisor instance
ai_advisor = ProxmoxAIAdvisor()
