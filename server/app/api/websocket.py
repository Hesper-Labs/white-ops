"""WebSocket hub for real-time event broadcasting."""

import json
from collections.abc import MutableSet
from enum import Enum

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = structlog.get_logger()
router = APIRouter()


class EventType(str, Enum):
    AGENT_STATUS = "agent.status"
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    WORKER_ONLINE = "worker.online"
    WORKER_OFFLINE = "worker.offline"
    MESSAGE_NEW = "message.new"
    NOTIFICATION = "notification"
    SYSTEM_ALERT = "system.alert"


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: MutableSet[WebSocket] = set()
        self._subscriptions: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("ws_connected", total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        for subs in self._subscriptions.values():
            subs.discard(websocket)
        logger.info("ws_disconnected", total=len(self.active_connections))

    def subscribe(self, websocket: WebSocket, event_type: str) -> None:
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = set()
        self._subscriptions[event_type].add(websocket)

    async def broadcast(self, event_type: str, data: dict) -> None:
        """Broadcast event to all connected clients."""
        message = json.dumps({"type": event_type, "data": data})
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)
        self.active_connections -= disconnected

    async def send_to_subscribed(self, event_type: str, data: dict) -> None:
        """Send event only to clients subscribed to this event type."""
        subscribers = self._subscriptions.get(event_type, set())
        if not subscribers:
            return await self.broadcast(event_type, data)

        message = json.dumps({"type": event_type, "data": data})
        disconnected = set()
        for connection in subscribers:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)
        subscribers -= disconnected

    async def notify(self, title: str, message: str, level: str = "info") -> None:
        """Send a notification to all clients."""
        await self.broadcast(EventType.NOTIFICATION, {
            "title": title,
            "message": message,
            "level": level,
        })


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON"},
                }))
                continue

            msg_type = message.get("type", "")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif msg_type == "subscribe":
                event = message.get("event", "")
                if event:
                    manager.subscribe(websocket, event)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "data": {"event": event},
                    }))
            else:
                logger.debug("ws_unknown_message", type=msg_type)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("ws_error", error=str(e))
        manager.disconnect(websocket)
