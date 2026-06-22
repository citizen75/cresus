"""Tests for CheckCashAgent."""

import unittest
from unittest.mock import patch

from core.context import AgentContext
from agents.orders_entry.sub_agents.check_cash_agent import CheckCashAgent


class TestCheckCashAgentStaticFormula(unittest.TestCase):
	"""type: capital with a static numeric literal (the common case)."""

	def setUp(self):
		self.context = AgentContext()
		self.context.set("portfolio_name", "test")
		self.context.set("strategy_config", {
			"order": {"parameters": {"position_sizing": {"type": "capital", "formula": 2000}}}
		})

	@patch("agents.orders_entry.sub_agents.check_cash_agent.PortfolioManager")
	def test_exits_when_cash_insufficient(self, mock_pm_cls):
		mock_pm_cls.return_value.get_portfolio_cash.return_value = 500.0
		agent = CheckCashAgent("CheckCashStep", context=self.context)

		result = agent.process()

		self.assertEqual(result["status"], "exit")
		self.assertIn("Insufficient cash", result["message"])

	@patch("agents.orders_entry.sub_agents.check_cash_agent.PortfolioManager")
	def test_succeeds_when_cash_sufficient(self, mock_pm_cls):
		mock_pm_cls.return_value.get_portfolio_cash.return_value = 100000.0
		agent = CheckCashAgent("CheckCashStep", context=self.context)

		result = agent.process()

		self.assertEqual(result["status"], "success")


class TestCheckCashAgentDynamicFormula(unittest.TestCase):
	"""type: capital with a dynamic, per-ticker formula referencing an indicator
	(e.g. "min(2500 / (vol_atr_pct[0] / 0.02), 3000)") - this agent runs once
	globally with no ticker/row context to evaluate such a formula against, so it
	must skip the check gracefully instead of crashing or exiting."""

	def setUp(self):
		self.context = AgentContext()
		self.context.set("portfolio_name", "test")
		self.context.set("strategy_config", {
			"order": {"parameters": {"position_sizing": {
				"type": "capital",
				"formula": "min(2500 / (vol_atr_pct[0] / 0.02), 3000)",
			}}}
		})

	@patch("agents.orders_entry.sub_agents.check_cash_agent.PortfolioManager")
	def test_does_not_crash_or_exit(self, mock_pm_cls):
		mock_pm_cls.return_value.get_portfolio_cash.return_value = 100000.0
		agent = CheckCashAgent("CheckCashStep", context=self.context)

		result = agent.process()

		self.assertEqual(result["status"], "success")


if __name__ == "__main__":
	unittest.main()
