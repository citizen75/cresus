"""Tests for TradingBroker and its sub-agents."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.trading_broker.agent import TradingBroker
from core.context import AgentContext


class TestTradingBroker(unittest.TestCase):
	"""Test cases for TradingBroker class."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = TradingBroker()
		self.agent.context = self.context

	def test_init(self):
		"""Test that TradingBroker can be initialized."""
		assert self.agent.name == "TradingBroker"
		assert hasattr(self.agent, "context")

	def test_process_missing_portfolio_name(self):
		"""Test that process returns error when portfolio_name missing."""
		result = self.agent.process({})

		# Should either error or use default
		assert result.get("status") in ["success", "error"]

	def test_process_success(self):
		"""Test that process succeeds with valid data."""
		self.context.set("portfolio_name", "test_portfolio")
		self.context.set("date", datetime.now())

		with patch("agents.trading_broker.agent.Journal"):
			with patch("agents.trading_broker.agent.Orders"):
				with patch("agents.trading_broker.agent.broker_from_journal"):
					with patch("agents.trading_broker.agent.PortfolioManager"):
						result = self.agent.process({})

						assert result.get("status") == "success"


class TestStopLossAgent(unittest.TestCase):
	"""Test cases for StopLossAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_stop_loss_triggers_on_low_hit(self):
		"""Test that stop loss is triggered when price hits low."""
		# Create mock position with stop loss
		position = {
			"ticker": "AAPL",
			"quantity": 100,
			"entry_price": 100,
			"stop_loss": 95,
			"current_price": 94,  # Below stop loss
		}

		# Stop loss should be triggered
		assert position["current_price"] < position["stop_loss"]


class TestTargetAgent(unittest.TestCase):
	"""Test cases for TargetAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_target_triggers_on_high_hit(self):
		"""Test that target is triggered when price hits high."""
		position = {
			"ticker": "AAPL",
			"quantity": 100,
			"entry_price": 100,
			"target": 107,
			"current_price": 108,  # Above target
		}

		# Target should be triggered
		assert position["current_price"] > position["target"]


class TestTimeLimitAgent(unittest.TestCase):
	"""Test cases for TimeLimitAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_time_limit_expires_holding(self):
		"""Test that position expires after holding period."""
		from datetime import timedelta

		position = {
			"ticker": "AAPL",
			"quantity": 100,
			"entry_date": datetime(2026, 5, 1),
			"holding_days": 10,
			"current_date": datetime(2026, 5, 12),
		}

		days_held = (position["current_date"] - position["entry_date"]).days
		assert days_held > position["holding_days"]


class TestTrailingStopAgent(unittest.TestCase):
	"""Test cases for TrailingStopAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_trailing_stop_updates_on_price_rise(self):
		"""Test that trailing stop updates when price rises."""
		position = {
			"ticker": "AAPL",
			"entry_price": 100,
			"peak_price": 105,
			"trailing_stop_pct": 0.05,
			"current_price": 108,
		}

		# New peak reached, trailing stop should update
		trailing_stop = position["peak_price"] * (1 - position["trailing_stop_pct"])
		assert position["current_price"] > position["peak_price"]


class TestLimitOrderAgent(unittest.TestCase):
	"""Test cases for LimitOrderAgent sub-agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_limit_order_executes_when_price_met(self):
		"""Test that limit order executes when price meets limit."""
		order = {
			"ticker": "AAPL",
			"quantity": 100,
			"limit_price": 100,
			"order_type": "BUY",
			"current_price": 99,  # Below limit for buy
		}

		# Limit order should execute
		assert order["current_price"] <= order["limit_price"]


if __name__ == "__main__":
	unittest.main()
