"""SSH Connection Management API - manage SSH connections for agent access."""

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_operator
from app.db.session import get_db
from app.models.user import User
from app.services.audit import log_action

logger = structlog.get_logger()
router = APIRouter()

# In-memory store for SSH connections (in production, use a dedicated model)
_ssh_connections: dict[str, dict] = {}
_ssh_logs: dict[str, list[dict]] = {}


@router.get("/")
async def list_ssh_connections(
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List all SSH connections."""
    items = list(_ssh_connections.values())
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(items)
    paged = items[skip : skip + limit]
    # Mask sensitive fields
    safe_items = []
    for conn in paged:
        safe = {k: v for k, v in conn.items() if k not in ("private_key", "password")}
        safe["has_key"] = bool(conn.get("private_key"))
        safe["has_password"] = bool(conn.get("password"))
        safe_items.append(safe)
    return {"items": safe_items, "total": total, "skip": skip, "limit": limit}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_ssh_connection(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Create a new SSH connection."""
    conn_id = str(uuid.uuid4())
    connection = {
        "id": conn_id,
        "name": data.get("name", "Unnamed Connection"),
        "host": data.get("host", ""),
        "port": data.get("port", 22),
        "username": data.get("username", ""),
        "password": data.get("password"),
        "private_key": data.get("private_key"),
        "auth_type": data.get("auth_type", "key"),  # key or password
        "description": data.get("description", ""),
        "tags": data.get("tags", []),
        "status": "untested",
        "created_by": str(user.id),
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _ssh_connections[conn_id] = connection

    await log_action(
        db,
        action="ssh_connection_created",
        resource_type="ssh_connection",
        actor_type="user",
        actor_id=user.id,
        details=f"SSH connection '{connection['name']}' created for {connection['host']}",
    )
    logger.info("ssh_connection_created", connection_id=conn_id, host=connection["host"])

    # Return without sensitive fields
    safe = {k: v for k, v in connection.items() if k not in ("private_key", "password")}
    return safe


@router.get("/{connection_id}")
async def get_ssh_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """Get SSH connection details (credentials masked)."""
    conn = _ssh_connections.get(connection_id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSH connection not found")

    safe = {k: v for k, v in conn.items() if k not in ("private_key", "password")}
    safe["has_key"] = bool(conn.get("private_key"))
    safe["has_password"] = bool(conn.get("password"))
    return safe


@router.put("/{connection_id}")
async def update_ssh_connection(
    connection_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Update an SSH connection."""
    conn = _ssh_connections.get(connection_id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSH connection not found")

    updatable = ["name", "host", "port", "username", "password", "private_key", "auth_type", "description", "tags"]
    for field in updatable:
        if field in data:
            conn[field] = data[field]
    conn["updated_at"] = datetime.now(UTC).isoformat()

    await log_action(
        db,
        action="ssh_connection_updated",
        resource_type="ssh_connection",
        resource_id=connection_id,
        actor_type="user",
        actor_id=user.id,
        details=f"SSH connection '{conn['name']}' updated",
    )
    logger.info("ssh_connection_updated", connection_id=connection_id)

    safe = {k: v for k, v in conn.items() if k not in ("private_key", "password")}
    return safe


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ssh_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> None:
    """Delete an SSH connection."""
    if connection_id not in _ssh_connections:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSH connection not found")

    conn = _ssh_connections.pop(connection_id)
    _ssh_logs.pop(connection_id, None)

    await log_action(
        db,
        action="ssh_connection_deleted",
        resource_type="ssh_connection",
        resource_id=connection_id,
        actor_type="user",
        actor_id=user.id,
        details=f"SSH connection '{conn['name']}' deleted",
    )
    logger.info("ssh_connection_deleted", connection_id=connection_id)


@router.post("/{connection_id}/test")
async def test_ssh_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Test an SSH connection."""
    conn = _ssh_connections.get(connection_id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSH connection not found")

    # Attempt connection test
    try:
        import asyncssh

        connect_kwargs: dict = {
            "host": conn["host"],
            "port": conn.get("port", 22),
            "username": conn["username"],
            "known_hosts": None,
        }
        if conn.get("private_key"):
            connect_kwargs["client_keys"] = [asyncssh.import_private_key(conn["private_key"])]
        elif conn.get("password"):
            connect_kwargs["password"] = conn["password"]

        async with asyncssh.connect(**connect_kwargs) as ssh_conn:
            result = await ssh_conn.run("echo ok", check=True)
            output = result.stdout.strip()

        conn["status"] = "connected"
        conn["last_tested_at"] = datetime.now(UTC).isoformat()
        logger.info("ssh_connection_test_success", connection_id=connection_id)
        return {"status": "success", "message": "Connection successful", "output": output}

    except ImportError:
        # asyncssh not installed, simulate test
        conn["status"] = "untested"
        logger.warning("ssh_test_asyncssh_not_installed")
        return {"status": "skipped", "message": "asyncssh not installed; cannot test connection"}

    except Exception as exc:
        conn["status"] = "failed"
        conn["last_tested_at"] = datetime.now(UTC).isoformat()
        logger.error("ssh_connection_test_failed", connection_id=connection_id, error=str(exc))
        return {"status": "failed", "message": str(exc)}


@router.get("/{connection_id}/logs")
async def get_ssh_logs(
    connection_id: str,
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Get session logs for an SSH connection."""
    if connection_id not in _ssh_connections:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSH connection not found")

    logs = _ssh_logs.get(connection_id, [])
    total = len(logs)
    items = logs[skip : skip + limit]
    return {"items": items, "total": total, "skip": skip, "limit": limit}
