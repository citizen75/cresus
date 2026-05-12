"""Filter to exclude tickers with open positions."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.portfolio.journal import Journal


class FilterOpenPositionsAgent(Agent):
	"""Filter out tickers that already have open positions.

	Prevents re-entering a position that is already open, allowing
	watchlist selection to move to other candidates.
	"""

	def __init__(self, name: str = "FilterOpenPositionsAgent"):
		"""Initialize filter.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter watchlist to exclude tickers with open positions.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with filtered watchlist
		"""
		if input_data is None:
			input_data = {}

		watchlist = self.context.get("watchlist") or []
		if not watchlist:
			return {
				"status": "success",
				"input": input_data,
				"output": {"filtered_count": 0},
				"message": "No watchlist to filter"
			}

		portfolio_name = self.context.get("portfolio_name") or "default"

		# Get open positions from journal
		try:
			journal = Journal(portfolio_name, context=self.context.__dict__)
			open_positions = journal.get_open_positions()
			open_tickers = {pos['ticker'] for pos in open_positions}
		except Exception as e:
			self.logger.warning(f"Could not get open positions: {e}")
			return {
				"status": "success",
				"input": input_data,
				"output": {"filtered_count": 0},
				"message": "No open positions to filter"
			}

		# Filter watchlist
		original_count = len(watchlist)
		filtered_watchlist = [t for t in watchlist if t not in open_tickers]
		removed_count = original_count - len(filtered_watchlist)

		self.context.set("watchlist", filtered_watchlist)

		if removed_count > 0:
			self.logger.info(
				f"Filtered watchlist: removed {removed_count} ticker(s) with open positions. "
				f"Watchlist: {original_count} → {len(filtered_watchlist)}"
			)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"original_count": original_count,
				"filtered_count": len(filtered_watchlist),
				"removed_count": removed_count,
				"open_tickers": list(open_tickers),
			},
			"message": f"Filtered {removed_count} ticker(s) with open positions"
		}
