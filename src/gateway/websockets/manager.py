"""WebSocket connection manager for real-time backtest updates."""

import json
import asyncio
from typing import Dict, Set, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class WebSocketMessage:
	"""Structured WebSocket message."""
	type: str
	backtest_id: str
	strategy_name: str
	timestamp: str
	data: Any

	def to_json(self) -> str:
		"""Convert to JSON string."""
		return json.dumps(asdict(self))

	@classmethod
	def from_dict(cls, data: Dict[str, Any]) -> "WebSocketMessage":
		"""Create from dict."""
		return cls(
			type=data.get("type", ""),
			backtest_id=data.get("backtest_id", ""),
			strategy_name=data.get("strategy_name", ""),
			timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
			data=data.get("data", {})
		)


class WebSocketManager:
	"""Manages WebSocket connections and message broadcasting.

	Handles:
	- Connection tracking per backtest
	- Message broadcasting to multiple clients
	- Webhook registration for agents
	- Async message queueing
	"""

	def __init__(self):
		"""Initialize WebSocket manager."""
		self.connections: Dict[str, Set[Any]] = {}  # backtest_id -> set of websockets
		self.webhooks: Dict[str, list[Callable]] = {}  # event_type -> list of webhooks
		self.message_queues: Dict[str, asyncio.Queue] = {}  # backtest_id -> queue

	def register_connection(self, backtest_id: str, websocket: Any) -> None:
		"""Register a WebSocket connection for a backtest.

		Args:
			backtest_id: Backtest identifier
			websocket: WebSocket connection object
		"""
		if backtest_id not in self.connections:
			self.connections[backtest_id] = set()
			self.message_queues[backtest_id] = asyncio.Queue()

		self.connections[backtest_id].add(websocket)

	def unregister_connection(self, backtest_id: str, websocket: Any) -> None:
		"""Unregister a WebSocket connection.

		Args:
			backtest_id: Backtest identifier
			websocket: WebSocket connection object
		"""
		if backtest_id in self.connections:
			self.connections[backtest_id].discard(websocket)

			# Clean up if no more connections
			if not self.connections[backtest_id]:
				del self.connections[backtest_id]
				if backtest_id in self.message_queues:
					del self.message_queues[backtest_id]

	def register_webhook(self, event_type: str, callback: Callable) -> None:
		"""Register a webhook callback for an event type.

		Args:
			event_type: Event type (e.g., 'daily_results', 'backtest_complete')
			callback: Async callable to invoke
		"""
		if event_type not in self.webhooks:
			self.webhooks[event_type] = []

		self.webhooks[event_type].append(callback)

	async def broadcast_message(
		self,
		backtest_id: str,
		message_type: str,
		data: Dict[str, Any],
		strategy_name: str = ""
	) -> None:
		"""Broadcast message to all connected WebSocket clients for a backtest.

		Args:
			backtest_id: Backtest identifier
			message_type: Type of message (daily_results, backtest_complete, error)
			data: Message data
			strategy_name: Strategy name
		"""
		message = WebSocketMessage(
			type=message_type,
			backtest_id=backtest_id,
			strategy_name=strategy_name,
			timestamp=datetime.utcnow().isoformat(),
			data=data
		)

		# Broadcast to all connected clients
		if backtest_id in self.connections:
			websockets_to_remove = set()

			for websocket in self.connections[backtest_id]:
				try:
					await websocket.send_json(message.to_json())
				except Exception as e:
					# Connection closed or error, mark for removal
					websockets_to_remove.add(websocket)

			# Remove closed connections
			for ws in websockets_to_remove:
				self.unregister_connection(backtest_id, ws)

		# Trigger webhooks
		if message_type in self.webhooks:
			for webhook in self.webhooks[message_type]:
				try:
					if asyncio.iscoroutinefunction(webhook):
						await webhook(message)
					else:
						webhook(message)
				except Exception as e:
					# Log webhook error but continue
					pass

	async def broadcast_daily_results(
		self,
		backtest_id: str,
		strategy_name: str,
		date: str,
		daily_results: Dict[str, Any]
	) -> None:
		"""Broadcast daily backtest results.

		Args:
			backtest_id: Backtest identifier
			strategy_name: Strategy name
			date: Trading date
			daily_results: Daily results dict
		"""
		data = {
			"date": date,
			"results": daily_results,
			"timestamp": datetime.utcnow().isoformat()
		}

		await self.broadcast_message(
			backtest_id,
			"daily_results",
			data,
			strategy_name
		)

	async def broadcast_backtest_complete(
		self,
		backtest_id: str,
		strategy_name: str,
		metrics: Dict[str, Any],
		days_processed: int
	) -> None:
		"""Broadcast backtest completion.

		Args:
			backtest_id: Backtest identifier
			strategy_name: Strategy name
			metrics: Final metrics
			days_processed: Total days processed
		"""
		data = {
			"backtest_id": backtest_id,
			"strategy_name": strategy_name,
			"metrics": metrics,
			"days_processed": days_processed,
			"timestamp": datetime.utcnow().isoformat()
		}

		await self.broadcast_message(
			backtest_id,
			"backtest_complete",
			data,
			strategy_name
		)

	async def broadcast_error(
		self,
		backtest_id: str,
		strategy_name: str,
		error_message: str
	) -> None:
		"""Broadcast backtest error.

		Args:
			backtest_id: Backtest identifier
			strategy_name: Strategy name
			error_message: Error message
		"""
		data = {
			"backtest_id": backtest_id,
			"strategy_name": strategy_name,
			"error": error_message,
			"timestamp": datetime.utcnow().isoformat()
		}

		await self.broadcast_message(
			backtest_id,
			"error",
			data,
			strategy_name
		)

	def get_active_backtests(self) -> list[str]:
		"""Get list of active backtest IDs with connected clients.

		Returns:
			List of backtest IDs with active connections
		"""
		return [bid for bid, conns in self.connections.items() if conns]

	def get_connection_count(self, backtest_id: str) -> int:
		"""Get number of active connections for a backtest.

		Args:
			backtest_id: Backtest identifier

		Returns:
			Number of connected clients
		"""
		return len(self.connections.get(backtest_id, set()))


# Global WebSocket manager instance
_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
	"""Get or create global WebSocket manager.

	Returns:
		WebSocketManager instance
	"""
	global _ws_manager
	if _ws_manager is None:
		_ws_manager = WebSocketManager()
	return _ws_manager
