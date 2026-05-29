"""Tests for refactored screener command."""

import tempfile
from pathlib import Path

import pytest

from src.cli.commands.screener import ScreenerCommandRefactored as ScreenerCommand
from src.tools.screener import ScreenerConfig, ScreenerManager


class TestScreenerCommand:
	"""Test refactored screener command."""

	@pytest.fixture
	def temp_db(self):
		"""Create temporary database path."""
		with tempfile.TemporaryDirectory() as tmpdir:
			yield Path(tmpdir)

	@pytest.fixture
	def cmd(self, temp_db, monkeypatch):
		"""Create command with temporary database."""
		# Monkey-patch manager to use temp db
		cmd = ScreenerCommand()
		cmd.manager = ScreenerManager(db_path=temp_db)
		return cmd

	def test_list_empty(self, cmd):
		"""Test listing with no screeners."""
		result = cmd.handle("list")
		assert result.success
		assert "No screeners" in result.message

	def test_create_success(self, cmd):
		"""Test creating screener."""
		result = cmd.handle('create momentum "rsi_14 > 70" "rsi_14,macd"')
		assert result.success
		assert "created successfully" in result.message.lower()

	def test_create_invalid_name(self, cmd):
		"""Test creating screener with invalid name."""
		result = cmd.handle('create "123invalid" "rsi_14 > 70" "rsi_14"')
		assert not result.success
		assert "invalid" in result.message.lower()

	def test_create_missing_args(self, cmd):
		"""Test creating screener with missing arguments."""
		result = cmd.handle("create momentum")
		assert not result.success
		assert "missing" in result.message.lower() or "usage" in result.message.lower()

	def test_list_after_create(self, cmd):
		"""Test listing after creating screener."""
		cmd.handle('create test_screener "rsi_14 > 50" "rsi_14"')
		result = cmd.handle("list")
		assert result.success
		assert "test_screener" in result.message or "Found 1" in result.message

	def test_info_success(self, cmd):
		"""Test getting screener info."""
		cmd.handle('create info_test "rsi_14 > 50" "rsi_14"')
		result = cmd.handle("info info_test")
		assert result.success

	def test_info_not_found(self, cmd):
		"""Test info for non-existent screener."""
		result = cmd.handle("info nonexistent")
		assert not result.success
		assert "not found" in result.message.lower()

	def test_delete_success(self, cmd):
		"""Test deleting screener."""
		cmd.handle('create delete_test "rsi_14 > 50" "rsi_14"')
		result = cmd.handle("delete delete_test")
		assert result.success
		assert "deleted successfully" in result.message.lower()

	def test_delete_not_found(self, cmd):
		"""Test deleting non-existent screener."""
		result = cmd.handle("delete nonexistent")
		assert not result.success
		assert "not found" in result.message.lower()

	def test_run_success(self, cmd):
		"""Test running screener."""
		cmd.handle('create run_test "rsi_14 > 50" "rsi_14"')
		result = cmd.handle("run run_test")
		assert result.success

	def test_results_no_results(self, cmd):
		"""Test results when none exist."""
		cmd.handle('create result_test "rsi_14 > 50" "rsi_14"')
		result = cmd.handle("results result_test")
		assert result.success
		assert "no results" in result.message.lower() or "No results" in result.message

	def test_clear_results(self, cmd):
		"""Test clearing results."""
		cmd.handle('create clear_test "rsi_14 > 50" "rsi_14"')
		result = cmd.handle("clear-results clear_test")
		assert result.success

	def test_command_error_handling(self, cmd):
		"""Test error handling for invalid commands."""
		result = cmd.handle("invalid_subcommand")
		assert not result.success
		assert "unknown" in result.message.lower()


class TestScreenerCommandIntegration:
	"""Integration tests for screener command."""

	@pytest.fixture
	def temp_db(self):
		"""Create temporary database path."""
		with tempfile.TemporaryDirectory() as tmpdir:
			yield Path(tmpdir)

	@pytest.fixture
	def cmd(self, temp_db):
		"""Create command with temporary database."""
		cmd = ScreenerCommand()
		cmd.manager = ScreenerManager(db_path=temp_db)
		return cmd

	def test_complete_workflow(self, cmd):
		"""Test complete screener workflow."""
		# Create
		result = cmd.handle('create workflow "rsi_14 > 70 and rsi_7 < 30" "rsi_14,rsi_7"')
		assert result.success

		# List
		result = cmd.handle("list")
		assert result.success

		# Info
		result = cmd.handle("info workflow")
		assert result.success

		# Delete
		result = cmd.handle("delete workflow")
		assert result.success

		# Verify deleted
		result = cmd.handle("list")
		assert "No screeners" in result.message

	def test_result_operations(self, cmd, temp_db):
		"""Test result storage and retrieval."""
		# Create screener
		cmd.handle('create res_test "rsi_14 > 50" "rsi_14"')

		# Save a result
		manager = ScreenerManager(db_path=temp_db)
		success, msg, result_id = manager.save_result(
			"res_test",
			[{"ticker": "AAPL", "rsi": "75"}]
		)
		assert success
		assert result_id is not None

		# Check results list
		result = cmd.handle("results res_test")
		assert result.success

	def test_error_recovery(self, cmd):
		"""Test that command recovers from errors."""
		# Invalid command
		result1 = cmd.handle("invalid")
		assert not result1.success

		# Valid command should still work
		result2 = cmd.handle("list")
		assert result2.success
