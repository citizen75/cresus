"""Position duplicate filter sub-agent for preventing duplicate position entries."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.portfolio import PortfolioManager


class PositionDuplicateFilterAgent(Agent):
	"""Filter out entry recommendations for tickers with existing open positions.

	Prevents duplicate position entries by checking if a recommendation's ticker
	already has an open position in the portfolio. This ensures we don't
	accidentally scale into existing positions without explicit intent.
	"""

	def __init__(self, name: str = "PositionDuplicateFilterAgent"):
		"""Initialize position duplicate filter agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter entry recommendations to remove duplicate positions.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with filtered recommendations and filtered items list
		"""
		if input_data is None:
			input_data = {}

		entry_recommendations = self.context.get("entry_recommendations") or []

		if not entry_recommendations:
			return {
				"status": "success",
				"input": input_data,
				"output": {},
				"message": "No entry recommendations to filter"
			}

		# Get portfolio state
		portfolio_name = self.context.get("portfolio_name") or "default"
		pm = PortfolioManager(context=self.context.__dict__)
		portfolio_details = pm.get_portfolio_details(portfolio_name)

		if not portfolio_details:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Portfolio '{portfolio_name}' not found"
			}

		# Get existing open positions (case-insensitive)
		existing_positions = portfolio_details.get("positions", [])
		existing_tickers = {pos["ticker"].upper() for pos in existing_positions}

		# Filter recommendations
		filtered_recommendations = []
		filtered_items = []

		for rec in entry_recommendations:
			ticker = rec.get("ticker", "").upper()

			if ticker in existing_tickers:
				# Position already exists - filter it out
				filtered_items.append({
					"ticker": ticker,
					"entry_score": rec.get("entry_score", 0),
					"composite_score": rec.get("composite_score", 0),
					"reason": f"Position already exists for {ticker}"
				})
				self.logger.info(f"Filtered recommendation for {ticker}: Position already exists")
			else:
				# Position doesn't exist - keep the recommendation
				filtered_recommendations.append(rec)

		# Update context with filtered recommendations
		self.context.set("entry_recommendations", filtered_recommendations)
		self.context.set("filtered_duplicate_items", filtered_items)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"original_count": len(entry_recommendations),
				"filtered_count": len(filtered_items),
				"remaining_count": len(filtered_recommendations),
				"filtered_tickers": [item["ticker"] for item in filtered_items]
			},
			"message": f"Filtered {len(filtered_items)} duplicate positions, {len(filtered_recommendations)} recommendations remain"
		}
