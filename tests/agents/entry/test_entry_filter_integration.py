"""Integration tests for EntryFilterAgent with real strategy configurations."""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

from src.agents.entry.sub_agents import EntryFilterAgent
from src.core.context import AgentContext


class TestEntryFilterIntegration(unittest.TestCase):
	"""Integration tests for EntryFilterAgent with real strategies."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryFilterAgent("integration_test", self.context)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_single_etf_filter_good_conditions(self, mock_strategy_manager_class):
		"""Test single_etf filter with good market conditions.

		Formula: sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > 20

		Good conditions:
		- Heikin-Ashi green on previous bar
		- Price above EMA-20
		- ADX > 20 (strong trend)
		"""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > 20",
							"description": "Heikin-Ashi green + price above EMA + strong ADX"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Create realistic market data with good conditions
		df = pd.DataFrame({
			"close": [104.5, 103.8, 103.2, 102.5, 101.0],  # Price uptrend
			"sha_10_green": [1, 1, 1, 1, 1],  # Heikin-Ashi green
			"ema_20": [100.0, 100.5, 101.0, 101.5, 102.0],  # EMA below price
			"adx_14": [25, 26, 27, 28, 29],  # Strong ADX
		})

		# Create recommendations
		recommendations = [
			{
				"ticker": "SPY",
				"composite_score": 85.0,
				"entry_score": 80.0,
				"timing_score": 75.0,
				"rr_ratio": 2.0,
				"entry_price": 104.5,
				"stop_loss": 99.0,
				"take_profit": 114.0,
				"recommendation": "BUY"
			}
		]

		self.context.set("strategy_name", "single_etf")
		self.context.set("data_history", {"SPY": df})
		self.context.set("entry_recommendations", recommendations)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["passed_count"], 1)
		self.assertEqual(result["output"]["filtered_count"], 0)
		self.assertEqual(len(self.context.get("entry_recommendations")), 1)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_single_etf_filter_poor_adx(self, mock_strategy_manager_class):
		"""Test single_etf filter blocks when ADX is weak.

		Formula requires ADX > 20, this data has ADX = 15
		"""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > 20",
							"description": "Heikin-Ashi green + price above EMA + strong ADX"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Market data with weak ADX (below 20)
		df = pd.DataFrame({
			"close": [104.5, 103.8, 103.2, 102.5, 101.0],
			"sha_10_green": [1, 1, 1, 1, 1],
			"ema_20": [100.0, 100.5, 101.0, 101.5, 102.0],
			"adx_14": [15, 16, 17, 18, 19],  # Weak ADX - below 20
		})

		recommendations = [
			{
				"ticker": "SPY",
				"composite_score": 75.0,
				"entry_score": 80.0,
				"timing_score": 75.0,
				"rr_ratio": 1.5,
			}
		]

		self.context.set("strategy_name", "single_etf")
		self.context.set("data_history", {"SPY": df})
		self.context.set("entry_recommendations", recommendations)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["filtered_count"], 1)
		self.assertEqual(result["output"]["passed_count"], 0)
		self.assertEqual(len(self.context.get("entry_recommendations")), 0)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_single_etf_filter_price_below_ema(self, mock_strategy_manager_class):
		"""Test single_etf filter blocks when price is below EMA-20."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > 20",
							"description": "Heikin-Ashi green + price above EMA + strong ADX"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Price below EMA-20
		df = pd.DataFrame({
			"close": [99.0, 99.5, 100.0, 100.5, 101.0],  # Price below EMA
			"sha_10_green": [1, 1, 1, 1, 1],
			"ema_20": [101.0, 101.5, 102.0, 102.5, 103.0],  # EMA above price
			"adx_14": [25, 26, 27, 28, 29],
		})

		recommendations = [
			{
				"ticker": "SPY",
				"composite_score": 75.0,
				"entry_score": 80.0,
				"timing_score": 75.0,
				"rr_ratio": 1.5,
			}
		]

		self.context.set("strategy_name", "single_etf")
		self.context.set("data_history", {"SPY": df})
		self.context.set("entry_recommendations", recommendations)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["filtered_count"], 1)
		self.assertEqual(result["output"]["passed_count"], 0)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_single_etf_filter_sha_red(self, mock_strategy_manager_class):
		"""Test single_etf filter blocks when Heikin-Ashi is red."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > 20",
							"description": "Heikin-Ashi green + price above EMA + strong ADX"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Heikin-Ashi red on previous bar
		df = pd.DataFrame({
			"close": [104.5, 103.8, 103.2, 102.5, 101.0],
			"sha_10_green": [0, 0, 0, 0, 0],  # All red - previous bar is red
			"ema_20": [100.0, 100.5, 101.0, 101.5, 102.0],
			"adx_14": [25, 26, 27, 28, 29],
		})

		recommendations = [
			{
				"ticker": "SPY",
				"composite_score": 75.0,
				"entry_score": 80.0,
				"timing_score": 75.0,
				"rr_ratio": 1.5,
			}
		]

		self.context.set("strategy_name", "single_etf")
		self.context.set("data_history", {"SPY": df})
		self.context.set("entry_recommendations", recommendations)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["filtered_count"], 1)
		self.assertEqual(result["output"]["passed_count"], 0)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_single_etf_filter_multiple_recommendations(self, mock_strategy_manager_class):
		"""Test single_etf filter on multiple recommendations with mixed results."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > 20",
							"description": "Heikin-Ashi green + price above EMA + strong ADX"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Good conditions
		df_good = pd.DataFrame({
			"close": [104.5, 103.8, 103.2, 102.5, 101.0],
			"sha_10_green": [1, 1, 1, 1, 1],
			"ema_20": [100.0, 100.5, 101.0, 101.5, 102.0],
			"adx_14": [25, 26, 27, 28, 29],
		})

		# Weak ADX
		df_weak_adx = pd.DataFrame({
			"close": [104.5, 103.8, 103.2, 102.5, 101.0],
			"sha_10_green": [1, 1, 1, 1, 1],
			"ema_20": [100.0, 100.5, 101.0, 101.5, 102.0],
			"adx_14": [15, 16, 17, 18, 19],
		})

		# Price below EMA
		df_price_low = pd.DataFrame({
			"close": [99.0, 99.5, 100.0, 100.5, 101.0],
			"sha_10_green": [1, 1, 1, 1, 1],
			"ema_20": [101.0, 101.5, 102.0, 102.5, 103.0],
			"adx_14": [25, 26, 27, 28, 29],
		})

		recommendations = [
			{"ticker": "GOOD", "composite_score": 85.0},
			{"ticker": "WEAK_ADX", "composite_score": 80.0},
			{"ticker": "PRICE_LOW", "composite_score": 75.0},
		]

		self.context.set("strategy_name", "single_etf")
		self.context.set("data_history", {
			"GOOD": df_good,
			"WEAK_ADX": df_weak_adx,
			"PRICE_LOW": df_price_low,
		})
		self.context.set("entry_recommendations", recommendations)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Only GOOD should pass
		self.assertEqual(result["output"]["passed_count"], 1)
		self.assertEqual(result["output"]["filtered_count"], 2)

		# Verify context was updated
		filtered_recs = self.context.get("entry_recommendations")
		self.assertEqual(len(filtered_recs), 1)
		self.assertEqual(filtered_recs[0]["ticker"], "GOOD")

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_single_etf_filter_logging(self, mock_strategy_manager_class):
		"""Test that filter logging is informative."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > 20",
							"description": "Heikin-Ashi green + price above EMA + strong ADX"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		df = pd.DataFrame({
			"close": [104.5, 103.8, 103.2, 102.5, 101.0],
			"sha_10_green": [1, 1, 1, 1, 1],
			"ema_20": [100.0, 100.5, 101.0, 101.5, 102.0],
			"adx_14": [25, 26, 27, 28, 29],
		})

		recommendations = [
			{"ticker": "SPY", "composite_score": 85.0},
		]

		self.context.set("strategy_name", "single_etf")
		self.context.set("data_history", {"SPY": df})
		self.context.set("entry_recommendations", recommendations)

		# Mock the logger to track calls
		with patch.object(self.agent, "logger") as mock_logger:
			result = self.agent.process({})

			# Verify formula was logged
			debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
			info_calls = [str(call) for call in mock_logger.info.call_args_list]

			# Should log the formula (check for Formula or entry_filter keyword)
			formula_logged = any("Formula:" in str(call) or "entry_filter" in str(call).lower() for call in debug_calls)
			self.assertTrue(formula_logged, "Formula should be logged in debug")

			# Should log summary with results
			summary_logged = any("passed" in str(call).lower() or "results" in str(call).lower()
									 for call in info_calls)
			self.assertTrue(summary_logged, "Summary should be logged in info")


if __name__ == "__main__":
	unittest.main()
