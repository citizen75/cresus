"""Tests for entry analysis agents."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

from src.agents.entry.agent import EntryAgent
from src.agents.entry.sub_agents import EntryScoreAgent, EntryTimingAgent, EntryRRAgent
from src.core.context import AgentContext


class TestEntryScoreAgent(unittest.TestCase):
	"""Test entry score calculation."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryScoreAgent("test_score", self.context)

	def test_initialization(self):
		"""Test agent initialization."""
		self.assertEqual(self.agent.name, "test_score")
		self.assertIsNotNone(self.agent.context)

	def test_process_no_watchlist(self):
		"""Test process with no watchlist in context."""
		result = self.agent.process({})
		self.assertEqual(result["status"], "error")
		self.assertIn("watchlist", result["message"].lower())

	def test_calculate_entry_score_with_rsi(self):
		"""Test entry score calculation with RSI."""
		row = pd.Series({
			"close": 100,
			"rsi_14": 25,  # Oversold, should add 20 points
			"ema_20": 95,
			"ema_50": 90,
		})

		score = self.agent._calculate_entry_score(row)
		# Base 50 + 20 (RSI oversold) + 10 (EMA20 > EMA50) + 10 (price > EMA20) = 90
		self.assertGreater(score, 70)
		self.assertLessEqual(score, 100)

	def test_calculate_entry_score_with_adx(self):
		"""Test entry score calculation with ADX trend."""
		row = pd.Series({
			"close": 100,
			"rsi_14": 50,
			"adx_20": 30,  # Strong trend
			"ema_20": 99,
			"ema_50": 95,
		})

		score = self.agent._calculate_entry_score(row)
		self.assertGreater(score, 50)

	def test_calculate_entry_score_overbought(self):
		"""Test score reduction when overbought."""
		row = pd.Series({
			"close": 100,
			"rsi_14": 75,  # Overbought, should subtract points
		})

		score = self.agent._calculate_entry_score(row)
		self.assertLess(score, 50)

	def test_process_with_watchlist(self):
		"""Test process with valid watchlist and data."""
		# Create mock data
		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104],
			"rsi_14": [45, 50, 55, 60, 65],
			"ema_20": [98, 99, 100, 101, 102],
			"ema_50": [95, 96, 97, 98, 99],
			"adx_20": [20, 22, 25, 28, 30],
		})

		watchlist = ["TICKER1", "TICKER2"]
		data_history = {
			"TICKER1": df.copy(),
			"TICKER2": df.copy(),
		}

		self.context.set("watchlist", watchlist)
		self.context.set("data_history", data_history)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["tickers_scored"], 2)
		self.assertIn("average_score", result["output"])


class TestEntryTimingAgent(unittest.TestCase):
	"""Test entry timing calculation."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryTimingAgent("test_timing", self.context)

	def test_initialization(self):
		"""Test agent initialization."""
		self.assertEqual(self.agent.name, "test_timing")

	def test_calculate_timing_ideal_pullback(self):
		"""Test timing score with ideal pullback (5-15%)."""
		df = pd.DataFrame({
			"close": [100, 102, 104, 106, 105, 104, 103, 102, 101, 100],
			"high": [100, 102, 104, 106, 107, 105, 104, 103, 102, 100],
			"low": [98, 100, 102, 104, 105, 104, 103, 102, 101, 99],
			"volume": [1000000] * 10,
		})

		score = self.agent._calculate_timing_score(df)
		# Should have good score with pullback from recent high
		self.assertGreater(score, 50)

	def test_calculate_timing_no_pullback(self):
		"""Test timing score near all-time high (risky)."""
		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
			"high": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
			"low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
			"volume": [1000000] * 10,
		})

		score = self.agent._calculate_timing_score(df)
		# Near all-time high with uptrend, score should be moderate
		self.assertGreater(score, 50)

	def test_calculate_timing_uptrend(self):
		"""Test timing score with uptrend formation."""
		df = pd.DataFrame({
			"close": [100, 99, 98, 99, 100, 101, 102],
			"high": [102, 101, 100, 101, 102, 103, 104],
			"low": [98, 97, 96, 97, 98, 99, 100],
			"volume": [1000000] * 7,
		})

		score = self.agent._calculate_timing_score(df)
		# Uptrend with good timing should have decent score
		self.assertGreater(score, 50)


class TestEntryRRAgent(unittest.TestCase):
	"""Test risk/reward ratio calculation."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryRRAgent("test_rr", self.context)

	def test_calculate_rr_basic(self):
		"""Test basic RR calculation."""
		df = pd.DataFrame({
			"close": [100, 102, 101, 103, 102, 101, 100, 99, 98, 97],
			"high": [100, 102, 101, 103, 102, 101, 100, 99, 98, 97],
			"low": [98, 100, 99, 101, 100, 99, 98, 97, 96, 95],
			"atr_14": [2] * 10,
		})

		metrics = self.agent._calculate_rr(df)

		self.assertIsNotNone(metrics)
		self.assertIn("rr_ratio", metrics)
		self.assertIn("stop_loss", metrics)
		self.assertIn("take_profit", metrics)
		self.assertGreater(metrics["rr_ratio"], 0)

	def test_calculate_rr_good_ratio(self):
		"""Test RR calculation with good ratio."""
		df = pd.DataFrame({
			"close": [100, 105, 104, 103, 102, 101, 100, 99, 98, 97],
			"high": [100, 105, 104, 103, 102, 101, 100, 99, 98, 107],
			"low": [97, 105, 104, 103, 102, 101, 100, 99, 98, 97],
		})

		metrics = self.agent._calculate_rr(df)

		self.assertIsNotNone(metrics)
		# Should have positive RR ratio
		self.assertGreater(metrics["rr_ratio"], 0.5)

	def test_process_with_watchlist(self):
		"""Test process with watchlist data."""
		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 100, 99],
			"high": [100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 100, 99],
			"low": [98, 99, 100, 101, 102, 103, 102, 101, 100, 99, 98, 97],
		})

		watchlist = ["TICKER1"]
		data_history = {"TICKER1": df.copy()}

		self.context.set("watchlist", watchlist)
		self.context.set("data_history", data_history)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertGreaterEqual(result["output"]["tickers_evaluated"], 0)


