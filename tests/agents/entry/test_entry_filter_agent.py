"""Tests for EntryFilterAgent."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

from src.agents.entry.sub_agents import EntryFilterAgent
from src.core.context import AgentContext


class TestEntryFilterAgent(unittest.TestCase):
	"""Test entry filter agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryFilterAgent("test_filter", self.context)

	def test_initialization(self):
		"""Test agent initialization."""
		self.assertEqual(self.agent.name, "test_filter")
		self.assertIsNotNone(self.agent.context)

	def test_process_no_recommendations(self):
		"""Test process with no recommendations."""
		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {})
		self.context.set("entry_recommendations", [])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["filtered_count"], 0)
		self.assertEqual(result["output"]["passed_count"], 0)

	def test_process_missing_strategy_name(self):
		"""Test process with missing strategy_name in context."""
		self.context.set("data_history", {})
		self.context.set("entry_recommendations", [{"ticker": "TEST"}])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Should pass through all recommendations
		self.assertEqual(result["output"]["passed_count"], 1)
		self.assertEqual(result["output"]["filtered_count"], 0)

	def test_process_missing_data_history(self):
		"""Test process with missing data_history in context."""
		self.context.set("strategy_name", "test_strategy")
		self.context.set("entry_recommendations", [{"ticker": "TEST"}])

		result = self.agent.process({})

		self.assertEqual(result["status"], "error")
		self.assertIn("data_history", result["message"])

	def test_process_missing_entry_recommendations(self):
		"""Test process with missing entry_recommendations in context."""
		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {})

		result = self.agent.process({})

		self.assertEqual(result["status"], "error")
		self.assertIn("entry_recommendations", result["message"])

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_process_strategy_load_error(self, mock_strategy_manager_class):
		"""Test process when strategy loading fails."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "error",
			"message": "Strategy not found"
		}
		mock_strategy_manager_class.return_value = mock_manager

		self.context.set("strategy_name", "nonexistent_strategy")
		self.context.set("data_history", {})
		self.context.set("entry_recommendations", [{"ticker": "TEST"}])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Should pass through all recommendations on strategy load error
		self.assertEqual(result["output"]["passed_count"], 1)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_process_no_entry_filter_config(self, mock_strategy_manager_class):
		"""Test process when entry_filter is not configured."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {}  # No entry_filter
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {})
		self.context.set("entry_recommendations", [{"ticker": "TEST"}])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Should pass through all recommendations
		self.assertEqual(result["output"]["passed_count"], 1)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_process_pass_all_recommendations(self, mock_strategy_manager_class):
		"""Test filtering when all recommendations pass."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 0"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Create test data
		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104],
		})

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {
			"TEST1": df.copy(),
			"TEST2": df.copy(),
		})
		self.context.set("entry_recommendations", [
			{"ticker": "TEST1", "score": 80},
			{"ticker": "TEST2", "score": 75},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["passed_count"], 2)
		self.assertEqual(result["output"]["filtered_count"], 0)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_process_filter_some_recommendations(self, mock_strategy_manager_class):
		"""Test filtering when some recommendations are blocked."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 101"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Create test data
		df_pass = pd.DataFrame({
			"close": [104, 103, 102, 101, 100],  # Most recent is 104
		})
		df_fail = pd.DataFrame({
			"close": [100, 99, 98, 97, 96],  # Most recent is 100
		})

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {
			"PASS": df_pass,
			"FAIL": df_fail,
		})
		self.context.set("entry_recommendations", [
			{"ticker": "PASS", "score": 80},
			{"ticker": "FAIL", "score": 75},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["passed_count"], 1)
		self.assertEqual(result["output"]["filtered_count"], 1)

		# Verify context was updated
		filtered_recs = self.context.get("entry_recommendations")
		self.assertEqual(len(filtered_recs), 1)
		self.assertEqual(filtered_recs[0]["ticker"], "PASS")

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_process_no_data_for_ticker(self, mock_strategy_manager_class):
		"""Test filtering when ticker has no data."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 0"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {})  # No data
		self.context.set("entry_recommendations", [
			{"ticker": "TEST", "score": 80},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Should pass through recommendations without data
		self.assertEqual(result["output"]["passed_count"], 1)
		self.assertEqual(result["output"]["filtered_count"], 0)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_process_empty_data_for_ticker(self, mock_strategy_manager_class):
		"""Test filtering when ticker data is empty."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 0"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Empty dataframe
		empty_df = pd.DataFrame()

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {
			"TEST": empty_df,
		})
		self.context.set("entry_recommendations", [
			{"ticker": "TEST", "score": 80},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Should pass through recommendations with empty data
		self.assertEqual(result["output"]["passed_count"], 1)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	@patch("src.agents.entry.sub_agents.entry_filter_agent.evaluate")
	def test_process_formula_evaluation_error(self, mock_evaluate, mock_strategy_manager_class):
		"""Test filtering when formula evaluation raises an error."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "invalid_indicator[0] > 0"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Mock evaluate to raise an error
		mock_evaluate.side_effect = ValueError("Indicator 'invalid_indicator' not found")

		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104],
		})

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {
			"TEST": df,
		})
		self.context.set("entry_recommendations", [
			{"ticker": "TEST", "score": 80},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Blocked on formula error
		self.assertEqual(result["output"]["filtered_count"], 1)
		self.assertEqual(result["output"]["passed_count"], 0)
		# Error should be in output
		self.assertIn("error_tickers", result["output"])
		self.assertEqual(len(result["output"]["error_tickers"]), 1)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	@patch("src.agents.entry.sub_agents.entry_filter_agent.evaluate")
	def test_missing_indicator_error_message(self, mock_evaluate, mock_strategy_manager_class):
		"""Test that missing indicator errors show available columns."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_red[-2] == 1"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Mock evaluate to raise an error about missing indicator
		mock_evaluate.side_effect = ValueError("Unexpected token: Token(INDICATOR, 'sha_10_red[-2]')")

		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104],
			"open": [99, 100, 101, 102, 103],
			"ema_20": [98, 99, 100, 101, 102],
		})

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {"TEST": df})
		self.context.set("entry_recommendations", [{"ticker": "TEST"}])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Blocked on formula error
		self.assertEqual(result["output"]["filtered_count"], 1)
		# Error message should mention missing indicator and available columns
		error_msg = result["output"]["error_tickers"][0]
		self.assertIn("sha_10_red", error_msg)
		self.assertIn("Available columns", error_msg)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	@patch("src.agents.entry.sub_agents.entry_filter_agent.evaluate")
	def test_syntax_error_detection(self, mock_evaluate, mock_strategy_manager_class):
		"""Test that syntax errors (missing operators) are detected and reported clearly."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_green[0] == 1 sha_10_red[-1] == 0"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Mock evaluate to raise a syntax error
		mock_evaluate.side_effect = ValueError("Unexpected token: Token(INDICATOR, 'sha_10_red[-1]')")

		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104],
			"sha_10_green": [1, 1, 1, 1, 1],
			"sha_10_red": [0, 0, 0, 0, 0],
		})

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {"TEST": df})
		self.context.set("entry_recommendations", [{"ticker": "TEST"}])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["filtered_count"], 1)
		# Error message should mention syntax error and missing operators
		error_msg = result["output"]["error_tickers"][0]
		self.assertIn("syntax error", error_msg.lower())
		self.assertIn("operator", error_msg.lower())

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	@patch("src.agents.entry.sub_agents.entry_filter_agent.evaluate")
	def test_process_dsl_formula_with_shift_notation(self, mock_evaluate, mock_strategy_manager_class):
		"""Test filtering with DSL formula using shift notation."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_green[-1] == 1 and ema_20[0] < close[0]"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Mock evaluate to return True
		mock_evaluate.return_value = True

		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104],
			"sha_10_green": [1, 1, 1, 1, 1],
			"ema_20": [99, 100, 101, 102, 103],
		})

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {
			"TEST": df,
		})
		self.context.set("entry_recommendations", [
			{"ticker": "TEST", "score": 80},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["passed_count"], 1)
		self.assertEqual(result["output"]["filtered_count"], 0)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_process_data_shorter_than_5_days(self, mock_strategy_manager_class):
		"""Test filtering when data has fewer than 5 days."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 0"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Only 2 days of data
		df = pd.DataFrame({
			"close": [104, 103],
		})

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {
			"TEST": df,
		})
		self.context.set("entry_recommendations", [
			{"ticker": "TEST", "score": 80},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Should still work with less than 5 days
		self.assertEqual(result["output"]["passed_count"], 1)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_process_mixed_pass_fail_with_errors(self, mock_strategy_manager_class):
		"""Test filtering with mix of passing, failing, and error cases."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 101"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		df_pass = pd.DataFrame({
			"close": [104, 103, 102, 101, 100],
		})
		df_fail = pd.DataFrame({
			"close": [100, 99, 98, 97, 96],
		})
		df_no_data = pd.DataFrame({})

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {
			"PASS": df_pass,
			"FAIL": df_fail,
			"NO_DATA": df_no_data,
		})
		self.context.set("entry_recommendations", [
			{"ticker": "PASS", "score": 80},
			{"ticker": "FAIL", "score": 75},
			{"ticker": "NO_DATA", "score": 70},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# 1 passed + 1 empty (no data) = 2
		self.assertEqual(result["output"]["passed_count"], 2)
		# 1 failed
		self.assertEqual(result["output"]["filtered_count"], 1)


class TestEntryFilterAgentWithSingleEtf(unittest.TestCase):
	"""Test EntryFilterAgent with single_etf strategy configuration."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryFilterAgent("test_filter", self.context)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	@patch("src.agents.entry.sub_agents.entry_filter_agent.evaluate")
	def test_single_etf_entry_filter(self, mock_evaluate, mock_strategy_manager_class):
		"""Test entry_filter from single_etf strategy.

		Formula: sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > 20
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

		# Mock evaluate to return True for good conditions
		mock_evaluate.return_value = True

		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104],
			"sha_10_green": [1, 1, 1, 1, 1],
			"ema_20": [99, 100, 101, 102, 103],
			"adx_14": [25, 26, 27, 28, 29],
		})

		self.context.set("strategy_name", "single_etf")
		self.context.set("data_history", {
			"SPY": df,
		})
		self.context.set("entry_recommendations", [
			{"ticker": "SPY", "composite_score": 85},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["passed_count"], 1)
		self.assertEqual(result["output"]["filtered_count"], 0)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	@patch("src.agents.entry.sub_agents.entry_filter_agent.evaluate")
	def test_single_etf_filter_blocks_poor_adx(self, mock_evaluate, mock_strategy_manager_class):
		"""Test single_etf filter blocks when ADX is too low."""
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "sha_10_green[-1] == 1 and ema_20[0] < close[0] and adx_14[0] > 20"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		# Mock evaluate to return False (ADX too low)
		mock_evaluate.return_value = False

		df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104],
			"sha_10_green": [1, 1, 1, 1, 1],
			"ema_20": [99, 100, 101, 102, 103],
			"adx_14": [15, 16, 17, 18, 19],  # Below 20
		})

		self.context.set("strategy_name", "single_etf")
		self.context.set("data_history", {
			"SPY": df,
		})
		self.context.set("entry_recommendations", [
			{"ticker": "SPY", "composite_score": 85},
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["filtered_count"], 1)
		self.assertEqual(result["output"]["passed_count"], 0)


if __name__ == "__main__":
	unittest.main()
