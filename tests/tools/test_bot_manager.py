"""Tests for BotManager."""

import pytest
import tempfile
import json
import yaml
from pathlib import Path

from tools.bot import BotManager


class TestBotManagerInitialization:
	"""Test BotManager initialization."""

	def test_init_default(self):
		"""Test creating BotManager with default db_root."""
		manager = BotManager()
		assert manager.bots_dir is not None
		assert manager.bots_dir.exists()

	def test_init_custom_root(self):
		"""Test creating BotManager with custom db_root."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = BotManager(Path(tmpdir))
			assert manager.db_root == Path(tmpdir)
			assert manager.bots_dir == Path(tmpdir) / "bots"


class TestBotCreation:
	"""Test bot creation."""

	def test_create_bot_basic(self):
		"""Test creating a basic bot."""
		with tempfile.TemporaryDirectory() as tmpdir:
			# Create strategy file
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			config = manager.create_bot("test_bot", str(strategy_file))

			assert config["name"] == "test_bot"
			assert config["state"] == "inactive"
			assert "created_at" in config

	def test_create_bot_files(self):
		"""Test that bot creation creates all necessary files."""
		with tempfile.TemporaryDirectory() as tmpdir:
			# Create strategy file
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			bot_dir = manager.get_bot_dir("test_bot")

			# Check files exist
			assert (bot_dir / "config.yml").exists()
			assert (bot_dir / "strategy.yml").exists()
			assert (bot_dir / "portfolio.json").exists()
			assert (bot_dir / "journal.csv").exists()
			assert (bot_dir / "watchlist.txt").exists()

	def test_create_bot_duplicate_error(self):
		"""Test that creating duplicate bot raises error."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			# Try to create duplicate
			with pytest.raises(ValueError):
				manager.create_bot("test_bot", str(strategy_file))

	def test_create_bot_missing_strategy(self):
		"""Test that creating bot with missing strategy raises error."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = BotManager(Path(tmpdir) / "db")

			with pytest.raises(ValueError):
				manager.create_bot("test_bot", "/nonexistent/strategy.yml")


class TestBotListing:
	"""Test bot listing and querying."""

	def test_list_bots_empty(self):
		"""Test listing bots when none exist."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = BotManager(Path(tmpdir) / "db")
			bots = manager.list_bots()
			assert len(bots) == 0

	def test_list_bots(self):
		"""Test listing multiple bots."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")

			# Create multiple bots
			for i in range(3):
				manager.create_bot(f"bot_{i}", str(strategy_file))

			bots = manager.list_bots()
			assert len(bots) == 3

	def test_list_bots_by_state(self):
		"""Test listing bots filtered by state."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")

			# Create bots
			manager.create_bot("active_bot", str(strategy_file))
			manager.create_bot("inactive_bot", str(strategy_file))

			# Activate one
			manager.activate_bot("active_bot")

			# List by state
			active = manager.list_bots(state_filter="active")
			inactive = manager.list_bots(state_filter="inactive")

			assert len(active) == 1
			assert len(inactive) == 1
			assert active[0]["name"] == "active_bot"
			assert inactive[0]["name"] == "inactive_bot"


class TestBotStateManagement:
	"""Test bot state management."""

	def test_activate_bot(self):
		"""Test activating a bot."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			# Activate
			result = manager.activate_bot("test_bot")
			assert result is True

			# Verify state
			bot = manager.get_bot("test_bot")
			assert bot["state"] == "active"
			assert "activated_at" in bot

	def test_deactivate_bot(self):
		"""Test deactivating a bot."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))
			manager.activate_bot("test_bot")

			# Deactivate
			result = manager.deactivate_bot("test_bot")
			assert result is True

			# Verify state
			bot = manager.get_bot("test_bot")
			assert bot["state"] == "inactive"
			assert "deactivated_at" in bot

	def test_state_nonexistent_bot(self):
		"""Test state operations on nonexistent bot."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = BotManager(Path(tmpdir) / "db")

			result = manager.activate_bot("nonexistent")
			assert result is False

			result = manager.deactivate_bot("nonexistent")
			assert result is False


class TestBotConfiguration:
	"""Test bot configuration management."""

	def test_load_save_config(self):
		"""Test loading and saving bot configuration."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			# Load config
			config = manager.load_config("test_bot")
			assert config is not None
			assert config["name"] == "test_bot"

			# Modify config
			config["description"] = "Updated description"

			# Save config
			manager.save_config("test_bot", config)

			# Reload and verify
			updated = manager.load_config("test_bot")
			assert updated["description"] == "Updated description"


