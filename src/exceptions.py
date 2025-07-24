
"""Custom exceptions for Proxmox MCP Server."""


class ProxmoxMCPException(Exception):
    """Base exception for Proxmox MCP Server."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or "PROXMOX_MCP_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class ProxmoxConnectionException(ProxmoxMCPException):
    """Exception raised when connection to Proxmox fails."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "PROXMOX_CONNECTION_ERROR", details)


class ProxmoxAuthenticationException(ProxmoxMCPException):
    """Exception raised when authentication fails."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "PROXMOX_AUTH_ERROR", details)


class ProxmoxOperationException(ProxmoxMCPException):
    """Exception raised when a Proxmox operation fails."""
    
    def __init__(self, message: str, operation: str = None, details: dict = None):
        self.operation = operation
        error_details = details or {}
        if operation:
            error_details['operation'] = operation
        super().__init__(message, "PROXMOX_OPERATION_ERROR", error_details)


class ProxmoxValidationException(ProxmoxMCPException):
    """Exception raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None, details: dict = None):
        self.field = field
        error_details = details or {}
        if field:
            error_details['field'] = field
        super().__init__(message, "PROXMOX_VALIDATION_ERROR", error_details)


class ProxmoxPermissionException(ProxmoxMCPException):
    """Exception raised when user lacks required permissions."""
    
    def __init__(self, message: str, required_permission: str = None, details: dict = None):
        self.required_permission = required_permission
        error_details = details or {}
        if required_permission:
            error_details['required_permission'] = required_permission
        super().__init__(message, "PROXMOX_PERMISSION_ERROR", error_details)


class ProxmoxTimeoutException(ProxmoxMCPException):
    """Exception raised when an operation times out."""
    
    def __init__(self, message: str, timeout: int = None, details: dict = None):
        self.timeout = timeout
        error_details = details or {}
        if timeout:
            error_details['timeout'] = timeout
        super().__init__(message, "PROXMOX_TIMEOUT_ERROR", error_details)


class ProxmoxResourceNotFoundException(ProxmoxMCPException):
    """Exception raised when a requested resource is not found."""
    
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None, details: dict = None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        error_details = details or {}
        if resource_type:
            error_details['resource_type'] = resource_type
        if resource_id:
            error_details['resource_id'] = resource_id
        super().__init__(message, "PROXMOX_RESOURCE_NOT_FOUND", error_details)
