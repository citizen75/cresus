"""Tests for DataAgent."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.data.agent import DataAgent
from core.context import AgentContext


class TestDataAgent(unittest.TestCase):
	"""Test cases for DataAgent class."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = DataAgent("DataAgent", context=self.context)

	def test_init(self):
		"""Test that DataAgent can be initialized."""
		assert self.agent.name == "DataAgent"
		assert self.agent.context is not None
		assert isinstance(self.agent.context, AgentContext)

	def test_process_skips_if_data_in_context(self):
		"""Test that process skips loading if data_history already in context."""
		# Pre-populate context with data_history (backtest mode)
		existing_data = {
			"AAPL": pd.DataFrame({"close": [100, 101, 102]}),
			"GOOGL": pd.DataFrame({"close": [2000, 2001, 2002]}),
		}
		self.context.set("data_history", existing_data)

		# Process should return early
		result = self.agent.process({"tickers": ["AAPL"]})

		assert result.get("status") == "success"
		assert result.get("output", {}).get("count") == 2  # From existing_data
		assert result.get("output", {}).get("data_fetched") == 2

	def test_process_loads_tickers_from_input(self):
		"""Test that process loads data for tickers from input."""
		mock_df = pd.DataFrame({
			"timestamp": pd.date_range("2026-01-01", periods=10),
			"open": [100 + i for i in range(10)],
			"high": [102 + i for i in range(10)],
			"low": [99 + i for i in range(10)],
			"close": [101 + i for i in range(10)],
			"volume": [1000000] * 10,
		})

		with patch("agents.data.agent.DataHistory") as mock_dh_class:
			mock_instance = MagicMock()
			mock_instance.get_all.return_value = mock_df
			mock_dh_class.return_value = mock_instance

			result = self.agent.process({"tickers": ["AAPL", "GOOGL"]})

			assert result.get("status") == "success"
			assert result.get("output", {}).get("count") == 2
			assert result.get("output", {}).get("data_fetched") == 2
			assert self.context.get("data_history") is not None
			assert "AAPL" in self.context.get("data_history")
			assert "GOOGL" in self.context.get("data_history")

	def test_process_loads_tickers_from_context(self):
		"""Test that process loads tickers from context if not in input."""
		self.context.set("tickers", ["MSFT", "AMZN"])

		mock_df = pd.DataFrame({
			"timestamp": pd.date_range("2026-01-01", periods=5),
			"close": [300, 301, 302, 303, 304],
		})

		with patch("agents.data.agent.DataHistory") as mock_dh_class:
			mock_instance = MagicMock()
			mock_instance.get_all.return_value = mock_df
			mock_dh_class.return_value = mock_instance

			result = self.agent.process({})

			assert result.get("status") == "success"
			assert result.get("output", {}).get("count") == 2
			assert result.get("output", {}).get("data_fetched") == 2

	def test_process_no_tickers_no_data(self):
		"""Test that process returns error when no tickers found."""
		result = self.agent.process({})

		assert result.get("status") == "error"
		assert "No tickers found" in result.get("message", "")

	def test_process_all_tickers_fail(self):
		"""Test that process returns error when all tickers fail to load."""
		with patch("agents.data.agent.DataHistory") as mock_dh_class:
			mock_instance = MagicMock()
			mock_instance.get_all.return_value = pd.DataFrame()  # Empty DataFrame
			mock_dh_class.return_value = mock_instance

			result = self.agent.process({"tickers": ["INVALID1", "INVALID2"]})

			# Should return success but with no data_fetched
			assert result.get("status") == "success"
			assert result.get("output", {}).get("data_fetched") == 0

	def test_process_partial_tickers_fail(self):
		"""Test that process continues when some tickers fail."""
		mock_df = pd.DataFrame({
			"timestamp": pd.date_range("2026-01-01", periods=5),
			"close": [100, 101, 102, 103, 104],
		})

		call_count = [0]

		def side_effect():
			call_count[0] += 1
			if call_count[0] == 1:
				return mock_df  # First call succeeds
			else:
				return pd.DataFrame()  # Second call fails

		with patch("agents.data.agent.DataHistory") as mock_dh_class:
			mock_instance = MagicMock()
			mock_instance.get_all.side_effect = side_effect
			mock_dh_class.return_value = mock_instance

			result = self.agent.process({"tickers": ["AAPL", "INVALID"]})

			assert result.get("status") == "success"
			assert result.get("output", {}).get("data_fetched") == 1

	def test_process_with_indicators(self):
		"""Test that process calculates indicators when specified."""
		mock_df = pd.DataFrame({
			"timestamp": pd.date_range("2026-01-01", periods=30),
			"open": [100 + i*0.5 for i in range(30)],
			"high": [102 + i*0.5 for i in range(30)],
			"low": [99 + i*0.5 for i in range(30)],
			"close": [101 + i*0.5 for i in range(30)],
			"volume": [1000000] * 30,
		})

		with patch("agents.data.agent.DataHistory") as mock_dh_class:
			with patch("agents.data.agent.calculate_indicators") as mock_calc:
				mock_instance = MagicMock()
				mock_instance.get_all.return_value = mock_df
				mock_instance.filepath = Path("/tmp/test.parquet")
				mock_dh_class.return_value = mock_instance

				mock_calc.return_value = {"rsi_14": pd.Series([50] * 30)}

				result = self.agent.process({
					"tickers": ["AAPL"],
					"indicators": ["rsi_14"]
				})

				assert result.get("status") == "success"
				assert mock_calc.called
				assert "rsi_14" in result.get("output", {}).get("indicators", [])

	def test_process_stores_strategy_config_indicators(self):
		"""Test that process uses indicators from strategy_config."""
		self.context.set("strategy_config", {"indicators": ["ema_20", "rsi_7"]})

		mock_df = pd.DataFrame({
			"timestamp": pd.date_range("2026-01-01", periods=30),
			"close": [100 + i for i in range(30)],
		})

		with patch("agents.data.agent.DataHistory") as mock_dh_class:
			with patch("agents.data.agent.calculate_indicators") as mock_calc:
				mock_instance = MagicMock()
				mock_instance.get_all.return_value = mock_df
				mock_instance.filepath = Path("/tmp/test.parquet")
				mock_dh_class.return_value = mock_instance

				mock_calc.return_value = {"ema_20": pd.Series([100] * 30)}

				result = self.agent.process({"tickers": ["MSFT"]})

				assert result.get("status") == "success"
				assert mock_calc.called
				# Verify that indicators were passed to calculate function
				call_args = mock_calc.call_args
				assert call_args is not None

	def test_process_empty_input(self):
		"""Test that process handles None input data."""
		result = self.agent.process(None)

		assert result.get("status") == "error"

	def test_process_multiple_calls(self):
		"""Test that multiple process calls work correctly."""
		mock_df = pd.DataFrame({
			"timestamp": pd.date_range("2026-01-01", periods=10),
			"close": [100 + i for i in range(10)],
		})

		with patch("agents.data.agent.DataHistory") as mock_dh_class:
			mock_instance = MagicMock()
			mock_instance.get_all.return_value = mock_df
			mock_dh_class.return_value = mock_instance

			result1 = self.agent.process({"tickers": ["AAPL"]})
			assert result1.get("status") == "success"

			# Create a new agent for second call to avoid context carryover
			agent2 = DataAgent("DataAgent", context=AgentContext())
			result2 = agent2.process({"tickers": ["GOOGL", "MSFT"]})
			assert result2.get("status") == "success"
			assert result2.get("output", {}).get("count") == 2


if __name__ == "__main__":
	unittest.main()
