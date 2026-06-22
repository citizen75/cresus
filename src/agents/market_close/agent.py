"""Market close agent: post-market cleanup at end of trading day.

Single canonical post-market pipeline used by BacktestAgent (backtests) and
BotFinance (live bots). Expires pending orders that weren't executed.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.agent import Agent
from agents.orders.agent import OrdersAgent


class MarketCloseAgent(Agent):
	"""Post-market cleanup: expire stale pending orders.

	Runs at end of each trading day to expire pending orders that were not
	executed (1-day lifetime by default, configurable via expiration_date).
	"""

	def __init__(self, strategy_name: str = "default", context: Optional[Any] = None):
		super().__init__(f"MarketCloseAgent[{strategy_name}]", context)
		self.strategy_name = strategy_name

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute post-market cleanup.

		Args:
			input_data: Input data with:
				- date: Trading date (read from context if not in context already)
				- strategy_name: Strategy name (optional, for time_stop lookup)
				- portfolio_name: Portfolio name

		Returns:
			Result dict with expiration details (from OrdersAgent)
		"""
		# Reset per-call: BacktestAgent's day loop calls .process() directly (not .run()),
		# so without this, agents_executed would grow unbounded across simulated days.
		self.agents_executed = []

		input_data = input_data or {}
		return self._run_sub_agent(
			OrdersAgent("OrdersExpireStep", self.context), input_data=input_data, fatal=True
		)

	def __repr__(self) -> str:
		return f"MarketCloseAgent(strategy='{self.strategy_name}')"
