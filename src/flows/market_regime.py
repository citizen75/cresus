"""Market regime detection flow."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from agents.market_regime.agent import MarketRegimeAgent


class MarketRegimeFlow(Flow):
	"""Flow for market regime detection (train or predict)."""

	def __init__(self):
		super().__init__("MarketRegimeFlow")
		self._setup_steps()

	def _setup_steps(self) -> None:
		"""Add MarketRegimeAgent as single step."""
		agent = MarketRegimeAgent("MarketRegimeAgent")
		self.add_step(agent, step_name="market_regime", required=True)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute market regime flow.

		Args:
			input_data: Payload with universe, action, etc.

		Returns:
			Flow result with regime output
		"""
		result = super().process(input_data or {})

		# Surface MarketRegimeAgent output directly
		regime_step = self.get_step("market_regime")
		if regime_step and regime_step.get("result"):
			agent_result = regime_step["result"]
			result["status"] = agent_result.get("status", "error")
			result["message"] = agent_result.get("message", "")
			result["output"] = agent_result.get("output", {})

		return result
