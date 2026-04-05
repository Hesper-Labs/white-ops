ROLES = {
    "admin": {
        "description": "Full system access",
        "permissions": [
            "agents:create", "agents:read", "agents:update", "agents:delete",
            "tasks:create", "tasks:read", "tasks:update", "tasks:delete",
            "workflows:create", "workflows:read", "workflows:update", "workflows:delete",
            "users:create", "users:read", "users:update", "users:delete",
            "workers:read", "workers:approve", "workers:remove",
            "files:read", "files:upload", "files:delete",
            "messages:read",
            "settings:read", "settings:update",
            "audit:read",
        ],
    },
    "operator": {
        "description": "Can manage agents and tasks",
        "permissions": [
            "agents:create", "agents:read", "agents:update",
            "tasks:create", "tasks:read", "tasks:update",
            "workflows:create", "workflows:read", "workflows:update",
            "files:read", "files:upload",
            "messages:read",
            "workers:read",
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
        ],
    },
}


def has_permission(role: str, permission: str) -> bool:
    role_def = ROLES.get(role)
    if not role_def:
        return False
    return permission in role_def["permissions"]
