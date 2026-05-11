"""Portfolio analysis flow for analyzing portfolio performance and identifying issues."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from agents.research.agent import ResearchAgent
from tools.portfolio import PortfolioManager
from utils.env import get_db_root


class PortfolioAnalysisFlow(Flow):
	"""Flow for analyzing portfolio performance and identifying issues.

	Loads portfolio journal data and runs research analysis to identify
	trading patterns, issues, and anomalies.
	"""

	def __init__(self, portfolio_name: str, context: Optional[Any] = None, use_backtest: bool = False):
		"""Initialize portfolio analysis flow.

		Args:
			portfolio_name: Portfolio name to analyze
			context: Optional AgentContext for shared state
			use_backtest: If True, analyze most recent backtest instead of live portfolio
		"""
		super().__init__(f"PortfolioAnalysisFlow[{portfolio_name}]", context=context)
		self.portfolio_name = portfolio_name
		self.use_backtest = use_backtest
		self._setup_default_steps()

	def _setup_default_steps(self) -> None:
		"""Set up default steps for portfolio analysis flow."""
		# Research agent - analyze portfolio journal and orders
		research_agent = ResearchAgent("ResearchAgent")
		self.add_step(research_agent, step_name="research", required=True)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process portfolio analysis through the flow.

		Loads portfolio journal through PortfolioManager and runs ResearchAgent
		to identify issues and patterns. Can analyze live portfolio or most recent backtest.

		Args:
			input_data: Input dictionary for the flow (may contain use_backtest flag)

		Returns:
			Final flow result with analysis findings
		"""
		# Prepare input data
		flow_input = input_data or {}

		# Check for backtest flag in input_data
		use_backtest = self.use_backtest or flow_input.get("use_backtest", False)

		# Set portfolio name in context
		self.context.set("portfolio_name", self.portfolio_name)
		
		# Set strategy_name (used by JournalAnalyzerAgent for take_profit check)
		# In backtest mode, portfolio_name is the strategy name
		if self.use_backtest or flow_input.get("use_backtest", False):
			self.context.set("strategy_name", self.portfolio_name)

		# Load portfolio journal
		import pandas as pd
		journal_file = None
		journals_dir = None

		if use_backtest:
			# Load most recent backtest for this strategy
			backtest_dir = get_db_root() / "backtests" / self.portfolio_name.lower().replace(' ', '_')

			if not backtest_dir.exists():
				return {
					"status": "error",
					"input": flow_input,
					"message": f"No backtests found for strategy '{self.portfolio_name}'",
				}

			# Find most recent backtest (highest timestamp)
			backtests = sorted([d for d in backtest_dir.iterdir() if d.is_dir()], reverse=True)
			if not backtests:
				return {
					"status": "error",
					"input": flow_input,
					"message": f"No backtest directories found in {backtest_dir}",
				}

			most_recent_backtest = backtests[0]
			journals_dir = most_recent_backtest / "portfolios"

			# Find portfolio journal in backtest
			portfolio_key = self.portfolio_name.lower().replace(' ', '_')
			journal_file = journals_dir / f"{portfolio_key}_journal.csv"

			if not journal_file.exists():
				return {
					"status": "error",
					"input": flow_input,
					"message": f"Journal file not found in backtest: {journal_file}",
				}

			self.context.set("backtest_dir", str(most_recent_backtest))
			self.context.set("backtest_mode", True)
			self.logger.info(f"Analyzing most recent backtest: {most_recent_backtest.name}")
		else:
			# Load live portfolio journal through PortfolioManager
			pm = PortfolioManager(context=self.context.__dict__)
			portfolio_details = pm.get_portfolio_details(self.portfolio_name)

			if not portfolio_details:
				return {
					"status": "error",
					"input": flow_input,
					"message": f"Portfolio '{self.portfolio_name}' not found",
				}

			# Get portfolio journal file path
			journals_dir = get_db_root() / "portfolios"
			journal_file = journals_dir / f"{self.portfolio_name.lower().replace(' ', '_')}_journal.csv"
			self.context.set("backtest_dir", str(journals_dir))

		# Verify journal file exists
		if not journal_file or not journal_file.exists():
			return {
				"status": "error",
				"input": flow_input,
				"message": f"Journal file not found: {journal_file}",
			}

		# Load journal data
		try:
			journal_df = pd.read_csv(journal_file)
			self.context.set("journal_data", journal_df)
		except Exception as e:
			return {
				"status": "error",
				"input": flow_input,
				"message": f"Error loading journal: {e}",
			}

		# Calculate portfolio metrics BEFORE research analysis (so metrics are available to stats analyzer)
		try:
			from tools.portfolio.metrics import PortfolioMetrics
			pm_metrics = PortfolioMetrics(context=self.context)
			metrics = pm_metrics.calculate_backtest_metrics(
				name=self.portfolio_name,
				start_value=10000  # Default backtest initial capital
			)
			# Make metrics available to research agent
			self.context.set("portfolio_metrics", metrics)
			self.logger.info(f"Calculated portfolio metrics for {self.portfolio_name}")
		except Exception as e:
			self.logger.debug(f"Could not calculate portfolio metrics: {e}")

		# Execute parent flow logic (which runs research agent with metrics in context)
		result = super().process(flow_input)

		# Extract research results
		research_step = self.get_step("research")
		if research_step:
			research_result = research_step.get("result")
			if research_result and research_result.get("status") == "success":
				output = research_result.get("output", {})
				result["research_analysis"] = output
				result["issues"] = output.get("identified_issues", [])
				result["severity"] = output.get("severity_level", "none")

		# Add portfolio details
		result["portfolio_name"] = self.portfolio_name
		result["analysis_mode"] = "backtest" if use_backtest else "live"
		if not use_backtest:
			result["portfolio_details"] = portfolio_details

		# Add metrics to result (already calculated and set in context)
		portfolio_metrics = self.context.get("portfolio_metrics") if self.context else {}
		if portfolio_metrics:
			result["portfolio_metrics"] = portfolio_metrics

		return result

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"PortfolioAnalysisFlow(portfolio='{self.portfolio_name}', steps={len(self.steps)})"
