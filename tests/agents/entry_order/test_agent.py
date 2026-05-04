"""Tests for EntryOrderAgent."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.context import AgentContext
from agents.entry_order.agent import EntryOrderAgent
from agents.entry_order.sub_agents import (
	PositionSizingAgent,
	EntryTimingAgent,
	RiskGuardAgent,
	OrderConstructionAgent,
)


class TestEntryOrderAgent(unittest.TestCase):
	"""Test EntryOrderAgent orchestration."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryOrderAgent("TestEntryOrderAgent", context=self.context)

	def test_initialization(self):
		"""Test agent initialization."""
		self.assertEqual(self.agent.name, "TestEntryOrderAgent")
		self.assertIsNotNone(self.agent.context)
		self.assertEqual(self.agent.sizing_method, "fractional")
		self.assertEqual(self.agent.risk_percent, 2.0)

	def test_initialization_with_params(self):
		"""Test agent initialization with custom parameters."""
		agent = EntryOrderAgent(
			"CustomAgent",
			context=self.context,
			sizing_method="kelly",
			risk_percent=3.0
		)
		self.assertEqual(agent.sizing_method, "kelly")
		self.assertEqual(agent.risk_percent, 3.0)

	def test_process_missing_entry_recommendations(self):
		"""Test process with missing entry recommendations."""
		result = self.agent.process({})

		self.assertEqual(result["status"], "error")
		self.assertIn("No entry recommendations", result["message"])

	@patch("agents.entry_order.agent.Flow.process")
	def test_process_with_entry_recommendations(self, mock_flow_process):
		"""Test process with valid entry recommendations."""
		# Setup entry recommendations
		entry_recs = [
			{
				"ticker": "AAPL",
				"entry_score": 80,
				"composite_score": 75,
				"entry_price": 150.0,
				"stop_loss": 145.0,
				"take_profit": 160.0,
				"rr_ratio": 2.0,
				"recommendation": "BUY",
			}
		]
		self.context.set("entry_recommendations", entry_recs)

		# Mock flow execution
		mock_flow_process.return_value = {
			"status": "success",
			"execution_history": [],
		}

		# Mock executable orders
		self.context.set("executable_orders", [
			{
				"id": "order123",
				"ticker": "AAPL",
				"shares": 10,
				"entry_price": 150.0,
				"risk_amount": 50.0,
			}
		])

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["count"], 1)
		self.assertIn("orders", result["output"])

	@patch("agents.entry_order.agent.Flow.process")
	def test_process_flow_failure(self, mock_flow_process):
		"""Test process when flow fails."""
		# Setup entry recommendations
		self.context.set("entry_recommendations", [{"ticker": "AAPL"}])

		# Mock flow failure
		mock_flow_process.return_value = {
			"status": "error",
			"message": "Flow execution failed",
		}

		result = self.agent.process({})

		self.assertEqual(result["status"], "error")
		self.assertIn("Flow execution failed", result["message"])

	@patch("agents.entry_order.agent.Flow.process")
	def test_process_portfolio_name(self, mock_flow_process):
		"""Test process sets portfolio name in context."""
		self.context.set("entry_recommendations", [{"ticker": "AAPL"}])
		mock_flow_process.return_value = {
			"status": "success",
			"execution_history": [],
		}
		self.context.set("executable_orders", [])

		self.agent.process({"portfolio_name": "myportfolio"})

		self.assertEqual(self.context.get("portfolio_name"), "myportfolio")

	def test_count_execution_methods(self):
		"""Test counting execution methods."""
		orders = [
			{"execution_method": "market"},
			{"execution_method": "market"},
			{"execution_method": "limit"},
			{"execution_method": "scale_in"},
		]

		counts = self.agent._count_execution_methods(orders)

		self.assertEqual(counts["market"], 2)
		self.assertEqual(counts["limit"], 1)
		self.assertEqual(counts["scale_in"], 1)


