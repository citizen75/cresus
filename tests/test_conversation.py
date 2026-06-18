"""Tests for conversation manager module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.tools.conversation import ConversationMessage, ConversationManager, ConversationSource


class TestConversationMessage:
	"""Test ConversationMessage class."""

	def test_init_with_defaults(self):
		"""Test message creation with default timestamp."""
		msg = ConversationMessage("user", "Hello")
		assert msg.source == "user"
		assert msg.content == "Hello"
		assert isinstance(msg.timestamp, datetime)

	def test_init_with_custom_timestamp(self):
		"""Test message creation with custom timestamp."""
		ts = datetime(2025, 1, 15, 10, 30, 0)
		msg = ConversationMessage("chatbot", "Hi there", timestamp=ts)
		assert msg.source == "chatbot"
		assert msg.content == "Hi there"
		assert msg.timestamp == ts

	def test_valid_sources(self):
		"""Test all valid message sources."""
		sources: list[ConversationSource] = ["user", "chatbot", "alert", "notification"]
		for source in sources:
			msg = ConversationMessage(source, f"Test {source}")
			assert msg.source == source

	def test_to_dict(self):
		"""Test converting message to dictionary."""
		ts = datetime(2025, 1, 15, 10, 30, 0)
		msg = ConversationMessage("user", "Test content", timestamp=ts)
		data = msg.to_dict()

		assert data["source"] == "user"
		assert data["content"] == "Test content"
		assert data["datetime"] == ts.isoformat()

	def test_from_dict(self):
		"""Test creating message from dictionary."""
		ts = datetime(2025, 1, 15, 10, 30, 0)
		data = {
			"source": "chatbot",
			"content": "Hello user",
			"datetime": ts.isoformat()
		}
		msg = ConversationMessage.from_dict(data)

		assert msg.source == "chatbot"
		assert msg.content == "Hello user"
		assert msg.timestamp == ts

	def test_round_trip_serialization(self):
		"""Test round-trip serialization and deserialization."""
		original = ConversationMessage("alert", "Alert message")
		data = original.to_dict()
		restored = ConversationMessage.from_dict(data)

		assert restored.source == original.source
		assert restored.content == original.content
		assert restored.timestamp == original.timestamp


class TestConversationManager:
	"""Test ConversationManager class."""

	@pytest.fixture
	def temp_db_path(self):
		"""Create temporary database path."""
		with tempfile.TemporaryDirectory() as tmpdir:
			yield Path(tmpdir)

	@pytest.fixture
	def manager(self, temp_db_path):
		"""Create a conversation manager with temp path."""
		return ConversationManager("test_portfolio", db_path=temp_db_path)

	def test_init_creates_paths(self, temp_db_path):
		"""Test that initialization sets up correct paths."""
		manager = ConversationManager("my_portfolio", db_path=temp_db_path)

		assert manager.portfolio_name == "my_portfolio"
		assert manager.base_path == temp_db_path
		assert manager.portfolio_path == temp_db_path / "portfolios" / "my_portfolio"
		assert manager.conversations_dir == temp_db_path / "portfolios" / "my_portfolio" / "conversations"

	def test_add_user_message(self, manager):
		"""Test adding a user message."""
		manager.add_user_message("Hello bot")
		assert manager.get_message_count() == 1

		messages = manager.get_history()
		assert messages[0].source == "user"
		assert messages[0].content == "Hello bot"

	def test_add_chatbot_message(self, manager):
		"""Test adding a chatbot message."""
		manager.add_chatbot_message("Hello user")
		assert manager.get_message_count() == 1

		messages = manager.get_history()
		assert messages[0].source == "chatbot"
		assert messages[0].content == "Hello user"

	def test_add_alert(self, manager):
		"""Test adding an alert."""
		manager.add_alert("Alert: Price dropped")
		assert manager.get_message_count() == 1

		messages = manager.get_history()
		assert messages[0].source == "alert"
		assert messages[0].content == "Alert: Price dropped"

	def test_add_notification(self, manager):
		"""Test adding a notification."""
		manager.add_notification("New trade executed")
		assert manager.get_message_count() == 1

		messages = manager.get_history()
		assert messages[0].source == "notification"
		assert messages[0].content == "New trade executed"

	def test_add_message_generic(self, manager):
		"""Test generic add_message method."""
		manager.add_message("user", "Generic message")
		assert manager.get_message_count() == 1

	def test_add_message_with_custom_timestamp(self, manager):
		"""Test adding message with custom timestamp."""
		ts = datetime(2025, 1, 15, 10, 30, 0)
		manager.add_message("user", "Timestamped message", timestamp=ts)

		messages = manager.get_history()
		assert messages[0].timestamp == ts

	def test_get_history_all(self, manager):
		"""Test getting all history."""
		manager.add_user_message("Message 1")
		manager.add_chatbot_message("Message 2")
		manager.add_alert("Message 3")

		messages = manager.get_history()
		assert len(messages) == 3

	def test_get_history_with_limit(self, manager):
		"""Test getting history with limit."""
		for i in range(5):
			manager.add_user_message(f"Message {i}")

		messages = manager.get_history(limit=3)
		assert len(messages) == 3
		assert messages[0].content == "Message 2"
		assert messages[1].content == "Message 3"
		assert messages[2].content == "Message 4"

	def test_get_history_with_source_filter(self, manager):
		"""Test filtering history by source."""
		manager.add_user_message("User message 1")
		manager.add_chatbot_message("Bot message")
		manager.add_user_message("User message 2")
		manager.add_alert("Alert message")

		user_messages = manager.get_history(source_filter="user")
		assert len(user_messages) == 2
		assert all(m.source == "user" for m in user_messages)

	def test_get_history_with_limit_and_filter(self, manager):
		"""Test history with both limit and source filter."""
		for i in range(3):
			manager.add_user_message(f"User {i}")
			manager.add_chatbot_message(f"Bot {i}")

		messages = manager.get_history(limit=2, source_filter="chatbot")
		assert len(messages) == 2
		assert all(m.source == "chatbot" for m in messages)

	def test_get_history_dicts(self, manager):
		"""Test getting history as dictionaries."""
		manager.add_user_message("Test message")
		dicts = manager.get_history_dicts()

		assert len(dicts) == 1
		assert dicts[0]["source"] == "user"
		assert dicts[0]["content"] == "Test message"
		assert "datetime" in dicts[0]

	def test_clear_history(self, manager):
		"""Test clearing history."""
		manager.add_user_message("Message 1")
		manager.add_chatbot_message("Message 2")
		assert manager.get_message_count() == 2

		manager.clear_history()
		assert manager.get_message_count() == 0

	def test_get_message_count_all(self, manager):
		"""Test getting total message count."""
		manager.add_user_message("1")
		manager.add_chatbot_message("2")
		manager.add_alert("3")

		assert manager.get_message_count() == 3

	def test_get_message_count_filtered(self, manager):
		"""Test getting filtered message count."""
		manager.add_user_message("1")
		manager.add_chatbot_message("2")
		manager.add_chatbot_message("3")

		assert manager.get_message_count(source_filter="chatbot") == 2

	def test_get_last_message(self, manager):
		"""Test getting last message."""
		manager.add_user_message("First")
		manager.add_chatbot_message("Second")
		manager.add_alert("Third")

		last = manager.get_last_message()
		assert last is not None
		assert last.source == "alert"
		assert last.content == "Third"

	def test_get_last_message_filtered(self, manager):
		"""Test getting last message with filter."""
		manager.add_user_message("User 1")
		manager.add_chatbot_message("Bot 1")
		manager.add_user_message("User 2")

		last_user = manager.get_last_message(source_filter="user")
		assert last_user is not None
		assert last_user.content == "User 2"

	def test_get_last_message_empty(self, manager):
		"""Test getting last message when history is empty."""
		last = manager.get_last_message()
		assert last is None

	def test_get_last_message_no_match(self, manager):
		"""Test getting last message with filter that matches nothing."""
		manager.add_user_message("User message")
		last = manager.get_last_message(source_filter="alert")
		assert last is None

	def test_persistence_save_and_load(self, temp_db_path):
		"""Test that messages persist to disk and load correctly."""
		manager1 = ConversationManager("persistent", db_path=temp_db_path)
		manager1.add_user_message("Message 1")
		manager1.add_chatbot_message("Message 2")

		# Create new manager with same portfolio
		manager2 = ConversationManager("persistent", db_path=temp_db_path)
		messages = manager2.get_history()

		assert len(messages) == 2
		assert messages[0].source == "user"
		assert messages[0].content == "Message 1"
		assert messages[1].source == "chatbot"
		assert messages[1].content == "Message 2"

	def test_history_file_format(self, temp_db_path):
		"""Test that history file is valid JSON."""
		manager = ConversationManager("json_test", db_path=temp_db_path)
		manager.add_user_message("Test message")

		# Note: Unified history is stored in conversations/history.json with portfolio metadata
		history_file = temp_db_path / "conversations" / "history.json"
		assert history_file.exists()

		with open(history_file, "r") as f:
			data = json.load(f)

		assert isinstance(data, list)
		assert len(data) >= 1
		# Find the message we just added
		test_msg = [m for m in data if m.get("content") == "Test message"]
		assert len(test_msg) == 1
		assert test_msg[0]["source"] == "user"

	def test_corrupted_history_handling(self, temp_db_path):
		"""Test graceful handling of corrupted history file."""
		# Create directory and corrupted file
		portfolio_path = temp_db_path / "portfolios" / "corrupt" / "conversations"
		portfolio_path.mkdir(parents=True, exist_ok=True)
		history_file = portfolio_path / "history.json"

		# Write invalid JSON
		with open(history_file, "w") as f:
			f.write("{ invalid json }")

		# Manager should load with empty history
		manager = ConversationManager("corrupt", db_path=temp_db_path)
		assert manager.get_message_count() == 0

	def test_empty_history_file(self, temp_db_path):
		"""Test loading from non-existent history file."""
		manager = ConversationManager("new", db_path=temp_db_path)
		assert manager.get_message_count() == 0
		assert manager.get_history() == []

	def test_multiple_portfolios(self, temp_db_path):
		"""Test separate conversations for different portfolios."""
		manager1 = ConversationManager("portfolio1", db_path=temp_db_path)
		manager2 = ConversationManager("portfolio2", db_path=temp_db_path)

		manager1.add_user_message("Portfolio 1 message")
		manager2.add_user_message("Portfolio 2 message")

		assert manager1.get_message_count() == 1
		assert manager2.get_message_count() == 1
		assert manager1.get_history()[0].content == "Portfolio 1 message"
		assert manager2.get_history()[0].content == "Portfolio 2 message"

	def test_special_characters_in_content(self, manager):
		"""Test handling of special characters in message content."""
		special_content = 'Hello! "Test" with\nnewlines\tand\tspecial chars: é à ü'
		manager.add_user_message(special_content)

		messages = manager.get_history()
		assert messages[0].content == special_content

	def test_very_long_message(self, manager):
		"""Test handling of very long messages."""
		long_content = "x" * 10000
		manager.add_user_message(long_content)

		messages = manager.get_history()
		assert messages[0].content == long_content
		assert len(messages[0].content) == 10000
