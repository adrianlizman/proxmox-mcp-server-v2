
"""Configuration settings for Proxmox MCP Server."""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Proxmox connection settings
    proxmox_host: str = Field(..., env="PROXMOX_HOST")
    proxmox_username: str = Field(..., env="PROXMOX_USERNAME")
    proxmox_password: str = Field(..., env="PROXMOX_PASSWORD")
    proxmox_port: int = Field(8006, env="PROXMOX_PORT")
    proxmox_verify_ssl: bool = Field(False, env="PROXMOX_VERIFY_SSL")
    proxmox_timeout: int = Field(30, env="PROXMOX_TIMEOUT")
    
    # MCP Server settings
    mcp_server_host: str = Field("localhost", env="MCP_SERVER_HOST")
    mcp_server_port: int = Field(8080, env="MCP_SERVER_PORT")
    
    # Security settings
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(60, env="JWT_EXPIRE_MINUTES")
    enable_rbac: bool = Field(True, env="ENABLE_RBAC")
    
    # Logging settings
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(None, env="LOG_FILE")
    
    # AI Integration settings
    ollama_host: str = Field("http://localhost:11434", env="OLLAMA_HOST")
    ollama_model: str = Field("llama2", env="OLLAMA_MODEL")
    enable_ai_features: bool = Field(True, env="ENABLE_AI_FEATURES")
    
    # n8n Integration settings
    n8n_host: str = Field("http://localhost:5678", env="N8N_HOST")
    n8n_webhook_url: str = Field("http://localhost:5678/webhook", env="N8N_WEBHOOK_URL")
    enable_n8n_integration: bool = Field(True, env="ENABLE_N8N_INTEGRATION")
    
    # Performance settings
    max_concurrent_operations: int = Field(10, env="MAX_CONCURRENT_OPERATIONS")
    operation_timeout: int = Field(300, env="OPERATION_TIMEOUT")
    
    # Monitoring settings
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
