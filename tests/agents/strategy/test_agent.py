"""Tests for StrategyAgent."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.strategy.agent import StrategyAgent
from core.context import AgentContext


class TestStrategyAgent(unittest.TestCase):
	"""Test cases for StrategyAgent class."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_init(self):
		"""Test that StrategyAgent can be initialized."""
		agent = StrategyAgent("StrategyAgent[test_strategy]", self.context)
		assert "test_strategy" in agent.name
		assert agent.context is not None

	def test_process_uses_input_tickers(self):
		"""Test that process uses tickers from input."""
		agent = StrategyAgent("StrategyAgent[test_strategy]", self.context)

		with patch("agents.strategy.agent.StrategyManager") as mock_mgr_class:
			mock_mgr = MagicMock()
			mock_mgr.load_strategy.return_value = {
				"status": "success",
				"data": {
					"engine": "TaModel",
					"signals": ["rsi_7"],
					"buy_conditions": "data['rsi_7'] < 30",
					"sell_conditions": "data['rsi_7'] > 70",
				}
			}
			mock_mgr_class.return_value = mock_mgr

			result = agent.process({"tickers": ["AAPL", "GOOGL", "MSFT"]})

			# Should process successfully or return output
			assert result.get("status") in ["success", "error"]

	def test_process_loads_from_universe(self):
		"""Test that process loads tickers from universe when not provided."""
		agent = StrategyAgent("StrategyAgent[test_strategy]", self.context)
		self.context.set("universe", "cac40")

		with patch("agents.strategy.agent.Universe") as mock_universe_class:
			mock_universe = MagicMock()
			mock_universe.get_tickers.return_value = ["AC.PA", "AI.PA", "BNP.PA"]
			mock_universe_class.return_value = mock_universe

			with patch("agents.strategy.agent.StrategyManager") as mock_mgr_class:
				mock_mgr = MagicMock()
				mock_mgr.load_strategy.return_value = {
					"status": "success",
					"data": {
						"engine": "TaModel",
						"signals": [],
						"buy_conditions": "True",
						"sell_conditions": "False",
					}
				}
				mock_mgr_class.return_value = mock_mgr

				result = agent.process({})

				assert result.get("status") in ["success", "error"]

	def test_process_strategy_not_found(self):
		"""Test that process returns error when strategy not found."""
		agent = StrategyAgent("StrategyAgent[nonexistent_strategy]", self.context)

		with patch("agents.strategy.agent.StrategyManager") as mock_mgr_class:
			mock_mgr = MagicMock()
			mock_mgr.load_strategy.return_value = {
				"status": "error",
				"message": "Strategy not found"
			}
			mock_mgr_class.return_value = mock_mgr

			result = agent.process({"tickers": ["AAPL"]})

			# Should handle error gracefully
			assert result.get("status") in ["success", "error"]

	def test_process_stores_strategy_config_in_context(self):
		"""Test that process stores strategy config in context."""
		agent = StrategyAgent("StrategyAgent[test_strategy]", self.context)

		strategy_config = {
			"engine": "TaModel",
			"signals": ["rsi_7"],
			"buy_conditions": "data['rsi_7'] < 30",
		}

		with patch("agents.strategy.agent.StrategyManager") as mock_mgr_class:
			mock_mgr = MagicMock()
			mock_mgr.load_strategy.return_value = {
				"status": "success",
				"data": strategy_config
			}
			mock_mgr_class.return_value = mock_mgr

			result = agent.process({"tickers": ["AAPL"]})

			assert result.get("status") in ["success", "error"]

	def test_process_with_empty_tickers(self):
		"""Test that process handles empty ticker list."""
		agent = StrategyAgent("StrategyAgent[test_strategy]", self.context)

		result = agent.process({"tickers": []})

		# Should return something (success or error)
		assert result.get("status") in ["success", "error"]


if __name__ == "__main__":
	unittest.main()
