"""Tests for refactored strategy command."""

from pathlib import Path

import pytest

from src.cli.commands.strategy import StrategyCommand


class TestStrategyCommand:
	"""Test refactored strategy command."""

	@pytest.fixture
	def cmd(self):
		"""Create strategy command."""
		return StrategyCommand(project_root=Path.cwd())

	def test_handle_empty(self, cmd):
		"""Test handling empty input."""
		result = cmd.handle("")
		# Empty should show list
		assert result is not None

	def test_unknown_subcommand(self, cmd):
		"""Test unknown subcommand handling."""
		result = cmd.handle("unknown_command")
		assert not result.success
		assert "unknown" in result.message.lower()

	def test_list_subcommand(self, cmd):
		"""Test list subcommand."""
		result = cmd.handle("list")
		assert result is not None
		assert hasattr(result, 'success')

	def test_command_result_structure(self, cmd):
		"""Test that command returns proper CommandResult structure."""
		result = cmd.handle("list")
		assert hasattr(result, 'success')
		assert hasattr(result, 'message')
		assert isinstance(result.success, bool)
		assert isinstance(result.message, str)

	def test_show_missing_args(self, cmd):
		"""Test show without required args."""
		result = cmd.handle("show")
		assert not result.success
		assert "usage" in result.message.lower() or "missing" in result.message.lower()

	def test_duplicate_missing_args(self, cmd):
		"""Test duplicate without required args."""
		result = cmd.handle("duplicate")
		assert not result.success

	def test_check_missing_args(self, cmd):
		"""Test check without required args."""
		result = cmd.handle("check")
		assert not result.success
		assert "usage" in result.message.lower() or "missing" in result.message.lower()
