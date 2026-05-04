"""Tests for BacktestAgent."""

import pytest
import sys
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.backtest.agent import BacktestAgent, _parse_date, _get_trading_days
from core.context import AgentContext
from core.flow import Flow


class TestBacktestAgentInitialization:
	"""Test BacktestAgent initialization."""

	def test_initialization_with_defaults(self):
		"""Test BacktestAgent initializes with default name."""
		agent = BacktestAgent()
		assert agent.name == "backtest"
		assert agent.context is not None
		assert agent.logger is not None

	def test_initialization_with_custom_name(self):
		"""Test BacktestAgent initializes with custom name."""
		agent = BacktestAgent("my_backtest")
		assert agent.name == "my_backtest"

	def test_initialization_with_context(self):
		"""Test BacktestAgent initializes with provided context."""
		context = AgentContext()
		agent = BacktestAgent("test", context=context)
		assert agent.context is context

	def test_flows_default_to_none(self):
		"""Test that flows are None by default."""
		agent = BacktestAgent()
		assert agent.pre_market_flow is None
		assert agent.market_flow is None
		assert agent.post_market_flow is None


class TestBacktestAgentFlowSetters:
	"""Test flow setter methods."""

	def test_set_premarket_flow(self):
		"""Test setting pre-market flow."""
		agent = BacktestAgent()
		flow = Mock(spec=Flow)
		agent.set_premarket_flow(flow)
		assert agent.pre_market_flow is flow

	def test_set_market_flow(self):
		"""Test setting market flow."""
		agent = BacktestAgent()
		flow = Mock(spec=Flow)
		agent.set_market_flow(flow)
		assert agent.market_flow is flow

	def test_set_postmarket_flow(self):
		"""Test setting post-market flow."""
		agent = BacktestAgent()
		flow = Mock(spec=Flow)
		agent.set_postmarket_flow(flow)
		assert agent.post_market_flow is flow


class TestBacktestAgentProcessInputValidation:
	"""Test process() input validation."""

	def test_process_missing_strategy_name(self):
		"""Test that process returns error when strategy_name is missing."""
		agent = BacktestAgent()
		result = agent.process({})
		assert result["status"] == "error"
		assert "strategy_name is required" in result["message"]

	def test_process_missing_strategy_name_with_none_input(self):
		"""Test that process returns error when input_data is None."""
		agent = BacktestAgent()
		result = agent.process(None)
		assert result["status"] == "error"
		assert "strategy_name is required" in result["message"]


class TestBacktestAgentDateResolution:
	"""Test date parsing and default resolution."""

	def test_process_date_defaults(self):
		"""Test that dates default correctly (end_date=today, start_date=today-365)."""
		agent = BacktestAgent()
		today = date.today()

		with patch("agents.backtest.agent.StrategyAgent") as mock_strategy, \
			 patch("agents.backtest.agent.DataAgent") as mock_data:
			mock_strategy.return_value.run.return_value = {"status": "success", "output": {}}
			mock_data.return_value.run.return_value = {
				"status": "success",
				"output": {},
			}
			# Mock context to return empty data_history
			agent.context.set("data_history", {})

			result = agent.process({"strategy_name": "test"})

			assert result["status"] == "error"  # Will error on no trading days
			backtest = agent.context.get("backtest")
			assert backtest is not None
			assert backtest["end_date"] == today.isoformat()
			assert backtest["start_date"] == (today - timedelta(days=365)).isoformat()

	def test_process_explicit_dates(self):
		"""Test explicit date input."""
		agent = BacktestAgent()
		start = "2023-01-01"
		end = "2023-12-31"

		with patch("agents.backtest.agent.StrategyAgent") as mock_strategy, \
			 patch("agents.backtest.agent.DataAgent") as mock_data:
			mock_strategy.return_value.run.return_value = {"status": "success", "output": {}}
			mock_data.return_value.run.return_value = {
				"status": "success",
				"output": {},
			}
			agent.context.set("data_history", {})

			result = agent.process({
				"strategy_name": "test",
				"start_date": start,
				"end_date": end,
			})

			backtest = agent.context.get("backtest")
			assert backtest["start_date"] == start
			assert backtest["end_date"] == end

	def test_process_custom_lookback_days(self):
		"""Test custom lookback_days."""
		agent = BacktestAgent()
		today = date.today()

		with patch("agents.backtest.agent.StrategyAgent") as mock_strategy, \
			 patch("agents.backtest.agent.DataAgent") as mock_data:
			mock_strategy.return_value.run.return_value = {"status": "success", "output": {}}
			mock_data.return_value.run.return_value = {
				"status": "success",
				"output": {},
			}
			agent.context.set("data_history", {})

			result = agent.process({
				"strategy_name": "test",
				"lookback_days": 100,
			})

			backtest = agent.context.get("backtest")
			expected_start = today - timedelta(days=100)
			assert backtest["start_date"] == expected_start.isoformat()