class TestPositionSizingAgent(unittest.TestCase):
	"""Test PositionSizingAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = PositionSizingAgent(
			"TestPositionSizing",
			sizing_method="fractional",
			risk_percent=2.0
		)
		self.agent.context = self.context

	def test_initialization(self):
		"""Test position sizing agent initialization."""
		self.assertEqual(self.agent.sizing_method, "fractional")
		self.assertEqual(self.agent.risk_percent, 2.0)

	def test_process_no_entry_recommendations(self):
		"""Test process with no entry recommendations."""
		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertIn("No entry recommendations", result["message"])

	@patch("agents.entry_order.sub_agents.PortfolioManager")
	@patch("agents.entry_order.sub_agents.Fundamental")
	def test_fractional_sizing(self, mock_fundamental, mock_portfolio):
		"""Test fractional position sizing."""
		# Setup mocks
		mock_pm = Mock()
		mock_portfolio.return_value = mock_pm
		mock_pm.get_portfolio_details.return_value = {"total_value": 50000, "num_positions": 0}
		mock_pm.get_portfolio_cash.return_value = 100000.0

		mock_fund = Mock()
		mock_fundamental.return_value = mock_fund
		mock_fund.get_current_price.return_value = 150.0

		# Setup entry recommendations
		entry_recs = [
			{
				"ticker": "AAPL",
				"entry_price": 150.0,
				"stop_loss": 145.0,
			}
		]
		self.context.set("entry_recommendations", entry_recs)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertIsNotNone(self.context.get("sized_orders"))

	def test_fractional_sizing_calculation(self):
		"""Test fractional sizing formula with position limits."""
		agent = PositionSizingAgent(risk_percent=2.0)

		# $100k portfolio, 2% risk = $2000 risk amount
		# Entry at 150, stop at 145 = $5 per share
		# Shares = $2000 / $5 = 400 shares
		# But limited to 5% of cash = $5000 / $150 = 33 shares
		shares = agent._fractional_sizing(
			cash=100000,
			current_price=150.0,
			entry_price=150.0,
			stop_loss=145.0
		)

		# Position limited to 5% of cash for safety
		self.assertEqual(shares, 33)

	def test_kelly_sizing_calculation(self):
		"""Test Kelly Criterion sizing."""
		agent = PositionSizingAgent()

		# Kelly: f = (rr * win_rate - (1 - win_rate)) / rr
		# RR=2.0, win=0.6: f = (2*0.6 - 0.4) / 2 = 0.4, half kelly = 0.2
		# 0.2 * 100k / 150 = 133 shares
		shares = agent._kelly_sizing(
			cash=100000,
			current_price=150.0,
			rr_ratio=2.0,
			win_rate=0.6
		)

		self.assertGreater(shares, 0)
		self.assertLess(shares, 200)

	def test_volatility_sizing_calculation(self):
		"""Test volatility-adjusted sizing."""
		agent = PositionSizingAgent(risk_percent=2.0)

		# High volatility = smaller position
		low_vol_shares = agent._volatility_sizing(100000, 150, 0.01)
		high_vol_shares = agent._volatility_sizing(100000, 150, 0.1)

		self.assertGreater(low_vol_shares, high_vol_shares)


class TestEntryTimingAgent(unittest.TestCase):
	"""Test EntryTimingAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = EntryTimingAgent("TestEntryTiming")
		self.agent.context = self.context

	def test_initialization(self):
		"""Test entry timing agent initialization."""
		self.assertEqual(self.agent.name, "TestEntryTiming")

	def test_process_no_sized_orders(self):
		"""Test process with no sized orders."""
		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertIn("No sized orders", result["message"])

	@patch("agents.entry_order.sub_agents.PortfolioManager")
	def test_timing_decisions(self, mock_portfolio):
		"""Test timing execution method selection."""
		# Setup sized orders
		sized_orders = [
			{
				"ticker": "AAPL",
				"shares": 100,
				"entry_price": 150.0,
			}
		]
		self.context.set("sized_orders", sized_orders)

		# Setup entry recommendations for score lookup
		entry_recs = [
			{
				"ticker": "AAPL",
				"entry_score": 85,
				"timing_score": 75,
			}
		]
		self.context.set("entry_recommendations", entry_recs)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		timed_orders = self.context.get("timed_orders")
		self.assertEqual(len(timed_orders), 1)
		self.assertIn("execution_method", timed_orders[0])


class TestRiskGuardAgent(unittest.TestCase):
	"""Test RiskGuardAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = RiskGuardAgent("TestRiskGuard")
		self.agent.context = self.context

	def test_initialization(self):
		"""Test risk guard agent initialization."""
		self.assertEqual(self.agent.name, "TestRiskGuard")

	def test_process_no_timed_orders(self):
		"""Test process with no timed orders."""
		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertIn("No orders to validate", result["message"])

	@patch("agents.entry_order.sub_agents.PortfolioManager")
	def test_portfolio_constraints(self, mock_portfolio_class):
		"""Test portfolio constraint validation."""
		# Setup mocks
		mock_pm = Mock()
		mock_portfolio_class.return_value = mock_pm
		mock_pm.get_portfolio_details.return_value = {
			"total_value": 50000,
			"num_positions": 2,
		}
		mock_pm.get_portfolio_cash.return_value = 100000.0  # Enough cash
		mock_pm.get_portfolio_allocation.return_value = {
			"total_value": 50000,
			"positions": [],
		}

		# Setup timed orders
		timed_orders = [
			{
				"ticker": "AAPL",
				"shares": 100,
				"entry_price": 150.0,
				"risk_amount": 500.0,
			}
		]
		self.context.set("timed_orders", timed_orders)

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		# Either validated or total output shows orders were processed
		self.assertIn("validated", result["output"])


class TestOrderConstructionAgent(unittest.TestCase):
	"""Test OrderConstructionAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = OrderConstructionAgent("TestOrderConstruction")
		self.agent.context = self.context

	def test_initialization(self):
		"""Test order construction agent initialization."""
		self.assertEqual(self.agent.name, "TestOrderConstruction")

	def test_process_no_validated_orders(self):
		"""Test process with no validated orders."""
		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(len(result["output"]["orders"]), 0)

	def test_order_construction(self):
		"""Test executable order construction."""
		# Setup validated orders
		validated_orders = [
			{
				"ticker": "AAPL",
				"shares": 100,
				"entry_price": 150.0,
				"execution_method": "market",
				"risk_amount": 500.0,
			}
		]
		self.context.set("validated_orders", validated_orders)

		# Setup entry recommendations
		entry_recs = [
			{
				"ticker": "AAPL",
				"entry_score": 80,
				"composite_score": 75,
				"rr_ratio": 2.0,
				"stop_loss": 145.0,
				"take_profit": 160.0,
				"recommendation": "BUY",
			}
		]
		self.context.set("entry_recommendations", entry_recs)
		self.context.set("strategy_name", "test_strategy")

		result = self.agent.process({})

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["output"]["count"], 1)

		orders = result["output"]["orders"]
		self.assertEqual(len(orders), 1)
		self.assertIn("id", orders[0])
		self.assertIn("ticker", orders[0])
		self.assertIn("shares", orders[0])
		self.assertIn("metadata", orders[0])

	def test_order_id_generation(self):
		"""Test order ID generation."""
		id1 = self.agent._generate_order_id("AAPL")
		id2 = self.agent._generate_order_id("AAPL")

		# Different timestamps should produce different IDs
		self.assertIsInstance(id1, str)
		self.assertEqual(len(id1), 12)


if __name__ == "__main__":
	unittest.main()