class TestBotWatchlist:
	"""Test bot watchlist management."""

	def test_load_save_watchlist(self):
		"""Test loading and saving watchlist."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			# Save watchlist
			tickers = ["AC.PA", "OR.PA", "CS.PA"]
			manager.save_watchlist("test_bot", tickers)

			# Load watchlist
			loaded = manager.load_watchlist("test_bot")
			assert loaded == tickers

	def test_add_to_watchlist(self):
		"""Test adding ticker to watchlist."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			# Add tickers
			result1 = manager.add_to_watchlist("test_bot", "AC.PA")
			result2 = manager.add_to_watchlist("test_bot", "AC.PA")  # Duplicate

			assert result1 is True
			assert result2 is False  # Already exists

			# Verify
			watchlist = manager.load_watchlist("test_bot")
			assert "AC.PA" in watchlist

	def test_remove_from_watchlist(self):
		"""Test removing ticker from watchlist."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			# Add and remove
			manager.add_to_watchlist("test_bot", "AC.PA")
			result = manager.remove_from_watchlist("test_bot", "AC.PA")

			assert result is True

			# Verify
			watchlist = manager.load_watchlist("test_bot")
			assert "AC.PA" not in watchlist


class TestBotPortfolio:
	"""Test bot portfolio management."""

	def test_load_save_portfolio(self):
		"""Test loading and saving portfolio."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			# Load portfolio
			portfolio = manager.load_portfolio("test_bot")
			assert portfolio is not None
			assert "cash" in portfolio
			assert "total_value" in portfolio

			# Modify portfolio
			portfolio["cash"] = 95000
			portfolio["total_value"] = 105000

			# Save portfolio
			manager.save_portfolio("test_bot", portfolio)

			# Reload and verify
			updated = manager.load_portfolio("test_bot")
			assert updated["cash"] == 95000
			assert updated["total_value"] == 105000


class TestBotSummary:
	"""Test bot summary."""

	def test_get_bots_summary(self):
		"""Test getting summary of bots by state."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")

			# Create bots
			manager.create_bot("active1", str(strategy_file))
			manager.create_bot("active2", str(strategy_file))
			manager.create_bot("inactive1", str(strategy_file))

			# Activate some
			manager.activate_bot("active1")
			manager.activate_bot("active2")

			# Get summary
			summary = manager.get_bots_summary()

			assert summary["active"] == 2
			assert summary["inactive"] == 1
			assert summary["total"] == 3


class TestBotDeletion:
	"""Test bot deletion."""

	def test_delete_bot(self):
		"""Test deleting a bot."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			# Delete
			result = manager.delete_bot("test_bot")
			assert result is True

			# Verify deleted
			bot = manager.get_bot("test_bot")
			assert bot is None

	def test_delete_nonexistent_bot(self):
		"""Test deleting nonexistent bot."""
		with tempfile.TemporaryDirectory() as tmpdir:
			manager = BotManager(Path(tmpdir) / "db")

			result = manager.delete_bot("nonexistent")
			assert result is False


class TestBotPaths:
	"""Test bot file paths."""

	def test_get_bot_dir(self):
		"""Test getting bot directory."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			bot_dir = manager.get_bot_dir("test_bot")
			assert bot_dir.exists()
			assert bot_dir.name == "test_bot"

	def test_get_file_paths(self):
		"""Test getting file paths."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			# Get paths
			portfolio_path = manager.get_portfolio_path("test_bot")
			journal_path = manager.get_journal_path("test_bot")
			watchlist_path = manager.get_watchlist_path("test_bot")

			assert portfolio_path.exists()
			assert journal_path.exists()
			assert watchlist_path.exists()


class TestBotBotInfo:
	"""Test getting comprehensive bot info."""

	def test_get_bot_info(self):
		"""Test getting all bot information."""
		with tempfile.TemporaryDirectory() as tmpdir:
			strategy_file = Path(tmpdir) / "strategy.yml"
			strategy_file.write_text("name: test_strategy\n")

			manager = BotManager(Path(tmpdir) / "db")
			manager.create_bot("test_bot", str(strategy_file))

			info = manager.get_bot_info("test_bot")

			assert info is not None
			assert "config" in info
			assert "portfolio" in info
			assert "watchlist" in info
			assert "strategy_file" in info
			assert "bot_dir" in info
