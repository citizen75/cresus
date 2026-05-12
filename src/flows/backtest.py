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

		# Extract dates for later use in context.json
		start_date = flow_input.get("start_date")
		end_date = flow_input.get("end_date")

		# Create backtest ID for sandboxing (timestamp + short UUID)
		backtest_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
		# Organize backtests by strategy: ~/.cresus/db/backtests/<strategy_name>/<timestamp>
		backtest_dir = get_db_root() / "backtests" / strategy_name / backtest_id
		backtest_dir.mkdir(parents=True, exist_ok=True)

		# Set in context for sandboxing
		self.context.set("backtest_id", backtest_id)
		self.context.set("backtest_dir", str(backtest_dir))
		self.context.set("strategy_name", strategy_name)

		# Load and set strategy_config early (needed by all agents and flows)
		from tools.strategy import StrategyManager
		sm = StrategyManager()
		strategy_result = sm.load_strategy(strategy_name)
		if strategy_result.get("status") == "success":
			strategy_config = strategy_result.get("data", {})
			self.context.set("strategy_config", strategy_config)
			self.logger.debug(f"Loaded strategy_config for {strategy_name}")
		else:
			self.logger.warning(f"Could not load strategy_config for {strategy_name}")

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
		postmarket_flow = PostMarketFlow(strategy_name, context=self.context)
		backtest_agent.set_postmarket_flow(postmarket_flow)

		# Run backtest through agent
		agent_result = backtest_agent.process({
			"strategy_name": strategy_name,
			"start_date": start_date,
			"end_date": end_date,
			"lookback_days": flow_input.get("lookback_days", 365),
		})

		if agent_result.get("status") != "success":
			return agent_result

		# Enrich result with backtest metadata and final portfolio state
		backtest_output = agent_result.get("output", {})
		backtest_output["backtest_id"] = backtest_id
		backtest_output["backtest_dir"] = str(backtest_dir)
		backtest_output["portfolio"] = portfolio_name

		# Flush portfolio journal from memory to disk
		from tools.portfolio.journal import Journal
		journal = Journal(portfolio_name, context=self.context.__dict__)
		journal.flush()
		
		# Get final portfolio metrics from persisted journal
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

		# Use actual start/end dates from backtest output
		# BacktestAgent adjusts end_date if needed (e.g., to last available data)
		actual_start_date = backtest_output.get("start_date", flow_input.get("start_date"))
		actual_end_date = backtest_output.get("end_date", flow_input.get("end_date"))

		# Calculate comprehensive backtest metrics from persisted portfolio
		metrics_calculator = PortfolioMetrics(context=self.context.__dict__)
		metrics = metrics_calculator.calculate_backtest_metrics(
			name=portfolio_name,
			start_date=actual_start_date,
			end_date=actual_end_date,
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

		# Print agent metrics summary to stdout (disabled - only show portfolio metrics in backtest output)
		# try:
		# 	metrics = self.context.get_agent_metrics()
		# 	if metrics:
		# 		print("\n" + "=" * 80)
		# 		print("Agent Execution Times")
		# 		print("=" * 80)
		# 		
		# 		total_ms = sum(t["duration_ms"] for t in metrics)
		# 		
		# 		# Sort by duration descending
		# 		sorted_metrics = sorted(metrics, key=lambda x: x["duration_ms"], reverse=True)
		# 		
		# 		# Filter out metrics with negligible duration (< 1ms or rounds to 0.0%)
		# 		significant_metrics = [
		# 			m for m in sorted_metrics 
		# 			if m["duration_ms"] >= 1.0 or (m["duration_ms"] / total_ms * 100 if total_ms > 0 else 0) >= 0.05
		# 		]
		# 		
		# 		for metric in significant_metrics:
		# 			name = metric["name"]
		# 			duration = metric["duration_ms"]
		# 			pct = (duration / total_ms * 100) if total_ms > 0 else 0
		# 			print(f"  {name:50s} {duration:8.2f}ms ({pct:5.1f}%)")
		# 		
		# 		print("-" * 80)
		# 		print(f"  {'Total':50s} {total_ms:8.2f}ms (100.0%)")
		# 		print("=" * 80 + "\n")
		# except Exception as e:
		# 	self.logger.debug(f"Could not print agent metrics: {e}")

		# Save context with execution metrics and ticker counts to context.json
		try:
			import json
			context_data = {
				"backtest_id": backtest_id,
				"strategy": strategy_name,
				"start_date": str(start_date),
				"end_date": str(end_date),
				"metadata": self.context.get("metadata") or {},
				"execution_history": self.context.get("execution_history") or [],
			}
			context_file = Path(backtest_dir) / "context.json"
			with open(context_file, 'w') as f:
				json.dump(context_data, f, indent=2, default=str)
			self.logger.debug(f"Saved execution context to {context_file}")
		except Exception as e:
			self.logger.warning(f"Could not save context.json: {e}")

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
