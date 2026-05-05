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
from tools.portfolio import PortfolioManager


class BacktestFlow(Flow):
	"""Flow for backtesting trading strategy over a date range.

	Orchestrates BacktestAgent with pluggable flows:
	1. PreMarketFlow - Generate pending orders based on strategy signals
	2. TransactFlow - Execute pending orders on the date

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
		backtest_dir = Path(os.environ.get("CRESUS_PROJECT_ROOT", ".")) / "db" / "local" / "backtests" / backtest_id
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