class TestEntryAgent(unittest.TestCase):
	"""Test main entry analysis agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryAgent("test_entry", self.context)

	def test_initialization(self):
		"""Test agent initialization."""
		self.assertEqual(self.agent.name, "test_entry")

	def test_process_no_watchlist(self):
		"""Test process with no watchlist."""
		result = self.agent.process({})
		self.assertEqual(result["status"], "error")

	def test_calculate_composite_score(self):
		"""Test composite score calculation."""
		rr_data = {"rr_ratio": 2.0}

		score = self.agent._calculate_composite_score(
			entry_score=80,
			timing_score=75,
			rr_data=rr_data
		)

		self.assertGreater(score, 0)
		self.assertLessEqual(score, 100)

	def test_get_recommendation_level(self):
		"""Test recommendation level assignment."""
		self.assertEqual(self.agent._get_recommendation_level(90), "STRONG BUY")
		self.assertEqual(self.agent._get_recommendation_level(70), "BUY")
		self.assertEqual(self.agent._get_recommendation_level(50), "HOLD")
		self.assertEqual(self.agent._get_recommendation_level(40), "WAIT")
		self.assertEqual(self.agent._get_recommendation_level(20), "SKIP")

	def test_create_recommendations(self):
		"""Test recommendation creation."""
		watchlist = ["TICKER1", "TICKER2"]
		entry_scores = {"TICKER1": 80, "TICKER2": 60}
		timing_scores = {"TICKER1": 75, "TICKER2": 50}
		rr_metrics = {
			"TICKER1": {
				"rr_ratio": 2.0,
				"entry_price": 100,
				"stop_loss": 95,
				"take_profit": 110,
				"risk_pct": 5,
				"reward_pct": 10,
			},
			"TICKER2": {
				"rr_ratio": 1.5,
				"entry_price": 100,
				"stop_loss": 96,
				"take_profit": 108,
				"risk_pct": 4,
				"reward_pct": 8,
			},
		}

		recs = self.agent._create_recommendations(
			watchlist, entry_scores, timing_scores, rr_metrics
		)

		self.assertEqual(len(recs), 2)
		# Should be sorted by composite score
		self.assertGreaterEqual(
			recs[0]["composite_score"],
			recs[1]["composite_score"]
		)

	def test_get_top_opportunities(self):
		"""Test top opportunities extraction."""
		recommendations = [
			{"ticker": "T1", "composite_score": 90, "recommendation": "STRONG BUY", "rr_ratio": 2.0},
			{"ticker": "T2", "composite_score": 80, "recommendation": "BUY", "rr_ratio": 1.8},
			{"ticker": "T3", "composite_score": 70, "recommendation": "BUY", "rr_ratio": 1.5},
		]

		top = self.agent._get_top_opportunities(recommendations, 2)

		self.assertEqual(len(top), 2)
		self.assertEqual(top[0]["rank"], 1)
		self.assertEqual(top[1]["rank"], 2)
		self.assertEqual(top[0]["ticker"], "T1")

	@patch("src.agents.entry.agent.Flow")
	def test_process_with_mock_flow(self, mock_flow_class):
		"""Test process with mocked flow."""
		# Setup mock flow
		mock_flow = MagicMock()
		mock_flow.process.return_value = {
			"status": "success",
			"execution_history": []
		}
		mock_flow_class.return_value = mock_flow

		# Setup context
		watchlist = ["TICKER1"]
		self.context.set("watchlist", watchlist)
		self.context.set("entry_scores", {"TICKER1": 75})
		self.context.set("timing_scores", {"TICKER1": 70})
		self.context.set("rr_metrics", {
			"TICKER1": {
				"rr_ratio": 1.5,
				"entry_price": 100,
				"stop_loss": 95,
				"take_profit": 110,
				"risk_pct": 5,
				"reward_pct": 10,
			}
		})

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertIn("recommendations", result["output"])


if __name__ == "__main__":
	unittest.main()