class TestBacktestAgentContext:
	"""Test context initialization and management."""

	def test_process_sets_backtest_context(self):
		"""Test that process initializes backtest context dict."""
		agent = BacktestAgent()

		with patch("agents.backtest.agent.StrategyAgent") as mock_strategy, \
			 patch("agents.backtest.agent.DataAgent") as mock_data:
			mock_strategy.return_value.run.return_value = {"status": "success", "output": {}}
			mock_data.return_value.run.return_value = {
				"status": "success",
				"output": {},
			}
			agent.context.set("data_history", {})

			result = agent.process({"strategy_name": "test_strat"})

			backtest = agent.context.get("backtest")
			assert backtest is not None
			assert backtest["strategy_name"] == "test_strat"
			assert "start_date" in backtest
			assert "end_date" in backtest
			assert isinstance(backtest["daily_results"], list)
			assert isinstance(backtest["metrics"], dict)


class TestBacktestAgentLooping:
	"""Test the main backtest loop."""

	def _create_mock_data_history(self, start_date: date, end_date: date, num_days: int):
		"""Helper to create mock data_history with trading dates."""
		dates = []
		current = start_date
		while current <= end_date and len(dates) < num_days:
			dates.append(current)
			current += timedelta(days=1)

		df = pd.DataFrame({
			"timestamp": pd.to_datetime(dates),
			"open": [100.0] * len(dates),
			"high": [101.0] * len(dates),
			"low": [99.0] * len(dates),
			"close": [100.0] * len(dates),
			"volume": [1000] * len(dates),
			"ticker": ["TEST"] * len(dates),
		})

		return {"TEST": df}

	def test_process_loops_over_trading_days(self):
		"""Test that backtest loops over trading days and calls flows."""
		agent = BacktestAgent()
		pre_market_mock = Mock(spec=Flow)
		pre_market_mock.context = None
		pre_market_mock.process = Mock(return_value={"status": "success"})

		market_mock = Mock(spec=Flow)
		market_mock.context = None
		market_mock.process = Mock(return_value={"status": "success"})

		post_market_mock = Mock(spec=Flow)
		post_market_mock.context = None
		post_market_mock.process = Mock(return_value={"status": "success"})

		agent.set_premarket_flow(pre_market_mock)
		agent.set_market_flow(market_mock)
		agent.set_postmarket_flow(post_market_mock)

		start = date(2023, 1, 1)
		end = date(2023, 1, 10)
		data_history = self._create_mock_data_history(start, end, 10)

		with patch("agents.backtest.agent.StrategyAgent") as mock_strategy, \
			 patch("agents.backtest.agent.DataAgent") as mock_data:
			mock_strategy.return_value.run.return_value = {"status": "success", "output": {}}
			mock_data.return_value.run.return_value = {
				"status": "success",
				"output": {},
			}
			agent.context.set("data_history", data_history)

			result = agent.process({
				"strategy_name": "test",
				"start_date": start,
				"end_date": end,
			})

			assert result["status"] == "success"
			# Should loop over 9 days (all but last)
			assert pre_market_mock.process.call_count == 9
			assert market_mock.process.call_count == 9
			assert post_market_mock.process.call_count == 9

	def test_process_increments_date(self):
		"""Test that current_date is incremented between pre_market and market."""
		agent = BacktestAgent()

		dates_seen = {"pre_market": [], "market": []}

		def capture_pre_market(input_data):
			dates_seen["pre_market"].append(agent.context.get("current_date"))
			return {"status": "success"}

		def capture_market(input_data):
			dates_seen["market"].append(agent.context.get("current_date"))
			return {"status": "success"}

		pre_market_mock = Mock(spec=Flow)
		pre_market_mock.context = None
		pre_market_mock.process = Mock(side_effect=capture_pre_market)

		market_mock = Mock(spec=Flow)
		market_mock.context = None
		market_mock.process = Mock(side_effect=capture_market)

		agent.set_premarket_flow(pre_market_mock)
		agent.set_market_flow(market_mock)

		start = date(2023, 1, 1)
		end = date(2023, 1, 5)
		data_history = self._create_mock_data_history(start, end, 5)

		with patch("agents.backtest.agent.StrategyAgent") as mock_strategy, \
			 patch("agents.backtest.agent.DataAgent") as mock_data:
			mock_strategy.return_value.run.return_value = {"status": "success", "output": {}}
			mock_data.return_value.run.return_value = {
				"status": "success",
				"output": {},
			}
			agent.context.set("data_history", data_history)

			result = agent.process({
				"strategy_name": "test",
				"start_date": start,
				"end_date": end,
			})

			assert result["status"] == "success"
			# Each market call should see a later date than pre_market
			for pre_date, market_date in zip(dates_seen["pre_market"], dates_seen["market"]):
				assert market_date > pre_date

	def test_process_no_flows_set(self):
		"""Test that loop runs without error when no flows are set."""
		agent = BacktestAgent()

		start = date(2023, 1, 1)
		end = date(2023, 1, 5)
		data_history = self._create_mock_data_history(start, end, 5)

		with patch("agents.backtest.agent.StrategyAgent") as mock_strategy, \
			 patch("agents.backtest.agent.DataAgent") as mock_data:
			mock_strategy.return_value.run.return_value = {"status": "success", "output": {}}
			mock_data.return_value.run.return_value = {
				"status": "success",
				"output": {},
			}
			agent.context.set("data_history", data_history)

			result = agent.process({
				"strategy_name": "test",
				"start_date": start,
				"end_date": end,
			})

			assert result["status"] == "success"
			backtest = result["output"]
			assert backtest["days_processed"] == 4

	def test_process_no_data_returns_error(self):
		"""Test that process returns error when no trading days found."""
		agent = BacktestAgent()

		with patch("agents.backtest.agent.StrategyAgent") as mock_strategy, \
			 patch("agents.backtest.agent.DataAgent") as mock_data:
			mock_strategy.return_value.run.return_value = {"status": "success", "output": {}}
			mock_data.return_value.run.return_value = {
				"status": "success",
				"output": {},
			}
			agent.context.set("data_history", {})  # Empty data

			result = agent.process({"strategy_name": "test"})

			assert result["status"] == "error"
			assert "No trading days found" in result["message"]

	def test_process_fills_daily_results(self):
		"""Test that daily_results are populated with dates."""
		agent = BacktestAgent()

		start = date(2023, 1, 1)
		end = date(2023, 1, 5)
		data_history = self._create_mock_data_history(start, end, 5)

		with patch("agents.backtest.agent.StrategyAgent") as mock_strategy, \
			 patch("agents.backtest.agent.DataAgent") as mock_data:
			mock_strategy.return_value.run.return_value = {"status": "success", "output": {}}
			mock_data.return_value.run.return_value = {
				"status": "success",
				"output": {},
			}
			agent.context.set("data_history", data_history)

			result = agent.process({
				"strategy_name": "test",
				"start_date": start,
				"end_date": end,
			})

			assert result["status"] == "success"
			backtest = result["output"]
			assert len(backtest["daily_results"]) == 4
			for day_result in backtest["daily_results"]:
				assert "date" in day_result


