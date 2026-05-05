"""Research agent for analyzing backtest journal and orders to identify issues."""

from typing import Any, Dict, Optional
from core.agent import Agent
from .sub_agents.journal_analyzer import JournalAnalyzerAgent
from .sub_agents.order_analyzer import OrderAnalyzerAgent
from .sub_agents.issue_identifier import IssueIdentifierAgent


class ResearchAgent(Agent):
	"""Analyze backtest results to identify issues and anomalies.

	Runs sub-agents to:
	1. Analyze trade journal for patterns and statistics
	2. Analyze order execution for discrepancies
	3. Identify issues and problems
	"""

	def __init__(self, name: str = "ResearchAgent"):
		"""Initialize research agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Analyze backtest results and identify issues.

		Orchestrates sub-agents to analyze:
		- Trade journal (entry/exit prices, durations, P&L)
		- Order execution (matched orders, fills, discrepancies)
		- Issues (zero metrics, position sizing problems, etc.)

		Args:
			input_data: Input data (optional)

		Returns:
			Response with analysis results and identified issues
		"""
		if input_data is None:
			input_data = {}

		backtest_dir = self.context.get("backtest_dir") if self.context else None
		portfolio_name = self.context.get("portfolio_name") if self.context else None
		if portfolio_name is None:
			portfolio_name = "default"

		if not backtest_dir:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No backtest_dir in context"
			}

		# Run sub-agents
		analysis_results = {}

		# 1. Analyze journal
		journal_agent = JournalAnalyzerAgent()
		journal_agent.context = self.context
		journal_result = journal_agent.process(input_data)
		analysis_results["journal"] = journal_result.get("output", {})

		# 2. Analyze orders
		order_agent = OrderAnalyzerAgent()
		order_agent.context = self.context
		order_result = order_agent.process(input_data)
		analysis_results["orders"] = order_result.get("output", {})

		# 3. Identify issues
		issue_agent = IssueIdentifierAgent()
		issue_agent.context = self.context
		issue_result = issue_agent.process({
			"journal_analysis": analysis_results["journal"],
			"order_analysis": analysis_results["orders"],
		})
		analysis_results["issues"] = issue_result.get("output", {})

		# Compile summary
		issues = analysis_results["issues"].get("identified_issues", [])
		severity = analysis_results["issues"].get("severity_level", "none")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"backtest_dir": backtest_dir,
				"portfolio": portfolio_name,
				"journal_analysis": analysis_results["journal"],
				"order_analysis": analysis_results["orders"],
				"identified_issues": issues,
				"severity_level": severity,
				"total_issues": len(issues),
			},
			"message": f"Analyzed backtest {backtest_dir}: {len(issues)} issues found (severity: {severity})"
		}
