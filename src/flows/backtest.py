"""Backtest flow for simulating trading strategy over a date range."""

import sys
import uuid
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, date as date_type, timedelta

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from agents.backtest.agent import BacktestAgent
from flows.premarket import PreMarketFlow
from flows.transact import TransactFlow
from flows.postmarket import PostMarketFlow
from agents.research.agent import ResearchAgent
from tools.portfolio import PortfolioManager
from tools.portfolio.metrics import PortfolioMetrics
from tools.strategy.strategy import StrategyManager
from utils.env import get_db_root


class BacktestFlow(Flow):
	"""Flow for backtesting trading strategy over a date range.

	Orchestrates BacktestAgent with pluggable flows:
	1. PreMarketFlow - Generate pending orders based on strategy signals
	2. TransactFlow - Execute pending orders on the date
	3. PostMarketFlow - Expire pending orders and cleanup at end of day

	Collects metrics and results across all days with sandboxed data.
	"""

	def __init__(self):
		"""Initialize backtest flow."""
		super().__init__("BacktestFlow")

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute backtest over a date range.

		Args:
			input_data: Input data with:
				- strategy: Strategy name (required)
				- start_date: Start date (YYYY-MM-DD) - optional, default 1 year ago
				- end_date: End date (YYYY-MM-DD) - optional, default today
				- portfolio_name: Portfolio name - optional, derived from strategy

		Returns:
			Backtest result with daily metrics and summary
		"""
		flow_input = input_data or {}

		# Validate strategy
		strategy_name = flow_input.get("strategy")
		if not strategy_name:
			return {
				"status": "error",
				"message": "strategy parameter required",
			}

		# Create backtest ID for sandboxing (timestamp + short UUID)
		backtest_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
		# Organize backtests by strategy: ~/.cresus/db/backtests/<strategy_name>/<timestamp>
		backtest_dir = get_db_root() / "backtests" / strategy_name / backtest_id
		backtest_dir.mkdir(parents=True, exist_ok=True)

		# Set in context for sandboxing
		self.context.set("backtest_id", backtest_id)
		self.context.set("backtest_dir", str(backtest_dir))
		self.context.set("strategy_name", strategy_name)

		# Derive portfolio name from strategy if not provided
		portfolio_name = flow_input.get("portfolio_name") or self._strategy_to_portfolio_name(strategy_name)
		self.context.set("portfolio_name", portfolio_name)

		self.logger.info(
			f"Starting backtest: {strategy_name} ({portfolio_name}) "
			f"backtest_id={backtest_id}"
		)

		# Create BacktestAgent with pluggable flows
		backtest_agent = BacktestAgent("BacktestAgent", context=self.context)

		# Set pre-market flow (generates pending orders)
		premarket_flow = PreMarketFlow(strategy_name, context=self.context)
		backtest_agent.set_premarket_flow(premarket_flow)

		# Set market flow (executes pending orders)
		transact_flow = TransactFlow(context=self.context)
		backtest_agent.set_market_flow(transact_flow)

		# Set post-market flow (cleanup: expire pending orders, update metrics)
		postmarket_flow = PostMarketFlow(strategy_name)
		postmarket_flow.context = self.context
		backtest_agent.set_postmarket_flow(postmarket_flow)

		# Run backtest through agent
		agent_result = backtest_agent.process({
			"strategy_name": strategy_name,
			"start_date": flow_input.get("start_date"),
			"end_date": flow_input.get("end_date"),
			"lookback_days": flow_input.get("lookback_days", 365),
		})

		if agent_result.get("status") != "success":
			return agent_result

		# Enrich result with backtest metadata and final portfolio state
		backtest_output = agent_result.get("output", {})
		backtest_output["backtest_id"] = backtest_id
		backtest_output["backtest_dir"] = str(backtest_dir)
		backtest_output["portfolio"] = portfolio_name

		# Get final portfolio metrics from sandboxed context
		pm = PortfolioManager(context=self.context.__dict__)
		final_portfolio = pm.get_portfolio_summary(portfolio_name)
		if final_portfolio:
			backtest_output["final_portfolio"] = final_portfolio

		# Load strategy configuration to get initial capital
		strategy_manager = StrategyManager()
		strategy_config = strategy_manager.load_strategy(strategy_name)
		initial_capital = 100.0  # default
		if strategy_config.get("status") == "success":
			strategy_data = strategy_config.get("data", {})
			initial_capital = strategy_data.get("backtest", {}).get("initial_capital", 100.0)
		
		self.logger.info(f"Using initial capital: ${initial_capital:.2f}")

		# Calculate comprehensive backtest metrics
		metrics_calculator = PortfolioMetrics(context=self.context)
		metrics = metrics_calculator.calculate_backtest_metrics(
			name=portfolio_name,
			start_date=flow_input.get("start_date"),
			end_date=flow_input.get("end_date"),
			start_value=initial_capital
		)
		# Add metrics under portfolio_metrics key
		backtest_output["portfolio_metrics"] = metrics

		# Run research agent to identify issues
		research_agent = ResearchAgent()
		research_agent.context = self.context
		research_result = research_agent.process()
		research_output = research_result.get("output", {})
		
		# Add research findings to output
		backtest_output["research"] = {
			"journal_analysis": research_output.get("journal_analysis", {}),
			"order_analysis": research_output.get("order_analysis", {}),
			"identified_issues": research_output.get("identified_issues", []),
			"severity_level": research_output.get("severity_level", "none"),
			"issue_count": research_output.get("total_issues", 0),
		}

		return {
			"status": "success",
			"output": backtest_output,
			"message": f"Backtest {backtest_id} completed for {strategy_name}",
		}

	@staticmethod
	def _strategy_to_portfolio_name(strategy_name: str) -> str:
		"""Convert strategy name to portfolio name.

		Examples:
			"momentum_cac" → "Momentum cac"
			"ta_nasdaq" → "Ta nasdaq"
		"""
		parts = strategy_name.split("_")
		return " ".join(p.capitalize() for p in parts)
