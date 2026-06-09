"""Unified conversation manager with single file storage and filtering."""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal

ConversationSource = Literal["user", "chatbot", "alert", "notification"]


class ConversationMessage:
	"""Represents a single conversation message."""

	def __init__(
		self,
		source: ConversationSource,
		content: str,
		portfolio: Optional[str] = None,
		timestamp: Optional[datetime] = None
	):
		"""Initialize a conversation message.

		Args:
			source: Message source (user, chatbot, alert, notification)
			content: Message content
			portfolio: Target portfolio (None = global)
			timestamp: Message timestamp (defaults to now)
		"""
		self.source = source
		self.content = content
		self.portfolio = portfolio
		self.timestamp = timestamp or datetime.utcnow()

	def to_dict(self) -> Dict[str, Any]:
		"""Convert message to dictionary."""
		return {
			"source": self.source,
			"content": self.content,
			"portfolio": self.portfolio,
			"datetime": self.timestamp.isoformat()
		}

	@classmethod
	def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
		"""Create message from dictionary."""
		timestamp = datetime.fromisoformat(data["datetime"])
		return cls(
			source=data["source"],
			content=data["content"],
			portfolio=data.get("portfolio"),
			timestamp=timestamp
		)


class ConversationManager:
	"""Manages unified conversation storage with filtering.

	Single file at ~/.cresus/db/conversations/history.json stores all messages
	with portfolio metadata. Filters applied at query time.
	"""

	_lock = threading.Lock()  # For thread-safe file access
	_global_history: Optional[List[ConversationMessage]] = None
	_cache_path: Optional[Path] = None

	def __init__(self, portfolio_name: str, db_path: Optional[Path] = None):
		"""Initialize conversation manager.

		Args:
			portfolio_name: Portfolio name (used for filtering, not storage path)
			db_path: Base database path (defaults to ~/.cresus/db)
		"""
		self.portfolio_name = portfolio_name

		if db_path is None:
			db_path = Path.home() / ".cresus" / "db"

		self.base_path = Path(db_path)
		self.history_file = self.base_path / "conversations" / "history.json"

		# Load global history once per process
		if ConversationManager._cache_path != self.history_file:
			ConversationManager._global_history = None
			ConversationManager._cache_path = self.history_file

		self._load_history()

	def _load_history(self) -> None:
		"""Load conversation history from file (cached)."""
		with ConversationManager._lock:
			if ConversationManager._global_history is not None:
				return

			if not self.history_file.exists():
				ConversationManager._global_history = []
				return

			try:
				with open(self.history_file, "r") as f:
					data = json.load(f)
					ConversationManager._global_history = [
						ConversationMessage.from_dict(msg) for msg in data
					]
			except (json.JSONDecodeError, KeyError) as e:
				print(f"Error loading conversation history: {e}")
				ConversationManager._global_history = []

	def _save_history(self) -> None:
		"""Save conversation history to file."""
		with ConversationManager._lock:
			self.history_file.parent.mkdir(parents=True, exist_ok=True)

			data = [msg.to_dict() for msg in ConversationManager._global_history]

			with open(self.history_file, "w") as f:
				json.dump(data, f, indent=2)

	def add_message(
		self,
		source: ConversationSource,
		content: str,
		portfolio: Optional[str] = None,
		timestamp: Optional[datetime] = None
	) -> None:
		"""Add a message to conversation history.

		Args:
			source: Message source
			content: Message content
			portfolio: Target portfolio (None = global)
			timestamp: Message timestamp (defaults to now)
		"""
		with ConversationManager._lock:
			message = ConversationMessage(source, content, portfolio, timestamp)
			ConversationManager._global_history.append(message)
			self._save_history()

	def add_user_message(self, content: str) -> None:
		"""Add a user message to this portfolio."""
		self.add_message("user", content, self.portfolio_name)

	def add_chatbot_message(self, content: str) -> None:
		"""Add a chatbot message to this portfolio."""
		self.add_message("chatbot", content, self.portfolio_name)

	def add_alert(self, content: str) -> None:
		"""Add an alert message to this portfolio."""
		self.add_message("alert", content, self.portfolio_name)

	def add_notification(self, content: str) -> None:
		"""Add a notification message to this portfolio."""
		self.add_message("notification", content, self.portfolio_name)

	def get_history(
		self,
		limit: Optional[int] = None,
		source_filter: Optional[ConversationSource] = None,
		portfolio_filter: Optional[str] = None
	) -> List[ConversationMessage]:
		"""Get conversation history with filtering.

		Args:
			limit: Maximum number of messages to return (None for all)
			source_filter: Filter by message source (None for all)
			portfolio_filter: Filter by portfolio (None for all, '_global' for global only)

		Returns:
			List of conversation messages
		"""
		with ConversationManager._lock:
			messages = ConversationManager._global_history[:]

		# Filter by portfolio
		if portfolio_filter == "_global":
			messages = [m for m in messages if m.portfolio is None]
		elif portfolio_filter:
			messages = [m for m in messages if m.portfolio == portfolio_filter]

		# Filter by source
		if source_filter:
			messages = [m for m in messages if m.source == source_filter]

		# Apply limit to most recent messages
		if limit:
			messages = messages[-limit:]

		return messages

	def get_history_dicts(
		self,
		limit: Optional[int] = None,
		source_filter: Optional[ConversationSource] = None,
		portfolio_filter: Optional[str] = None
	) -> List[Dict[str, Any]]:
		"""Get conversation history as dictionaries.

		Args:
			limit: Maximum number of messages to return
			source_filter: Filter by message source
			portfolio_filter: Filter by portfolio

		Returns:
			List of message dictionaries
		"""
		messages = self.get_history(limit, source_filter, portfolio_filter)
		return [msg.to_dict() for msg in messages]

	def clear_history(self) -> None:
		"""Clear all conversation history."""
		with ConversationManager._lock:
			ConversationManager._global_history = []
			self._save_history()

	def get_message_count(
		self,
		source_filter: Optional[ConversationSource] = None,
		portfolio_filter: Optional[str] = None
	) -> int:
		"""Get count of messages with optional filters.

		Args:
			source_filter: Filter by message source
			portfolio_filter: Filter by portfolio

		Returns:
			Number of messages
		"""
		messages = self.get_history(source_filter=source_filter, portfolio_filter=portfolio_filter)
		return len(messages)

	def get_last_message(
		self,
		source_filter: Optional[ConversationSource] = None,
		portfolio_filter: Optional[str] = None
	) -> Optional[ConversationMessage]:
		"""Get the last message matching filters.

		Args:
			source_filter: Filter by message source
			portfolio_filter: Filter by portfolio

		Returns:
			Last message or None
		"""
		messages = self.get_history(source_filter=source_filter, portfolio_filter=portfolio_filter)
		return messages[-1] if messages else None
