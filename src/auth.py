
"""Authentication and authorization module for Proxmox MCP Server."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings
from .proxmox_client import proxmox_client

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ProxmoxAuthManager:
    """Manages Proxmox VE authentication and connections."""
    
    def __init__(self):
        self.client = proxmox_client
        self._connection_cache: Dict[str, Any] = {}
        
    async def connect(self) -> bool:
        """Establish connection to Proxmox VE."""
        try:
            success = await self.client.connect()
            if success:
                logger.info(f"Successfully connected to Proxmox VE: {settings.proxmox_host}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox VE: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from Proxmox VE."""
        try:
            await self.client.disconnect()
            logger.info("Disconnected from Proxmox VE")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
    
    async def validate_connection(self) -> bool:
        """Validate the current connection."""
        try:
            return await self.client.validate_connection()
                
        except Exception as e:
            logger.error(f"Connection validation failed: {str(e)}")
            return False
    
    def get_client(self):
        """Get the Proxmox client instance."""
        return self.client


class JWTManager:
    """Manages JWT tokens for API authentication."""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
            return payload
        except JWTError as e:
            logger.error(f"JWT verification failed: {str(e)}")
            return None


class RBACManager:
    """Role-Based Access Control manager for Proxmox operations."""
    
    ROLES = {
        "admin": [
            # VM operations
            "vm:create", "vm:delete", "vm:start", "vm:stop", "vm:clone", "vm:migrate",
            "vm:snapshot", "vm:config", "vm:monitor",
            
            # Container operations
            "lxc:create", "lxc:delete", "lxc:start", "lxc:stop", "lxc:clone",
            "lxc:snapshot", "lxc:config", "lxc:monitor", "lxc:exec",
            
            # Node operations
            "node:monitor", "node:configure", "node:reboot", "node:shutdown",
            "node:services", "node:tasks",
            
            # Cluster operations
            "cluster:monitor", "cluster:configure", "cluster:ha", "cluster:backup",
            
            # Storage operations
            "storage:create", "storage:delete", "storage:configure", "storage:monitor",
            "storage:upload", "storage:download",
            
            # Network operations
            "network:create", "network:delete", "network:configure", "network:monitor",
            "network:sdn", "network:firewall",
            
            # Backup operations
            "backup:create", "backup:restore", "backup:delete", "backup:schedule",
            "backup:monitor",
            
            # System operations
            "system:configure", "system:monitor", "system:logs"
        ],
        "operator": [
            # VM operations (limited)
            "vm:start", "vm:stop", "vm:clone", "vm:snapshot", "vm:monitor",
            
            # Container operations (limited)
            "lxc:start", "lxc:stop", "lxc:clone", "lxc:snapshot", "lxc:monitor",
            
            # Node operations (limited)
            "node:monitor", "node:tasks",
            
            # Cluster operations (limited)
            "cluster:monitor",
            
            # Storage operations (limited)
            "storage:monitor", "storage:upload",
            
            # Network operations (limited)
            "network:monitor",
            
            # Backup operations (limited)
            "backup:create", "backup:monitor",
            
            # System operations (limited)
            "system:monitor"
        ],
        "viewer": [
            # Read-only operations
            "vm:monitor", "lxc:monitor", "node:monitor", "cluster:monitor",
            "storage:monitor", "network:monitor", "backup:monitor", "system:monitor"
        ]
    }
    
    @classmethod
    def check_permission(cls, user_role: str, required_permission: str) -> bool:
        """Check if a user role has the required permission."""
        if not settings.enable_rbac:
            return True
        
        user_permissions = cls.ROLES.get(user_role, [])
        return required_permission in user_permissions
    
    @classmethod
    def get_user_permissions(cls, user_role: str) -> list:
        """Get all permissions for a user role."""
        return cls.ROLES.get(user_role, [])


# Global auth manager instance
auth_manager = ProxmoxAuthManager()
