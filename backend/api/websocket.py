"""
api/websocket.py — WebSocket endpoint for real-time progress streaming.

Clients connect to ws://localhost:8765/ws/progress
The server pushes ProgressEvent JSON objects as operations run.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self) -> None:
        self._active: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._active.add(ws)
        logger.debug("WebSocket connected — total: %d", len(self._active))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._active.discard(ws)
        logger.debug("WebSocket disconnected — total: %d", len(self._active))

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all connected clients."""
        if not self._active:
            return

        dead: set[WebSocket] = set()
        async with self._lock:
            clients = set(self._active)

        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)

        async with self._lock:
            self._active -= dead

    async def send_to(self, ws: WebSocket, message: dict) -> None:
        """Send to a single client."""
        try:
            await ws.send_json(message)
        except Exception:
            await self.disconnect(ws)


# Singleton shared across all routes
ws_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, progress_queue: asyncio.Queue) -> None:
    """
    WebSocket handler.  Reads from shared progress_queue and pushes to client.
    Should be paired with a background task populating the queue.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            try:
                event = await asyncio.wait_for(progress_queue.get(), timeout=30)
                if event is None:
                    await websocket.send_json({"event": "done"})
                    break
                await websocket.send_json(
                    event.model_dump() if hasattr(event, "model_dump") else event
                )
            except asyncio.TimeoutError:
                # Send a heartbeat so the connection stays alive
                await websocket.send_json({"event": "heartbeat"})
    except WebSocketDisconnect:
        logger.debug("Client disconnected from WebSocket")
    finally:
        await ws_manager.disconnect(websocket)
