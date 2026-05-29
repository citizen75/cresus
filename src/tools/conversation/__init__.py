"""Conversation manager for portfolio-specific message storage."""

import json
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
		timestamp: Optional[datetime] = None
	):
		"""Initialize a conversation message.

		Args:
			source: Message source (user, chatbot, alert, notification)
			content: Message content
			timestamp: Message timestamp (defaults to now)
		"""
		self.source = source
		self.content = content
		self.timestamp = timestamp or datetime.utcnow()

	def to_dict(self) -> Dict[str, Any]:
		"""Convert message to dictionary."""
		return {
			"source": self.source,
			"content": self.content,
			"datetime": self.timestamp.isoformat()
		}

	@classmethod
	def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
		"""Create message from dictionary."""
		timestamp = datetime.fromisoformat(data["datetime"])
		return cls(
			source=data["source"],
			content=data["content"],
			timestamp=timestamp
		)


class ConversationManager:
	"""Manages conversation storage for a specific portfolio."""

	def __init__(self, portfolio_name: str, db_path: Optional[Path] = None):
		"""Initialize conversation manager.

		Args:
			portfolio_name: Name of the portfolio
			db_path: Base database path (defaults to ~/.cresus/db)
		"""
		self.portfolio_name = portfolio_name

		if db_path is None:
			db_path = Path.home() / ".cresus" / "db"

		self.base_path = Path(db_path)
		self.portfolio_path = self.base_path / "portfolios" / portfolio_name
		self.conversations_dir = self.portfolio_path / "conversations"
		self.history_file = self.conversations_dir / "history.json"

		self._messages: List[ConversationMessage] = []
		self._load_history()

	def _load_history(self) -> None:
		"""Load conversation history from file."""
		if not self.history_file.exists():
			self._messages = []
			return

		try:
			with open(self.history_file, "r") as f:
				data = json.load(f)
				self._messages = [
					ConversationMessage.from_dict(msg) for msg in data
				]
		except (json.JSONDecodeError, KeyError) as e:
			print(f"Error loading conversation history: {e}")
			self._messages = []

	def _save_history(self) -> None:
		"""Save conversation history to file."""
		self.conversations_dir.mkdir(parents=True, exist_ok=True)

		data = [msg.to_dict() for msg in self._messages]

		with open(self.history_file, "w") as f:
			json.dump(data, f, indent=2)

	def add_message(
		self,
		source: ConversationSource,
		content: str,
		timestamp: Optional[datetime] = None
	) -> None:
		"""Add a message to conversation history.

		Args:
			source: Message source
			content: Message content
			timestamp: Message timestamp (defaults to now)
		"""
		message = ConversationMessage(source, content, timestamp)
		self._messages.append(message)
		self._save_history()

	def add_user_message(self, content: str) -> None:
		"""Add a user message."""
		self.add_message("user", content)

	def add_chatbot_message(self, content: str) -> None:
		"""Add a chatbot message."""
		self.add_message("chatbot", content)

	def add_alert(self, content: str) -> None:
		"""Add an alert message."""
		self.add_message("alert", content)

	def add_notification(self, content: str) -> None:
		"""Add a notification message."""
		self.add_message("notification", content)

	def get_history(
		self,
		limit: Optional[int] = None,
		source_filter: Optional[ConversationSource] = None
	) -> List[ConversationMessage]:
		"""Get conversation history.

		Args:
			limit: Maximum number of messages to return (None for all)
			source_filter: Filter by message source (None for all)

		Returns:
			List of conversation messages
		"""
		messages = self._messages

		if source_filter:
			messages = [m for m in messages if m.source == source_filter]

		if limit:
			messages = messages[-limit:]

		return messages

	def get_history_dicts(
		self,
		limit: Optional[int] = None,
		source_filter: Optional[ConversationSource] = None
	) -> List[Dict[str, Any]]:
		"""Get conversation history as dictionaries.

		Args:
			limit: Maximum number of messages to return
			source_filter: Filter by message source

		Returns:
			List of message dictionaries
		"""
		messages = self.get_history(limit, source_filter)
		return [msg.to_dict() for msg in messages]

	def clear_history(self) -> None:
		"""Clear all conversation history."""
		self._messages = []
		self._save_history()

	def get_message_count(self, source_filter: Optional[ConversationSource] = None) -> int:
		"""Get count of messages.

		Args:
			source_filter: Filter by message source

		Returns:
			Number of messages
		"""
		if source_filter:
			return len([m for m in self._messages if m.source == source_filter])
		return len(self._messages)

	def get_last_message(
		self,
		source_filter: Optional[ConversationSource] = None
	) -> Optional[ConversationMessage]:
		"""Get the last message.

		Args:
			source_filter: Filter by message source

		Returns:
			Last message or None
		"""
		messages = self.get_history(source_filter=source_filter)
		return messages[-1] if messages else None
