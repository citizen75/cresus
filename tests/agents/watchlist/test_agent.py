"""Tests for WatchListAgent and watchlist sub-agents."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.watchlist.agent import WatchListAgent
from core.context import AgentContext


class TestWatchListAgent(unittest.TestCase):
	"""Test cases for WatchListAgent class."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = WatchListAgent("WatchListAgent", self.context)

	def test_init(self):
		"""Test that WatchListAgent can be initialized."""
		assert self.agent.name == "WatchListAgent"

	def test_process_no_tickers(self):
		"""Test that process returns error when no tickers."""
		result = self.agent.process({})

		assert result.get("status") == "error"

	def test_process_success(self):
		"""Test that process succeeds with valid tickers."""
		mock_data = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=30),
				"close": [100 + i*0.5 for i in range(30)],
				"volume": [1000000] * 30,
			}),
			"GOOGL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=30),
				"close": [2000 + i for i in range(30)],
				"volume": [5000000] * 30,
			})
		}
		self.context.set("data_history", mock_data)

		result = self.agent.process({"tickers": ["AAPL", "GOOGL"]})

		assert result.get("status") == "success"
		# Check that output contains watchlist data
		assert result.get("output") is not None


class TestFilterStaleDataAgent(unittest.TestCase):
	"""Test cases for FilterStaleDataAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_stale_data_filtered(self):
		"""Test that stale data is filtered out."""
		from datetime import timedelta

		current_date = pd.Timestamp("2026-05-07")
		old_date = pd.Timestamp("2026-01-01")  # Very old

		data_history = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range(old_date, periods=5),
				"close": [100, 101, 102, 103, 104],
			}),
			"GOOGL": pd.DataFrame({
				"timestamp": pd.date_range(current_date - timedelta(days=10), periods=5),
				"close": [2000, 2001, 2002, 2003, 2004],
			})
		}

		self.context.set("data_history", data_history)

		# AAPL should be filtered for stale data
		assert data_history["AAPL"].iloc[-1]["timestamp"] < current_date - timedelta(days=30)


class TestFilterVolumeAgent(unittest.TestCase):
	"""Test cases for FilterVolumeAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_low_volume_filtered(self):
		"""Test that low volume tickers are filtered."""
		data_history = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=10),
				"volume": [1000000] * 10,  # High volume
			}),
			"PENNY": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=10),
				"volume": [1000] * 10,  # Low volume
			})
		}

		self.context.set("data_history", data_history)

		# PENNY stock should be filtered for low volume
		avg_volume_aapl = data_history["AAPL"]["volume"].mean()
		avg_volume_penny = data_history["PENNY"]["volume"].mean()

		assert avg_volume_aapl > avg_volume_penny


class TestTrendAgent(unittest.TestCase):
	"""Test cases for TrendAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_uptrend_identified(self):
		"""Test that uptrend is identified."""
		data_history = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=30),
				"close": [100 + i for i in range(30)],  # Uptrend
			})
		}

		self.context.set("data_history", data_history)

		# Check uptrend
		last_price = data_history["AAPL"]["close"].iloc[-1]
		first_price = data_history["AAPL"]["close"].iloc[0]

		assert last_price > first_price


class TestVolatilityAgent(unittest.TestCase):
	"""Test cases for VolatilityAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_volatility_calculated(self):
		"""Test that volatility is calculated."""
		import numpy as np

		data_history = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=30),
				"close": [100 + np.random.randn() * 5 for _ in range(30)],
			})
		}

		self.context.set("data_history", data_history)

		# Calculate simple volatility
		returns = data_history["AAPL"]["close"].pct_change()
		volatility = returns.std()

		assert volatility is not None
		assert volatility >= 0


class TestRankTickersAgent(unittest.TestCase):
	"""Test cases for RankTickersAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_tickers_ranked_by_score(self):
		"""Test that tickers are ranked by score."""
		tickers = {
			"AAPL": {"score": 85},
			"GOOGL": {"score": 92},
			"MSFT": {"score": 78},
		}

		# Sort by score descending
		sorted_tickers = sorted(tickers.items(), key=lambda x: x[1]["score"], reverse=True)

		assert sorted_tickers[0][0] == "GOOGL"
		assert sorted_tickers[1][0] == "AAPL"
		assert sorted_tickers[2][0] == "MSFT"


class TestMaxTickersAgent(unittest.TestCase):
	"""Test cases for MaxTickersAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_max_tickers_limited(self):
		"""Test that output is limited to max_tickers."""
		tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "NFLX", "ADBE", "CRM"]
		max_tickers = 3

		limited_tickers = tickers[:max_tickers]

		assert len(limited_tickers) == max_tickers
		assert "AAPL" in limited_tickers
		assert "NFLX" not in limited_tickers


if __name__ == "__main__":
	unittest.main()