class TestHelperFunctions:
	"""Test helper functions."""

	def test_parse_date_none(self):
		"""Test _parse_date with None."""
		assert _parse_date(None) is None

	def test_parse_date_date_object(self):
		"""Test _parse_date with date object."""
		d = date(2023, 1, 1)
		assert _parse_date(d) == d

	def test_parse_date_string(self):
		"""Test _parse_date with string."""
		result = _parse_date("2023-01-15")
		assert result == date(2023, 1, 15)

	def test_get_trading_days_empty(self):
		"""Test _get_trading_days with empty data_history."""
		result = _get_trading_days({}, date(2023, 1, 1), date(2023, 12, 31))
		assert result == []

	def test_get_trading_days_filtering(self):
		"""Test _get_trading_days filters by date range."""
		df = pd.DataFrame({
			"timestamp": pd.to_datetime([
				"2023-01-01", "2023-01-02", "2023-01-03",
				"2023-02-01", "2023-03-01",
			]),
		})
		data_history = {"TEST": df}

		result = _get_trading_days(
			data_history,
			date(2023, 1, 2),
			date(2023, 2, 15),
		)

		expected = [date(2023, 1, 2), date(2023, 1, 3), date(2023, 2, 1)]
		assert result == expected

	def test_get_trading_days_ordering(self):
		"""Test _get_trading_days returns sorted dates."""
		df = pd.DataFrame({
			"timestamp": pd.to_datetime([
				"2023-01-05", "2023-01-01", "2023-01-03",
				"2023-01-02", "2023-01-04",
			]),
		})
		data_history = {"TEST": df}

		result = _get_trading_days(
			data_history,
			date(2023, 1, 1),
			date(2023, 1, 5),
		)

		assert result == [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3),
						   date(2023, 1, 4), date(2023, 1, 5)]
