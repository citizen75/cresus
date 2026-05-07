"""Tests for ResearchAgent."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.research.agent import ResearchAgent
from agents.research.sub_agents.journal_analyzer import JournalAnalyzerAgent
from agents.research.sub_agents.order_analyzer import OrderAnalyzerAgent
from agents.research.sub_agents.issue_identifier import IssueIdentifierAgent
from agents.research.sub_agents.stats_analyzer import PortfolioStatsAnalyzerAgent
from agents.research.sub_agents.orders_analysis import OrdersAnalysisAgent
from core.context import AgentContext


class TestResearchAgent(unittest.TestCase):
	"""Test cases for ResearchAgent class."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = ResearchAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that ResearchAgent can be initialized."""
		assert self.agent.name == "ResearchAgent"
		assert self.agent.context is not None

	def test_process_missing_backtest_dir(self):
		"""Test that process returns error when backtest_dir missing."""
		result = self.agent.process({})

		assert result.get("status") == "error"
		assert "backtest_dir" in result.get("message", "")

	def test_process_runs_all_sub_agents(self):
		"""Test that process runs all sub-agents."""
		self.context.set("backtest_dir", "/path/to/backtest")

		with patch.object(JournalAnalyzerAgent, "process") as mock_journal:
			with patch.object(OrderAnalyzerAgent, "process") as mock_order:
				with patch.object(IssueIdentifierAgent, "process") as mock_issue:
					with patch.object(PortfolioStatsAnalyzerAgent, "process") as mock_stats:
						with patch.object(OrdersAnalysisAgent, "process") as mock_orders_analysis:
							mock_journal.return_value = {"output": {}}
							mock_order.return_value = {"output": {}}
							mock_issue.return_value = {"output": {}}
							mock_stats.return_value = {"output": {}}
							mock_orders_analysis.return_value = {"output": {}}

							result = self.agent.process({})

							assert result.get("status") == "success"


class TestJournalAnalyzerAgent(unittest.TestCase):
	"""Test cases for JournalAnalyzerAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = JournalAnalyzerAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "JournalAnalyzerAgent"

	def test_process_analyzes_journal(self):
		"""Test that process analyzes journal."""
		self.context.set("backtest_dir", "/tmp/backtest")

		with patch("agents.research.sub_agents.journal_analyzer.Journal") as mock_journal_class:
			mock_journal = MagicMock()
			mock_journal.load_trades.return_value = pd.DataFrame({
				"ticker": ["AAPL", "GOOGL"],
				"entry_price": [100, 2000],
				"exit_price": [105, 2050],
				"quantity": [10, 5],
				"pnl": [50, 250],
			})
			mock_journal_class.return_value = mock_journal

			result = self.agent.process({})

			assert result.get("status") == "success"


class TestOrderAnalyzerAgent(unittest.TestCase):
	"""Test cases for OrderAnalyzerAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = OrderAnalyzerAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "OrderAnalyzerAgent"

	def test_process_analyzes_orders(self):
		"""Test that process analyzes orders."""
		self.context.set("backtest_dir", "/tmp/backtest")

		with patch("agents.research.sub_agents.order_analyzer.Journal") as mock_journal_class:
			mock_journal = MagicMock()
			mock_journal.load_orders.return_value = pd.DataFrame({
				"ticker": ["AAPL", "GOOGL"],
				"status": ["EXECUTED", "EXECUTED"],
				"quantity": [10, 5],
				"price": [100, 2000],
			})
			mock_journal_class.return_value = mock_journal

			result = self.agent.process({})

			assert result.get("status") == "success"


class TestIssueIdentifierAgent(unittest.TestCase):
	"""Test cases for IssueIdentifierAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = IssueIdentifierAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "IssueIdentifierAgent"

	def test_process_identifies_issues(self):
		"""Test that process identifies issues."""
		result = self.agent.process({
			"journal_analysis": {"trade_count": 10},
			"order_analysis": {"executed_count": 10}
		})

		assert result.get("status") == "success"
		assert "identified_issues" in result.get("output", {})


class TestPortfolioStatsAnalyzerAgent(unittest.TestCase):
	"""Test cases for PortfolioStatsAnalyzerAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = PortfolioStatsAnalyzerAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "PortfolioStatsAnalyzerAgent"

	def test_process_analyzes_stats(self):
		"""Test that process analyzes portfolio stats."""
		self.context.set("strategy_name", "test_strategy")
		self.context.set("portfolio_metrics", {
			"total_return": 0.15,
			"sharpe_ratio": 1.5,
			"max_drawdown": 0.10
		})

		result = self.agent.process({})

		assert result.get("status") == "success"


class TestOrdersAnalysisAgent(unittest.TestCase):
	"""Test cases for OrdersAnalysisAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = OrdersAnalysisAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "OrdersAnalysisAgent"

	def test_process_analyzes_orders_quality(self):
		"""Test that process analyzes orders quality."""
		self.context.set("strategy_name", "test_strategy")

		with patch("agents.research.sub_agents.orders_analysis.Journal") as mock_journal_class:
			mock_journal = MagicMock()
			mock_journal.load_orders.return_value = pd.DataFrame({
				"ticker": ["AAPL"],
				"status": ["EXECUTED"],
				"quantity": [10]
			})
			mock_journal_class.return_value = mock_journal

			result = self.agent.process({})

			assert result.get("status") == "success"


if __name__ == "__main__":
	unittest.main()
