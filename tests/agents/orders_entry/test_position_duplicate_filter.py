"""Tests for PositionDuplicateFilterAgent."""

import unittest
from unittest.mock import Mock, patch, MagicMock

from core.context import AgentContext
from agents.entry.sub_agents import PositionDuplicateFilterAgent


class TestPositionDuplicateFilterAgent(unittest.TestCase):
	"""Test PositionDuplicateFilterAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = PositionDuplicateFilterAgent("TestPositionDuplicateFilterAgent")
		self.agent.context = self.context

	def test_initialization(self):
		"""Test agent initialization."""
		self.assertEqual(self.agent.name, "TestPositionDuplicateFilterAgent")
		self.assertIsNotNone(self.agent.context)

	def test_process_no_entry_recommendations(self):
		"""Test process with no entry recommendations."""
		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertIn("No entry recommendations", result["message"])

	@patch("agents.entry.sub_agents.position_duplicate_filter.PortfolioManager")
	def test_process_portfolio_not_found(self, mock_pm_class):
		"""Test process when portfolio is not found."""
		# Setup mocks
		mock_pm = MagicMock()
		mock_pm.get_portfolio_details.return_value = None
		mock_pm_class.return_value = mock_pm

		# Setup context with entry recommendations
		entry_recs = [
			{
				"ticker": "AAPL",
				"entry_score": 80,
				"composite_score": 75,
			}
		]
		self.context.set("entry_recommendations", entry_recs)
		self.context.set("portfolio_name", "default")

		result = self.agent.process({})

		self.assertEqual(result["status"], "error")
		self.assertIn("not found", result["message"])

	@patch("agents.entry.sub_agents.position_duplicate_filter.PortfolioManager")
	def test_filter_duplicate_position(self, mock_pm_class):
		"""Test filtering out recommendation with existing position."""
		# Setup mocks
		mock_pm = MagicMock()
		mock_pm.get_portfolio_details.return_value = {
			"name": "default",
			"num_positions": 1,
			"positions": [
				{
					"ticker": "AAPL",
					"quantity": 100,
					"avg_entry_price": 150.0,
					"current_price": 155.0,
					"position_value": 15500.0,
					"position_gain": 500.0,
					"position_gain_pct": 3.33,
				}
			]
		}
		mock_pm_class.return_value = mock_pm

		# Setup context with entry recommendations
		entry_recs = [
			{
				"ticker": "AAPL",
				"entry_score": 80,
				"composite_score": 75,
			},
			{
				"ticker": "GOOGL",
				"entry_score": 75,
				"composite_score": 70,
			}
		]
		self.context.set("entry_recommendations", entry_recs)
		self.context.set("portfolio_name", "default")

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["original_count"], 2)
		self.assertEqual(result["output"]["filtered_count"], 1)
		self.assertEqual(result["output"]["remaining_count"], 1)
		self.assertEqual(result["output"]["filtered_tickers"], ["AAPL"])

		# Verify context is updated
		remaining_recs = self.context.get("entry_recommendations")
		self.assertEqual(len(remaining_recs), 1)
		self.assertEqual(remaining_recs[0]["ticker"], "GOOGL")

		# Verify filtered items
		filtered_items = self.context.get("filtered_duplicate_items")
		self.assertEqual(len(filtered_items), 1)
		self.assertEqual(filtered_items[0]["ticker"], "AAPL")
		self.assertIn("Position already exists", filtered_items[0]["reason"])

	@patch("agents.entry.sub_agents.position_duplicate_filter.PortfolioManager")
	def test_no_duplicates(self, mock_pm_class):
		"""Test when no recommendations have duplicate positions."""
		# Setup mocks
		mock_pm = MagicMock()
		mock_pm.get_portfolio_details.return_value = {
			"name": "default",
			"num_positions": 1,
			"positions": [
				{
					"ticker": "MSFT",
					"quantity": 50,
					"avg_entry_price": 300.0,
					"current_price": 310.0,
					"position_value": 15500.0,
					"position_gain": 500.0,
					"position_gain_pct": 3.33,
				}
			]
		}
		mock_pm_class.return_value = mock_pm

		# Setup context with entry recommendations
		entry_recs = [
			{
				"ticker": "AAPL",
				"entry_score": 80,
				"composite_score": 75,
			},
			{
				"ticker": "GOOGL",
				"entry_score": 75,
				"composite_score": 70,
			}
		]
		self.context.set("entry_recommendations", entry_recs)
		self.context.set("portfolio_name", "default")

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["original_count"], 2)
		self.assertEqual(result["output"]["filtered_count"], 0)
		self.assertEqual(result["output"]["remaining_count"], 2)
		self.assertEqual(result["output"]["filtered_tickers"], [])

		# Verify all recommendations are kept
		remaining_recs = self.context.get("entry_recommendations")
		self.assertEqual(len(remaining_recs), 2)

		# Verify no filtered items
		filtered_items = self.context.get("filtered_duplicate_items")
		self.assertEqual(len(filtered_items), 0)

	@patch("agents.entry.sub_agents.position_duplicate_filter.PortfolioManager")
	def test_case_insensitive_ticker_matching(self, mock_pm_class):
		"""Test that ticker matching is case-insensitive."""
		# Setup mocks
		mock_pm = MagicMock()
		mock_pm.get_portfolio_details.return_value = {
			"name": "default",
			"num_positions": 1,
			"positions": [
				{
					"ticker": "aapl",  # lowercase
					"quantity": 100,
					"avg_entry_price": 150.0,
					"current_price": 155.0,
					"position_value": 15500.0,
					"position_gain": 500.0,
					"position_gain_pct": 3.33,
				}
			]
		}
		mock_pm_class.return_value = mock_pm

		# Setup context with entry recommendations (uppercase ticker)
		entry_recs = [
			{
				"ticker": "AAPL",  # uppercase
				"entry_score": 80,
				"composite_score": 75,
			}
		]
		self.context.set("entry_recommendations", entry_recs)
		self.context.set("portfolio_name", "default")

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["filtered_count"], 1)

		# Verify AAPL is filtered out despite case difference
		remaining_recs = self.context.get("entry_recommendations")
		self.assertEqual(len(remaining_recs), 0)

	@patch("agents.entry.sub_agents.position_duplicate_filter.PortfolioManager")
	def test_empty_portfolio(self, mock_pm_class):
		"""Test filtering when portfolio has no positions."""
		# Setup mocks
		mock_pm = MagicMock()
		mock_pm.get_portfolio_details.return_value = {
			"name": "default",
			"num_positions": 0,
			"positions": []
		}
		mock_pm_class.return_value = mock_pm

		# Setup context with entry recommendations
		entry_recs = [
			{
				"ticker": "AAPL",
				"entry_score": 80,
				"composite_score": 75,
			}
		]
		self.context.set("entry_recommendations", entry_recs)
		self.context.set("portfolio_name", "default")

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["filtered_count"], 0)
		self.assertEqual(result["output"]["remaining_count"], 1)

		# Verify all recommendations are kept
		remaining_recs = self.context.get("entry_recommendations")
		self.assertEqual(len(remaining_recs), 1)


if __name__ == "__main__":
	unittest.main()
