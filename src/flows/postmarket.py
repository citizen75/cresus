"""Post-market flow for cleanup and reconciliation at end of trading day.

Expires pending orders that weren't executed and updates portfolio metrics.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from agents.orders.agent import OrdersAgent


class PostMarketFlow(Flow):
	"""Post-market cleanup flow.

	Runs at end of each trading day to:
	1. Expire pending orders that were not executed (1-day lifetime)
	2. Update portfolio metrics and reconcile positions

	Used in BacktestAgent's third phase after market close.
	"""

	def __init__(self, strategy: str = "default", context: Optional[Any] = None):
		"""Initialize post-market flow.

		Args:
			strategy: Strategy name
			context: Optional AgentContext for shared state
		"""
		super().__init__(f"PostMarketFlow[{strategy}]", context=context)
		self.strategy = strategy
		self._setup_steps()

	def _setup_steps(self) -> None:
		"""Set up post-market flow steps (called once at init)."""
		# Add OrdersAgent to expire pending orders
		orders_agent = OrdersAgent("OrdersExpireStep", self.context)
		self.add_step(orders_agent, required=False)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute post-market flow at end of trading day.

		Args:
			input_data: Input data with:
				- date: Trading date
				- strategy_name: Strategy name
				- portfolio_name: Portfolio name

		Returns:
			Flow result with execution history
		"""
		input_data = input_data or {}

		# Execute the flow
		return super().process(input_data)