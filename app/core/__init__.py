"""Core module for MCP Server."""

from .instances import Instance, InstanceManager, InstanceClient
from .security import (
    SecurityMode,
    requires_mode,
    check_action,
    get_security_mode,
    set_security_mode,
    is_action_allowed,
)
from .exceptions import (
    ModusBIError,
    AuthenticationError,
    APIError,
    NotFoundError,
    ValidationError,
    SecurityError,
    InstanceError,
)

__all__ = [
    # Instances
    "Instance",
    "InstanceManager",
    "InstanceClient",
    # Security
    "SecurityMode",
    "requires_mode",
    "check_action",
    "get_security_mode",
    "set_security_mode",
    "is_action_allowed",
    # Exceptions
    "ModusBIError",
    "AuthenticationError",
    "APIError",
    "NotFoundError",
    "ValidationError",
    "SecurityError",
    "InstanceError",
]
