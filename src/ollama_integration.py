
"""Ollama integration module for VMware MCP Server."""

import logging
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
import httpx
from .config import settings
from .exceptions import VMwareMCPException

logger = logging.getLogger(__name__)


class OllamaIntegration:
    """Handles integration with Ollama for AI-powered VMware operations."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.ollama_timeout)
        self.base_url = settings.ollama_host
        self.model = settings.ollama_model
        self.enabled = settings.enable_ollama
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available."""
        if not self.enabled:
            return False
        
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate AI response for VMware operations."""
        if not self.enabled:
            return {"error": "Ollama integration is disabled"}
        
        try:
            # Enhance prompt with VMware context
            enhanced_prompt = self._enhance_prompt_with_context(prompt, context)
            
            payload = {
                "model": self.model,
                "prompt": enhanced_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": True,
                "response": result.get("response", ""),
                "model": self.model,
                "context": result.get("context", [])
            }
            
        except Exception as e:
            logger.error(f"Failed to generate Ollama response: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stream_response(self, prompt: str, context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """Stream AI response for real-time interaction."""
        if not self.enabled:
            yield "Ollama integration is disabled"
            return
        
        try:
            enhanced_prompt = self._enhance_prompt_with_context(prompt, context)
            
            payload = {
                "model": self.model,
                "prompt": enhanced_prompt,
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            }
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            import json
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Failed to stream Ollama response: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def analyze_vm_performance(self, vm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze VM performance data using AI."""
        prompt = f"""
        Analyze the following VMware VM performance data and provide insights:
        
        VM Name: {vm_data.get('name', 'Unknown')}
        Power State: {vm_data.get('power_state', 'Unknown')}
        CPU Usage: {vm_data.get('cpu_usage_mhz', 0)} MHz
        Memory Usage: {vm_data.get('memory_usage_mb', 0)} MB
        CPU Utilization: {vm_data.get('cpu_utilization_percent', 0)}%
        Memory Utilization: {vm_data.get('memory_utilization_percent', 0)}%
        
        Please provide:
        1. Performance assessment (Good/Warning/Critical)
        2. Potential issues or bottlenecks
        3. Optimization recommendations
        4. Suggested actions
        
        Format your response as structured analysis.
        """
        
        return await self.generate_response(prompt, {"type": "performance_analysis", "vm_data": vm_data})
    
    async def suggest_vm_sizing(self, workload_description: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest VM sizing based on workload requirements."""
        prompt = f"""
        Based on the following workload description and requirements, suggest optimal VM sizing:
        
        Workload: {workload_description}
        Requirements: {requirements}
        
        Please suggest:
        1. CPU cores needed
        2. Memory (GB) required
        3. Storage requirements
        4. Network considerations
        5. High availability recommendations
        
        Provide reasoning for each recommendation.
        """
        
        return await self.generate_response(prompt, {"type": "vm_sizing", "workload": workload_description})
    
    async def troubleshoot_issue(self, issue_description: str, vm_context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide troubleshooting guidance for VMware issues."""
        prompt = f"""
        Help troubleshoot the following VMware issue:
        
        Issue: {issue_description}
        VM Context: {vm_context}
        
        Please provide:
        1. Possible root causes
        2. Diagnostic steps to verify the issue
        3. Step-by-step resolution procedures
        4. Prevention measures
        
        Focus on practical, actionable solutions.
        """
        
        return await self.generate_response(prompt, {"type": "troubleshooting", "issue": issue_description})
    
    async def generate_maintenance_plan(self, hosts: List[Dict[str, Any]], 
                                      maintenance_type: str) -> Dict[str, Any]:
        """Generate a maintenance plan for VMware infrastructure."""
        prompt = f"""
        Generate a maintenance plan for the following VMware infrastructure:
        
        Maintenance Type: {maintenance_type}
        Hosts: {len(hosts)} hosts
        Host Details: {hosts}
        
        Please provide:
        1. Pre-maintenance checklist
        2. Step-by-step maintenance procedure
        3. Rollback plan
        4. Post-maintenance verification steps
        5. Estimated downtime
        6. Risk assessment
        
        Ensure minimal service disruption.
        """
        
        return await self.generate_response(prompt, {"type": "maintenance_plan", "hosts": hosts})
    
    async def explain_vmware_concept(self, concept: str) -> Dict[str, Any]:
        """Explain VMware concepts and technologies."""
        prompt = f"""
        Explain the VMware concept: {concept}
        
        Please provide:
        1. Clear definition
        2. How it works
        3. Use cases and benefits
        4. Best practices
        5. Common configurations
        6. Related technologies
        
        Make it accessible for both beginners and experienced administrators.
        """
        
        return await self.generate_response(prompt, {"type": "concept_explanation", "concept": concept})
    
    def _enhance_prompt_with_context(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Enhance prompt with VMware-specific context."""
        base_context = """
        You are an expert VMware vSphere administrator with deep knowledge of:
        - VMware vCenter Server and ESXi hosts
        - Virtual machine management and optimization
        - Resource allocation and performance tuning
        - Storage and networking in virtualized environments
        - High availability and disaster recovery
        - Troubleshooting and best practices
        
        Provide accurate, practical, and actionable advice based on VMware best practices.
        """
        
        if context:
            context_str = f"\nAdditional Context: {context}\n"
        else:
            context_str = ""
        
        return f"{base_context}{context_str}\nUser Query: {prompt}"
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global Ollama integration instance
ollama_integration = OllamaIntegration()
