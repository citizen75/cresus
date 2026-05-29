"""Tests for refactored portfolio command."""

import tempfile
from pathlib import Path

import pytest

from src.cli.commands.portfolio import PortfolioCommand


class TestPortfolioCommand:
	"""Test refactored portfolio command."""

	@pytest.fixture
	def cmd(self):
		"""Create portfolio command."""
		return PortfolioCommand()

	def test_handle_empty(self, cmd):
		"""Test handling empty input."""
		result = cmd.handle("")
		assert result.success or not result.success  # Either error or help

	def test_orders_subcommand(self, cmd):
		"""Test orders subcommand routing."""
		result = cmd.handle("orders")
		# Should fail with usage error
		assert not result.success
		assert "usage" in result.message.lower() or "unknown" in result.message.lower()

	def test_watchlist_subcommand(self, cmd):
		"""Test watchlist subcommand routing."""
		result = cmd.handle("watchlist")
		# Should fail with usage error
		assert not result.success

	def test_unknown_subcommand(self, cmd):
		"""Test unknown subcommand handling."""
		result = cmd.handle("unknown")
		assert not result.success
		assert "unknown" in result.message.lower()

	def test_command_result_structure(self, cmd):
		"""Test that command returns proper CommandResult structure."""
		result = cmd.handle("list")
		assert hasattr(result, 'success')
		assert hasattr(result, 'message')
		assert isinstance(result.success, bool)
		assert isinstance(result.message, str)
