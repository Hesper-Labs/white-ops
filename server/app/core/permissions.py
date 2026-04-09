"""Role-based access control (RBAC): roles, permissions, and helper functions."""

ROLES: dict[str, dict] = {
    "admin": {
        "description": "Full system access",
        "permissions": [
            # Agents
            "agents:create", "agents:read", "agents:update", "agents:delete",
            # Tasks
            "tasks:create", "tasks:read", "tasks:update", "tasks:delete",
            # Workflows
            "workflows:create", "workflows:read", "workflows:update", "workflows:delete",
            # Users
            "users:create", "users:read", "users:update", "users:delete",
            # Workers
            "workers:read", "workers:approve", "workers:remove",
            # Files
            "files:read", "files:upload", "files:delete",
            # Messages
            "messages:read",
            # Settings
            "settings:read", "settings:update",
            # Audit
            "audit:read",
            # Secrets management
            "secrets:create", "secrets:read", "secrets:update", "secrets:delete",
            # SSH
            "ssh:create", "ssh:read", "ssh:update", "ssh:delete", "ssh:connect",
            # Approvals
            "approvals:create", "approvals:read", "approvals:approve", "approvals:reject",
            # Triggers
            "triggers:create", "triggers:read", "triggers:update", "triggers:delete",
            # Notifications
            "notifications:read", "notifications:update",
            # Cost management
            "cost:read", "cost:manage",
            # Security settings
            "security:read", "security:update",
            # Memory / context
            "memory:read", "memory:delete",
            # Circuit breakers
            "circuit_breakers:read", "circuit_breakers:manage",
        ],
    },
    "operator": {
        "description": "Can manage agents, tasks, and operational resources",
        "permissions": [
            # Agents
            "agents:create", "agents:read", "agents:update",
            # Tasks
            "tasks:create", "tasks:read", "tasks:update",
            # Workflows
            "workflows:create", "workflows:read", "workflows:update",
            # Files
            "files:read", "files:upload",
            # Messages
            "messages:read",
            # Workers
            "workers:read",
            # Secrets (read-only)
            "secrets:read",
            # SSH (no delete)
            "ssh:create", "ssh:read", "ssh:update", "ssh:connect",
            # Approvals
            "approvals:create", "approvals:read", "approvals:approve", "approvals:reject",
            # Triggers
            "triggers:create", "triggers:read", "triggers:update",
            # Notifications
            "notifications:read", "notifications:update",
            # Cost (read-only)
            "cost:read",
            # Memory
            "memory:read",
            # Circuit breakers (read-only)
            "circuit_breakers:read",
        ],
    },
    "viewer": {
        "description": "Read-only access to dashboards and reports",
        "permissions": [
            "agents:read",
            "tasks:read",
            "workflows:read",
            "files:read",
            "messages:read",
            "workers:read",
            "secrets:read",
            "ssh:read",
            "approvals:read",
            "triggers:read",
            "notifications:read",
            "cost:read",
            "memory:read",
            "circuit_breakers:read",
        ],
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    role_def = ROLES.get(role)
    if not role_def:
        return False
    return permission in role_def["permissions"]


def get_role_permissions(role: str) -> list[str]:
    """Return the list of permissions for a given role, or empty list if unknown."""
    role_def = ROLES.get(role)
    if not role_def:
        return []
    return list(role_def["permissions"])


def check_resource_access(user_role: str, resource: str, action: str) -> bool:
    """Check if a role can perform an action on a resource.

    Args:
        user_role: The user's role (e.g. "admin", "operator", "viewer").
        resource: The resource name (e.g. "secrets", "agents").
        action: The action (e.g. "create", "read", "delete").

    Returns:
        True if the role has the "resource:action" permission.
    """
    return has_permission(user_role, f"{resource}:{action}")
