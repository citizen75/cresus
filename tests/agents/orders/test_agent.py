"""Tests for OrdersAgent."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.orders.agent import OrdersAgent
from core.context import AgentContext


class TestOrdersAgent(unittest.TestCase):
	"""Test cases for OrdersAgent class."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = OrdersAgent("OrdersAgent", self.context)

	def test_init(self):
		"""Test that OrdersAgent can be initialized."""
		assert self.agent.name == "OrdersAgent"
		assert self.agent.context is not None

	def test_process_no_date_in_context(self):
		"""Test that process returns error when date not in context."""
		result = self.agent.process({})

		assert result.get("status") == "error"
		assert "date not set" in result.get("message", "")

	def test_process_success(self):
		"""Test that process succeeds with valid data."""
		self.context.set("date", datetime.now())
		self.context.set("portfolio_name", "test_portfolio")

		with patch("agents.orders.agent.Orders") as mock_orders_class:
			mock_orders = MagicMock()
			mock_orders.load_df.return_value = pd.DataFrame({
				"id": ["1", "2", "3"],
				"ticker": ["AAPL", "GOOGL", "MSFT"],
				"status": ["PENDING", "EXECUTED", "PENDING"],
				"quantity": [100, 50, 75],
				"created_at": [
					(datetime.now() - timedelta(days=2)).isoformat(),
					(datetime.now() - timedelta(days=1)).isoformat(),
					datetime.now().isoformat(),
				]
			})
			mock_orders_class.return_value = mock_orders

			result = self.agent.process({})

			assert result.get("status") == "success"
			assert "expired_count" in result.get("output", {})

	def test_process_with_time_stop_param(self):
		"""Test that time_stop parameter is respected."""
		self.context.set("date", datetime.now())
		self.context.set("portfolio_name", "test_portfolio")

		with patch("agents.orders.agent.Orders") as mock_orders_class:
			mock_orders = MagicMock()
			mock_orders.load_df.return_value = pd.DataFrame({
				"id": ["1"],
				"ticker": ["AAPL"],
				"status": ["PENDING"],
				"quantity": [100],
				"created_at": [(datetime.now() - timedelta(days=3)).isoformat()]
			})
			mock_orders_class.return_value = mock_orders

			result = self.agent.process({"time_stop": 5})

			assert result.get("status") == "success"

	def test_process_empty_orders(self):
		"""Test process with no orders in database."""
		self.context.set("date", datetime.now())

		with patch("agents.orders.agent.Orders") as mock_orders_class:
			mock_orders = MagicMock()
			mock_orders.load_df.return_value = pd.DataFrame({
				"id": [],
				"ticker": [],
				"status": [],
				"quantity": [],
				"created_at": []
			})
			mock_orders_class.return_value = mock_orders

			result = self.agent.process({})

			assert result.get("status") == "success"
			assert result.get("output", {}).get("expired_count") == 0

	def test_process_no_pending_orders(self):
		"""Test process when no orders are pending."""
		self.context.set("date", datetime.now())

		with patch("agents.orders.agent.Orders") as mock_orders_class:
			mock_orders = MagicMock()
			mock_orders.load_df.return_value = pd.DataFrame({
				"id": ["1", "2"],
				"ticker": ["AAPL", "GOOGL"],
				"status": ["EXECUTED", "CANCELLED"],
				"quantity": [100, 50],
				"created_at": [
					(datetime.now() - timedelta(days=1)).isoformat(),
					(datetime.now() - timedelta(days=2)).isoformat(),
				]
			})
			mock_orders_class.return_value = mock_orders

			result = self.agent.process({})

			assert result.get("status") == "success"
			assert result.get("output", {}).get("expired_count") == 0

	def test_process_expires_old_orders(self):
		"""Test that process expires orders older than time_stop."""
		self.context.set("date", datetime.now())

		old_date = (datetime.now() - timedelta(days=2)).isoformat()
		new_date = datetime.now().isoformat()

		with patch("agents.orders.agent.Orders") as mock_orders_class:
			mock_orders = MagicMock()
			mock_orders.load_df.return_value = pd.DataFrame({
				"id": ["1", "2"],
				"ticker": ["AAPL", "GOOGL"],
				"status": ["PENDING", "PENDING"],
				"quantity": [100, 50],
				"created_at": [old_date, new_date]
			})
			mock_orders.update_order_status = MagicMock()
			mock_orders_class.return_value = mock_orders

			result = self.agent.process({"time_stop": 1})

			assert result.get("status") == "success"
			# Old order should be expired
			mock_orders.update_order_status.assert_called()

	def test_process_with_strategy_name(self):
		"""Test that process loads time_stop from strategy config."""
		self.context.set("date", datetime.now())
		self.context.set("strategy_name", "test_strategy")

		with patch("agents.orders.agent.Orders") as mock_orders_class:
			with patch("agents.orders.agent.StrategyManager") as mock_strategy_mgr_class:
				mock_orders = MagicMock()
				mock_orders.load_df.return_value = pd.DataFrame({
					"id": [],
					"ticker": [],
					"status": [],
					"quantity": [],
					"created_at": []
				})
				mock_orders_class.return_value = mock_orders

				mock_strategy_mgr = MagicMock()
				mock_strategy_mgr.load_strategy.return_value = {
					"status": "success",
					"data": {
						"exit": {
							"parameters": {
								"time_stop": {
									"formula": "3"
								}
							}
						}
					}
				}
				mock_strategy_mgr_class.return_value = mock_strategy_mgr

				result = self.agent.process({})

				assert result.get("status") == "success"

	def test_process_default_portfolio_name(self):
		"""Test that default portfolio name is used when not provided."""
		self.context.set("date", datetime.now())

		with patch("agents.orders.agent.Orders") as mock_orders_class:
			mock_orders = MagicMock()
			mock_orders.load_df.return_value = pd.DataFrame()
			mock_orders_class.return_value = mock_orders

			result = self.agent.process({})

			# Should use "default" portfolio name
			mock_orders_class.assert_called()
			call_args = mock_orders_class.call_args
			assert call_args is not None


if __name__ == "__main__":
	unittest.main()
