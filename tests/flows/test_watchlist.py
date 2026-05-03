"""Tests for WatchlistFlow."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from flows.watchlist import WatchlistFlow
from agents.core.context import AgentContext
from agents.strategy.agent import StrategyAgent
from agents.watchlist.agent import WatchListAgent


class TestWatchlistFlow:
	"""Test cases for WatchlistFlow class."""

	def test_watchlist_flow_initialization(self):
		"""Test that WatchlistFlow can be initialized with a strategy."""
		flow = WatchlistFlow("test_strategy")
		assert flow.strategy_name == "test_strategy"
		assert flow.context is not None
		assert isinstance(flow.context, AgentContext)
		assert len(flow.steps) == 2  # strategy and watchlist steps

	def test_watchlist_flow_initialization_creates_context(self):
		"""Test that WatchlistFlow creates a new context."""
		flow = WatchlistFlow("strategy1")
		assert isinstance(flow.context, AgentContext)
		assert flow.context is not None

	def test_watchlist_flow_initialization_creates_strategy_agent(self):
		"""Test that WatchlistFlow creates steps with correct agents."""
		flow = WatchlistFlow("my_strategy")
		assert len(flow.steps) == 2
		assert flow.steps[0].name == "strategy"
		assert flow.steps[0].agent_name == "StrategyAgent[my_strategy]"
		assert flow.steps[1].name == "watchlist"
		assert flow.steps[1].agent_name == "WatchListAgent"

	def test_watchlist_flow_process_with_valid_input(self):
		"""Test that process returns success with valid input."""
		flow = WatchlistFlow("test_strategy")
		input_data = {"tickers": ["AAPL", "GOOGL", "MSFT"]}
		result = flow.process(input_data)

		assert result.get("status") == "success"
		assert "watchlist" in result
		assert result.get("strategy") == "test_strategy"

	def test_watchlist_flow_process_with_empty_input(self):
		"""Test that process handles empty input data."""
		flow = WatchlistFlow("test_strategy")
		result = flow.process({"tickers": []})

		# Empty ticker list should fail
		assert result.get("status") == "error"

	def test_watchlist_flow_process_with_none_input(self):
		"""Test that process handles None input data."""
		flow = WatchlistFlow("test_strategy")
		result = flow.process(None)

		# None input should fail because no tickers are provided
		assert result.get("status") == "error"

	def test_watchlist_flow_process_passes_data_to_strategy_agent(self):
		"""Test that process passes input data to strategy agent."""
		flow = WatchlistFlow("test_strategy")
		input_data = {"tickers": ["AAPL"], "timeframe": "1h"}
		result = flow.process(input_data)

		# Verify strategy data was stored in context
		strategy_input = flow.context.get("strategy_input")
		assert strategy_input == input_data

	def test_watchlist_flow_process_stores_strategy_result(self):
		"""Test that process stores strategy result in context."""
		flow = WatchlistFlow("test_strategy")
		input_data = {"tickers": ["AAPL", "GOOGL"]}
		flow.process(input_data)

		strategy_result = flow.context.get("strategy_result")
		assert strategy_result is not None
		assert strategy_result.get("status") == "success"

	def test_watchlist_flow_process_returns_correct_structure(self):
		"""Test that process returns correct response structure."""
		flow = WatchlistFlow("test_strategy")
		input_data = {"tickers": ["AAPL"]}
		result = flow.process(input_data)

		assert isinstance(result, dict)
		assert "status" in result
		assert "watchlist" in result
		assert "strategy" in result

	def test_watchlist_flow_multiple_executions(self):
		"""Test that multiple process calls work correctly."""
		flow = WatchlistFlow("test_strategy")

		result1 = flow.process({"tickers": ["AAPL"]})
		assert result1.get("status") == "success"

		result2 = flow.process({"tickers": ["GOOGL", "MSFT"]})
		assert result2.get("status") == "success"

	def test_watchlist_flow_context_isolation(self):
		"""Test that different flows have isolated contexts."""
		flow1 = WatchlistFlow("strategy1")
		flow2 = WatchlistFlow("strategy2")

		flow1.process({"tickers": ["AAPL"]})
		flow2.process({"tickers": ["GOOGL"]})

		assert flow1.context is not flow2.context
		assert flow1.steps[0].agent_class == flow2.steps[0].agent_class

	def test_watchlist_flow_with_complex_input(self):
		"""Test process with complex nested input data."""
		flow = WatchlistFlow("complex_strategy")
		input_data = {
			"tickers": ["AAPL", "GOOGL", "MSFT"],
			"timeframe": "1h",
			"indicators": {
				"rsi": {"period": 14, "threshold": 30},
				"macd": {"fast": 12, "slow": 26},
			},
			"filters": {
				"min_volume": 1000000,
				"max_price": 500,
			},
		}

		result = flow.process(input_data)
		assert result.get("status") == "success"

	def test_watchlist_flow_process_with_empty_ticker_list(self):
		"""Test process with empty ticker list."""
		flow = WatchlistFlow("test_strategy")
		input_data = {"tickers": []}
		result = flow.process(input_data)

		# Empty ticker list should fail
		assert result.get("status") == "error"

	def test_watchlist_flow_strategy_name_preservation(self):
		"""Test that strategy name is correctly preserved."""
		strategy_name = "my_test_strategy_v1"
		flow = WatchlistFlow(strategy_name)

		result = flow.process({"tickers": ["AAPL"]})
		assert result.get("strategy") == strategy_name

	def test_watchlist_flow_with_special_characters_strategy_name(self):
		"""Test flow with strategy name containing special characters."""
		flow = WatchlistFlow("strategy-v2_test.1")
		assert flow.strategy_name == "strategy-v2_test.1"
		result = flow.process({"tickers": ["GOOGL"]})
		assert result.get("strategy") == "strategy-v2_test.1"

	def test_watchlist_flow_process_sequential_calls(self):
		"""Test that sequential process calls don't interfere."""
		flow = WatchlistFlow("test_strategy")

		result1 = flow.process({"tickers": ["AAPL"]})
		assert result1.get("status") == "success"

		# Second call should work independently
		result2 = flow.process({"tickers": ["GOOGL", "MSFT", "AMZN"]})
		assert result2.get("status") == "success"

	def test_watchlist_flow_response_has_watchlist_field(self):
		"""Test that response contains watchlist field for valid inputs."""
		flow = WatchlistFlow("test_strategy")

		# Test with valid inputs
		for input_data in [{"tickers": ["AAPL"]}, {"tickers": ["GOOGL", "MSFT"]}]:
			result = flow.process(input_data)
			assert "watchlist" in result

	def test_watchlist_flow_initialization_with_different_strategies(self):
		"""Test flow initialization with different strategy names."""
		strategies = ["ta_cac_1", "ml_nasdaq_2", "hybrid_etf_3"]

		for strategy in strategies:
			flow = WatchlistFlow(strategy)
			assert flow.strategy_name == strategy
			assert flow.steps[0].agent_name == f"StrategyAgent[{strategy}]"

	def test_watchlist_flow_context_shares_between_agents(self):
		"""Test that context is shared between strategy and watchlist agents."""
		flow = WatchlistFlow("test_strategy")
		input_data = {"tickers": ["AAPL"]}

		flow.process(input_data)

		# Verify context data is accessible
		assert flow.context.get("strategy_input") is not None
		assert flow.context.get("strategy_result") is not None

	def test_watchlist_flow_process_sets_strategy_result_in_context(self):
		"""Test that strategy result is set in context for watchlist agent."""
		flow = WatchlistFlow("test_strategy")
		input_data = {"tickers": ["GOOGL", "MSFT"]}

		flow.process(input_data)

		strategy_result = flow.context.get("strategy_result")
		assert strategy_result.get("status") == "success"
		assert "output" in strategy_result

	def test_watchlist_flow_return_value_includes_strategy_name(self):
		"""Test that return value includes the strategy name."""
		flow = WatchlistFlow("my_strategy")
		result = flow.process({"tickers": ["AAPL", "GOOGL"]})

		assert result.get("strategy") == "my_strategy"

	def test_watchlist_flow_with_numeric_input_values(self):
		"""Test process with numeric values in input."""
		flow = WatchlistFlow("test_strategy")
		input_data = {
			"tickers": ["AAPL"],
			"period": 14,
			"threshold": 30.5,
			"count": 100,
		}

		result = flow.process(input_data)
		assert result.get("status") == "success"

	def test_watchlist_flow_with_list_input_values(self):
		"""Test process with list values in input."""
		flow = WatchlistFlow("test_strategy")
		input_data = {
			"tickers": ["AAPL", "GOOGL", "MSFT"],
			"signals": ["rsi", "macd", "bb"],
			"timeframes": [60, 3600, 86400],
		}

		result = flow.process(input_data)
		assert result.get("status") == "success"

	def test_watchlist_flow_successive_calls_with_different_inputs(self):
		"""Test successive calls with different inputs maintain flow state."""
		flow = WatchlistFlow("test_strategy")

		inputs = [
			{"tickers": ["AAPL"]},
			{"tickers": ["GOOGL", "MSFT"]},
			{"tickers": ["AMZN", "TSLA", "META"]},
		]

		for input_data in inputs:
			result = flow.process(input_data)
			assert result.get("status") == "success"
			assert result.get("strategy") == "test_strategy"

	def test_watchlist_flow_process_with_large_ticker_list(self):
		"""Test process with large number of tickers."""
		flow = WatchlistFlow("test_strategy")
		large_ticker_list = [f"TICK{i}" for i in range(100)]
		input_data = {"tickers": large_ticker_list}

		result = flow.process(input_data)
		assert result.get("status") == "success"
		assert "watchlist" in result

	def test_watchlist_flow_agent_names_are_unique_per_flow(self):
		"""Test that each flow instance creates unique agent names."""
		flow1 = WatchlistFlow("strategy1")
		flow2 = WatchlistFlow("strategy2")

		assert flow1.steps[0].agent_name != flow2.steps[0].agent_name
		assert flow1.context is not flow2.context
