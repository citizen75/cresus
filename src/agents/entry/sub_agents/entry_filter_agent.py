"""Agent to filter entry recommendations based on entry_filter formula."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.strategy.strategy import StrategyManager
from tools.formula.calculator import evaluate


class EntryFilterAgent(Agent):
	"""Filter entry recommendations based on entry_filter formula from strategy.

	Applies market regime/condition filtering to entry recommendations.
	Only allows entries when the entry_filter formula evaluates to True.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter recommendations based on entry_filter formula.

		Loads entry_filter formula from strategy config and evaluates it
		against current market data for each recommendation.

		Args:
			input_data: Input data (not used, uses context)

		Returns:
			Response with filtered recommendations count
		"""
		if input_data is None:
			input_data = {}

		# Get entry recommendations and data from context
		entry_recommendations = self.context.get("entry_recommendations") or []
		data_history = self.context.get("data_history") or {}
		strategy_name = self.context.get("strategy_name")

		if not entry_recommendations:
			return {
				"status": "success",
				"input": input_data,
				"output": {"filtered_count": 0, "passed_count": 0},
				"message": "No entry recommendations to filter"
			}

		if not strategy_name:
			return {
				"status": "success",
				"input": input_data,
				"output": {"filtered_count": 0, "passed_count": len(entry_recommendations)},
				"message": "No strategy_name in context, skipping filter"
			}

		# Load strategy config to get entry_filter formula
		try:
			strategy_manager = StrategyManager()
			strategy_result = strategy_manager.load_strategy(strategy_name)
			if strategy_result.get("status") != "success":
				return {
					"status": "success",
					"input": input_data,
					"output": {"filtered_count": 0, "passed_count": len(entry_recommendations)},
					"message": f"Could not load strategy {strategy_name}"
				}

			strategy_data = strategy_result.get("data", {})
			entry_config = strategy_data.get("entry", {}).get("parameters", {})
			entry_filter_config = entry_config.get("entry_filter")

			if not entry_filter_config:
				return {
					"status": "success",
					"input": input_data,
					"output": {"filtered_count": 0, "passed_count": len(entry_recommendations)},
					"message": "No entry_filter configured"
				}

			entry_filter_formula = entry_filter_config.get("formula")
			if not entry_filter_formula:
				return {
					"status": "success",
					"input": input_data,
					"output": {"filtered_count": 0, "passed_count": len(entry_recommendations)},
					"message": "No formula in entry_filter config"
				}

			# Apply filter to recommendations
			filtered_recommendations = []
			blocked_count = 0

			for rec in entry_recommendations:
				ticker = rec.get("ticker")
				
				# If no data for ticker, pass through
				if ticker not in data_history:
					filtered_recommendations.append(rec)
					continue

				df = data_history[ticker]
				if df.empty:
					filtered_recommendations.append(rec)
					continue

				# Get last 5 days of data for evaluation (supports shift notation like [-1], [-2])
				# Data is sorted newest-first, so [:5] gets the most recent 5 days
				last_5_days = df.iloc[:5].copy() if len(df) >= 5 else df.copy()
				# Evaluate entry_filter formula
				try:
					passes_filter = evaluate(entry_filter_formula, last_5_days)
					if passes_filter:
						filtered_recommendations.append(rec)
					else:
						blocked_count += 1
						self.logger.debug(f"Entry filter blocked {ticker}")
				except Exception as e:
					self.logger.warning(f"Error evaluating entry_filter for {ticker}: {e}")
					# On error, pass through the recommendation
					filtered_recommendations.append(rec)

			# Update context with filtered recommendations
			self.context.set("entry_recommendations", filtered_recommendations)

			if blocked_count > 0:
				self.logger.info(f"Entry filter blocked {blocked_count} of {len(entry_recommendations)} recommendations")

			return {
				"status": "success",
				"input": input_data,
				"output": {
					"filtered_count": blocked_count,
					"passed_count": len(filtered_recommendations),
				},
				"message": f"Filtered {blocked_count} recommendations"
			}

		except Exception as e:
			self.logger.error(f"Error in entry_filter: {e}")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Entry filter error: {str(e)}"
			}
