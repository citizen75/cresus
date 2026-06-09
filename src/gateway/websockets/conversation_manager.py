"""WebSocket manager for conversation real-time updates."""

import json
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional
from collections import defaultdict
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConversationWebSocketManager:
    """Manages WebSocket connections for conversations with file monitoring."""

    def __init__(self):
        """Initialize the manager."""
        self.connections: Dict[str, Set[WebSocket]] = defaultdict(set)  # {portfolio_name: {websockets}}
        self.file_hashes: Dict[str, str] = {}  # Track file changes
        self.db_path = Path.home() / ".cresus" / "db"

    def register(self, portfolio_name: str, websocket: WebSocket) -> None:
        """Register a WebSocket connection for a portfolio."""
        self.connections[portfolio_name].add(websocket)
        logger.debug(f"WebSocket registered for portfolio: {portfolio_name}")

    def unregister(self, portfolio_name: str, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        self.connections[portfolio_name].discard(websocket)
        if not self.connections[portfolio_name]:
            del self.connections[portfolio_name]
        logger.debug(f"WebSocket unregistered for portfolio: {portfolio_name}")

    async def broadcast(self, portfolio_name: str, message: dict) -> None:
        """Broadcast message to all connected clients for a portfolio."""
        disconnected = set()
        for websocket in self.connections[portfolio_name]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {portfolio_name}: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.unregister(portfolio_name, ws)

    def get_history_file(self) -> Path:
        """Get path to unified conversation history file."""
        return self.db_path / "conversations" / "history.json"

    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """Get hash of file contents to detect changes."""
        if not file_path.exists():
            return None
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None

    async def check_for_updates(self, portfolio_name: str, source_filter: Optional[str] = None) -> None:
        """Check if conversation file has changed and broadcast new messages."""
        from tools.conversation import ConversationManager

        history_file = self.get_history_file()
        current_hash = self._get_file_hash(history_file)

        if portfolio_name not in self.file_hashes or current_hash != self.file_hashes.get(portfolio_name):
            self.file_hashes[portfolio_name] = current_hash or ""

            # File changed, read and broadcast latest message
            try:
                manager = ConversationManager(portfolio_name)
                messages = manager.get_history_dicts(
                    source_filter=source_filter,
                    portfolio_filter=portfolio_name
                )

                if messages:
                    latest = messages[-1]
                    await self.broadcast(portfolio_name, {
                        "type": "message",
                        "data": latest
                    })
            except Exception as e:
                logger.error(f"Error reading conversation history: {e}")


# Global manager instance
_manager: Optional[ConversationWebSocketManager] = None


def get_conversation_websocket_manager() -> ConversationWebSocketManager:
    """Get or create the global WebSocket manager."""
    global _manager
    if _manager is None:
        _manager = ConversationWebSocketManager()
    return _manager
