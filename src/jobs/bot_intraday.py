"""Intraday trading bot job."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.job import Job, JobStatus
from core.context import AgentContext


class BotIntraday(Job):
	"""Intraday trading bot for active market management.

	Responsibilities:
	- Monitor active positions throughout the day
	- Execute scaling in/out based on price action
	- Manage stop losses and take profits
	- Generate intraday signals and alerts
	"""

	def __init__(self, name: str, job_dir: Path, context: Optional[AgentContext] = None):
		"""Initialize intraday bot.

		Args:
			name: Job identifier
			job_dir: Directory to store job data
			context: Optional AgentContext
		"""
		super().__init__(name, job_dir, context)
		self.active_positions: List[Dict[str, Any]] = []
		self.trades_executed: List[Dict[str, Any]] = []
		self.market_events: List[Dict[str, Any]] = []

	def monitor_positions(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
		"""Monitor active portfolio positions.

		Args:
			portfolio: Current portfolio state

		Returns:
			Portfolio status summary
		"""
		self.logger.info("Monitoring active positions")
		self.active_positions = portfolio.get("positions", [])

		self.context.set("portfolio", portfolio)

		return {
			"positions_count": len(self.active_positions),
			"total_pnl": sum(p.get("pnl", 0) for p in self.active_positions),
			"winning_positions": len([p for p in self.active_positions if p.get("pnl", 0) > 0]),
			"losing_positions": len([p for p in self.active_positions if p.get("pnl", 0) < 0]),
			"timestamp": datetime.now().isoformat()
		}

	def check_exit_conditions(self, exit_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
		"""Check if any positions should be exited.

		Args:
			exit_rules: Rules for position exits (stop loss, take profit, time-based)

		Returns:
			List of positions to exit
		"""
		self.logger.info("Checking exit conditions")

		self.context.set("exit_rules", exit_rules)

		exit_candidates = []
		for position in self.active_positions:
			pnl = position.get("pnl", 0)
			pnl_pct = position.get("pnl_pct", 0)

			stop_loss = exit_rules.get("stop_loss", -0.05)
			take_profit = exit_rules.get("take_profit", 0.10)

			if pnl_pct <= stop_loss or pnl_pct >= take_profit:
				exit_candidates.append({
					"ticker": position["ticker"],
					"reason": "stop_loss" if pnl_pct <= stop_loss else "take_profit",
					"pnl_pct": pnl_pct,
					"current_price": position.get("current_price")
				})

		return exit_candidates

	def execute_scale_in(self, ticker: str, quantity: int, price: float) -> Dict[str, Any]:
		"""Execute scale-in trade (add to position).

		Args:
			ticker: Stock ticker
			quantity: Quantity to add
			price: Execution price

		Returns:
			Trade execution record
		"""
		self.logger.info(f"Scale in {ticker}: {quantity} @ {price}")

		trade = {
			"type": "scale_in",
			"ticker": ticker,
			"quantity": quantity,
			"price": price,
			"timestamp": datetime.now().isoformat(),
			"status": "executed"
		}

		self.trades_executed.append(trade)
		self.set_result("last_trade", trade)

		return trade

	def execute_scale_out(self, ticker: str, quantity: int, price: float) -> Dict[str, Any]:
		"""Execute scale-out trade (reduce position).

		Args:
			ticker: Stock ticker
			quantity: Quantity to sell
			price: Execution price

		Returns:
			Trade execution record
		"""
		self.logger.info(f"Scale out {ticker}: {quantity} @ {price}")

		trade = {
			"type": "scale_out",
			"ticker": ticker,
			"quantity": quantity,
			"price": price,
			"timestamp": datetime.now().isoformat(),
			"status": "executed"
		}

		self.trades_executed.append(trade)
		self.set_result("last_trade", trade)

		return trade

	def record_market_event(self, event_type: str, description: str, data: Dict[str, Any]) -> None:
		"""Record significant market event.

		Args:
			event_type: Type of event (gap, breakout, reversal, etc.)
			description: Event description
			data: Event data
		"""
		event = {
			"type": event_type,
			"description": description,
			"data": data,
			"timestamp": datetime.now().isoformat()
		}

		self.market_events.append(event)
		self.logger.info(f"Market event: {event_type} - {description}")

	def run_intraday_cycle(self, portfolio: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
		"""Execute full intraday trading cycle.

		Args:
			portfolio: Current portfolio state
			rules: Trading rules and configuration

		Returns:
			Cycle execution summary
		"""
		self.start()
		self.logger.info(f"Starting intraday bot: {self.name}")

		try:
			# Monitor positions
			status = self.monitor_positions(portfolio)
			self.set_result("position_status", status)

			# Check exit conditions
			exits = self.check_exit_conditions(rules.get("exits", {}))
			self.set_result("exit_candidates", exits)

			# Execute exits
			exit_count = 0
			for exit_candidate in exits:
				self.execute_scale_out(
					exit_candidate["ticker"],
					100,
					exit_candidate["current_price"]
				)
				exit_count += 1

			# Record summary
			summary = {
				"status": "completed",
				"positions_monitored": status["positions_count"],
				"trades_executed": len(self.trades_executed),
				"positions_exited": exit_count,
				"winning_positions": status["winning_positions"],
				"losing_positions": status["losing_positions"],
				"market_events": len(self.market_events),
				"total_pnl": status["total_pnl"],
				"timestamp": datetime.now().isoformat()
			}

			self.complete(summary)
			self.logger.info(f"Intraday cycle completed: {summary}")

			return summary

		except Exception as e:
			error_msg = f"Intraday bot failed: {str(e)}"
			self.fail(error_msg)
			self.logger.exception(error_msg)
			raise

	def get_trade_log(self) -> List[Dict[str, Any]]:
		"""Get all trades executed in this session.

		Returns:
			List of trade records
		"""
		return self.trades_executed

	def get_market_events_log(self) -> List[Dict[str, Any]]:
		"""Get all market events recorded.

		Returns:
			List of market events
		"""
		return self.market_events
