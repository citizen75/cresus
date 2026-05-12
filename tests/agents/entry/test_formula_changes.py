"""Test that EntryFilterAgent picks up formula changes from strategy files."""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.agents.entry.sub_agents import EntryFilterAgent
from src.core.context import AgentContext


class TestFormulaChanges(unittest.TestCase):
	"""Test that formula changes are reflected immediately."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryFilterAgent("test_filter", self.context)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_formula_change_is_picked_up(self, mock_strategy_manager_class):
		"""Test that changing formula in strategy file is reflected in output.

		This simulates a user modifying the YAML file and re-running the filter.
		"""
		# First run with original formula
		mock_manager = MagicMock()
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 101",  # Original: only pass if > 101
							"description": "Original formula"
						}
					}
				}
			}
		}
		mock_strategy_manager_class.return_value = mock_manager

		df = pd.DataFrame({
			"close": [100.5, 100.5, 100.5, 100.5, 100.5],  # Below 101
		})

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {"TEST": df})
		self.context.set("entry_recommendations", [{"ticker": "TEST"}])

		# First execution - should be blocked
		result1 = self.agent.process({})
		self.assertEqual(result1["output"]["filtered_count"], 1)
		self.assertEqual(result1["output"]["passed_count"], 0)

		# Now simulate formula change in YAML file
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 100",  # Changed: now only > 100
							"description": "Updated formula"
						}
					}
				}
			}
		}

		# Reset context but keep data
		self.context.set("entry_recommendations", [{"ticker": "TEST"}])

		# Second execution with new formula - should now pass
		result2 = self.agent.process({})
		self.assertEqual(result2["output"]["filtered_count"], 0)
		self.assertEqual(result2["output"]["passed_count"], 1)

	@patch("src.agents.entry.sub_agents.entry_filter_agent.StrategyManager")
	def test_multiple_formula_changes(self, mock_strategy_manager_class):
		"""Test multiple formula changes in sequence."""
		mock_manager = MagicMock()
		mock_strategy_manager_class.return_value = mock_manager

		df = pd.DataFrame({
			"close": [100, 100, 100, 100, 100],
		})

		# Formula 1: close > 101 (blocks)
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 101",
						}
					}
				}
			}
		}

		self.context.set("strategy_name", "test_strategy")
		self.context.set("data_history", {"TEST": df})
		self.context.set("entry_recommendations", [{"ticker": "TEST"}])

		result1 = self.agent.process({})
		self.assertEqual(result1["output"]["filtered_count"], 1)

		# Formula 2: close > 99 (passes)
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] > 99",
						}
					}
				}
			}
		}

		self.context.set("entry_recommendations", [{"ticker": "TEST"}])
		result2 = self.agent.process({})
		self.assertEqual(result2["output"]["passed_count"], 1)

		# Formula 3: close < 99 (blocks again)
		mock_manager.load_strategy.return_value = {
			"status": "success",
			"data": {
				"entry": {
					"parameters": {
						"entry_filter": {
							"formula": "close[0] < 99",
						}
					}
				}
			}
		}

		self.context.set("entry_recommendations", [{"ticker": "TEST"}])
		result3 = self.agent.process({})
		self.assertEqual(result3["output"]["filtered_count"], 1)

		# Verify StrategyManager.load_strategy was called 3 times (not cached)
		self.assertEqual(mock_manager.load_strategy.call_count, 3)


if __name__ == "__main__":
	unittest.main()
