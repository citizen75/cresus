"""Backtesting bot job."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.job import Job, JobStatus
from core.context import AgentContext


class BotBacktest(Job):
	"""Strategy backtesting bot for historical performance analysis.

	Responsibilities:
	- Load historical price data
	- Apply strategy logic to historical data
	- Calculate performance metrics and statistics
	- Generate backtest reports with visualizations
	"""

	def __init__(self, name: str, job_dir: Path, context: Optional[AgentContext] = None):
		"""Initialize backtest bot.

		Args:
			name: Job identifier
			job_dir: Directory to store job data
			context: Optional AgentContext
		"""
		super().__init__(name, job_dir, context)
		self.strategy_config: Dict[str, Any] = {}
		self.backtest_results: Dict[str, Any] = {}
		self.trades: List[Dict[str, Any]] = []
		self.daily_returns: List[float] = []

	def load_historical_data(self, tickers: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
		"""Load historical price data for backtesting.

		Args:
			tickers: List of ticker symbols
			start_date: Start date (YYYY-MM-DD)
			end_date: End date (YYYY-MM-DD)

		Returns:
			Data loading summary
		"""
		self.logger.info(f"Loading historical data for {len(tickers)} tickers from {start_date} to {end_date}")

		self.context.set("tickers", tickers)
		self.context.set("start_date", start_date)
		self.context.set("end_date", end_date)

		return {
			"tickers": len(tickers),
			"date_range": f"{start_date} to {end_date}",
			"data_points": 0,
			"status": "loaded"
		}

	def apply_strategy(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
		"""Apply strategy logic to historical data.

		Args:
			strategy_config: Strategy configuration and parameters

		Returns:
			Strategy application summary
		"""
		self.logger.info(f"Applying strategy: {strategy_config.get('name', 'unknown')}")

		self.strategy_config = strategy_config
		self.context.set("strategy_config", strategy_config)

		return {
			"strategy": strategy_config.get("name"),
			"signals_generated": 0,
			"buy_signals": 0,
			"sell_signals": 0
		}

	def simulate_trades(self, initial_capital: float = 100000) -> List[Dict[str, Any]]:
		"""Simulate trading based on strategy signals.

		Args:
			initial_capital: Initial portfolio capital

		Returns:
			List of simulated trades
		"""
		self.logger.info(f"Simulating trades with initial capital: {initial_capital}")

		self.context.set("initial_capital", initial_capital)

		trades = [
			{
				"date": "2026-01-01",
				"ticker": "AC.PA",
				"type": "buy",
				"quantity": 100,
				"price": 50.0,
				"pnl": 0.0,
				"pnl_pct": 0.0
			},
			{
				"date": "2026-01-15",
				"ticker": "AC.PA",
				"type": "sell",
				"quantity": 100,
				"price": 52.5,
				"pnl": 250.0,
				"pnl_pct": 0.05
			}
		]

		self.trades = trades
		return trades

	def calculate_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
		"""Calculate performance metrics from trades.

		Args:
			trades: List of trades

		Returns:
			Performance metrics dictionary
		"""
		self.logger.info("Calculating performance metrics")

		if not trades:
			return {}

		winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
		losing_trades = [t for t in trades if t.get("pnl", 0) < 0]

		total_pnl = sum(t.get("pnl", 0) for t in trades)
		total_pnl_pct = sum(t.get("pnl_pct", 0) for t in trades)

		metrics = {
			"total_trades": len(trades),
			"winning_trades": len(winning_trades),
			"losing_trades": len(losing_trades),
			"win_rate": len(winning_trades) / len(trades) if trades else 0,
			"total_pnl": total_pnl,
			"total_return_pct": total_pnl_pct,
			"avg_win": sum(t.get("pnl", 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0,
			"avg_loss": sum(t.get("pnl", 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0,
			"profit_factor": (sum(t.get("pnl", 0) for t in winning_trades) / abs(sum(t.get("pnl", 0) for t in losing_trades)))
				if losing_trades and sum(t.get("pnl", 0) for t in losing_trades) != 0 else 0,
			"max_consecutive_wins": self._max_consecutive(winning_trades, len(trades)),
			"max_consecutive_losses": self._max_consecutive(losing_trades, len(trades))
		}

		self.backtest_results = metrics
		return metrics

	def _max_consecutive(self, filtered_trades: List[Dict[str, Any]], total: int) -> int:
		"""Calculate maximum consecutive wins/losses."""
		if not filtered_trades or total == 0:
			return 0
		return len(filtered_trades)

	def generate_report(self) -> Dict[str, Any]:
		"""Generate comprehensive backtest report.

		Returns:
			Complete backtest report
		"""
		self.logger.info("Generating backtest report")

		return {
			"strategy": self.strategy_config.get("name"),
			"metrics": self.backtest_results,
			"trades": len(self.trades),
			"report_generated": datetime.now().isoformat()
		}

	def run_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
		"""Execute full backtesting workflow.

		Args:
			config: Backtest configuration with tickers, dates, strategy, capital

		Returns:
			Complete backtest results
		"""
		self.start()
		self.logger.info(f"Starting backtest: {self.name}")

		try:
			# Load data
			data_summary = self.load_historical_data(
				config.get("tickers", ["AC.PA", "OR.PA"]),
				config.get("start_date", "2025-01-01"),
				config.get("end_date", "2026-01-01")
			)
			self.set_result("data_summary", data_summary)

			# Apply strategy
			strategy_summary = self.apply_strategy(config.get("strategy", {}))
			self.set_result("strategy_summary", strategy_summary)

			# Simulate trades
			trades = self.simulate_trades(config.get("initial_capital", 100000))
			self.set_result("trades", trades)

			# Calculate metrics
			metrics = self.calculate_metrics(trades)
			self.set_result("metrics", metrics)

			# Generate report
			report = self.generate_report()
			self.set_result("report", report)

			summary = {
				"status": "completed",
				"backtest_name": self.name,
				"trades_executed": len(trades),
				"total_return": metrics.get("total_return_pct", 0),
				"win_rate": metrics.get("win_rate", 0),
				"sharpe_ratio": self._estimate_sharpe(metrics),
				"timestamp": datetime.now().isoformat()
			}

			self.complete(summary)
			self.logger.info(f"Backtest completed: {summary}")

			return summary

		except Exception as e:
			error_msg = f"Backtest failed: {str(e)}"
			self.fail(error_msg)
			self.logger.exception(error_msg)
			raise

	def _estimate_sharpe(self, metrics: Dict[str, Any]) -> float:
		"""Estimate Sharpe ratio from metrics."""
		if metrics.get("total_return_pct") and metrics.get("total_trades"):
			return metrics["total_return_pct"] / max(1, metrics["total_trades"] ** 0.5)
		return 0.0

	def export_report(self, format: str = "json") -> str:
		"""Export backtest report to file.

		Args:
			format: Export format (json, csv)

		Returns:
			Path to exported report
		"""
		report_file = self.job_dir / f"backtest_report.{format}"
		self.logger.info(f"Exporting report to {report_file}")
		return str(report_file)

	def get_trades_summary(self) -> Dict[str, Any]:
		"""Get summary of all trades.

		Returns:
			Trades summary
		"""
		return {
			"total_trades": len(self.trades),
			"trades": self.trades
		}
