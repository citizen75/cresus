"""Strategy agent for executing trading strategies."""

from typing import Any, Dict, Optional, List
import re
from core.agent import Agent
from tools.strategy.strategy import StrategyManager
from tools.strategy.validator import StrategyValidator
from tools.universe.universe import Universe


class StrategyAgent(Agent):
	"""Agent for executing and managing trading strategies."""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process strategy execution.

		Loads tickers from strategy source configuration and stores in context.

		Args:
			input_data: Input data for strategy processing

		Returns:
			Response dictionary with strategy results
		"""
		if input_data is None:
			input_data = {}

		self.context.set("strategy_input", input_data)

		# Load strategy config if not already in context
		strategy_config = self.context.get("strategy_config")
		if not strategy_config:
			try:
				strategy_name = self.name.split("[")[1].rstrip("]") if "[" in self.name else None
				if strategy_name:
					# Use StrategyManager without project_root to use centralized ~/.cresus/db/strategies
					strategy_manager = StrategyManager()
					strategy_result = strategy_manager.load_strategy(strategy_name)
					if strategy_result.get("status") == "success":
						strategy_config = strategy_result.get("data", {})

						# Validate strategy configuration
						validator = StrategyValidator()
						is_valid, validation_errors = validator.validate(strategy_config)
						if not is_valid:
							error_msg = f"Strategy '{strategy_name}' validation failed:\n"
							for error in validation_errors:
								error_msg += f"  - {error}\n"
							self.logger.error(error_msg)
							return {
								"status": "error",
								"input": input_data,
								"output": {},
								"message": error_msg,
								"validation_errors": validation_errors
							}

						# Extract indicators from filter formula and add to strategy config
						self._add_filter_indicators_to_config(strategy_config)

						self.context.set("strategy_config", strategy_config)
						self.logger.info(f"Loaded and validated strategy: {strategy_name}")
					else:
						self.logger.error(f"Failed to load strategy '{strategy_name}': {strategy_result.get('message', 'Unknown error')}")
						return {
							"status": "error",
							"input": input_data,
							"output": {},
							"message": strategy_result.get("message", "Failed to load strategy")
						}
			except Exception as e:
				self.logger.error(f"Failed to load strategy config: {str(e)}")
				return {
					"status": "error",
					"input": input_data,
					"output": {},
					"message": f"Failed to load strategy: {str(e)}"
				}

		tickers = input_data.get("tickers", [])

		# If no tickers in input, load from strategy universe or direct tickers
		if not tickers and strategy_config:
			universe = strategy_config.get("universe")
			if universe:
				tickers = self._load_tickers_from_source(universe)
				self.logger.info(f"Loaded {len(tickers)} tickers from universe '{universe}'")
			else:
				# Fallback: check for direct tickers in strategy config
				tickers = strategy_config.get("tickers", [])
				if tickers:
					self.logger.info(f"Loaded {len(tickers)} tickers directly from strategy config: {tickers}")

		# Store tickers in context for downstream agents
		self.context.set("tickers", tickers)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"strategy": self.name,
				"tickers": tickers,
			},
		}

	def _add_filter_indicators_to_config(self, config: Dict[str, Any]) -> None:
		"""Extract indicators from filter formula and add to strategy config.

		Finds all indicator references in the watchlist filter formula and ensures
		they're included in the strategy config's indicators list so they're
		calculated by DataAgent before FilterAgent runs.

		Note: Indicators are usually already in the config, so this is a safety net.
		Most indicators should be declared upfront in the strategy config.

		Args:
			config: Strategy configuration dict (modified in-place)
		"""
		watchlist_config = config.get("watchlist", {})
		filter_config = watchlist_config.get("parameters", {}).get("filter", {})
		filter_formula = filter_config.get("formula")

		if not filter_formula:
			return

		# Extract only from the filter formula (DSL syntax: bare indicator names)
		# Only extract identifiers that look like indicator names (contain underscore or all lowercase)
		pattern = r'\b([a-z_][a-z0-9_]*)\b'
		matches = re.findall(pattern, filter_formula.lower())

		# Filter out common non-indicator words
		non_indicators = {"and", "or", "not", "if", "else"}
		required_indicators = [m for m in set(matches) if m not in non_indicators and "_" in m]

		if not required_indicators:
			return

		# Add to strategy config indicators if not already there
		current_indicators = config.get("indicators", [])
		added_indicators = [ind for ind in required_indicators if ind not in current_indicators]

		if added_indicators:
			config["indicators"] = current_indicators + added_indicators
			self.logger.debug(f"Added filter indicators to strategy config: {added_indicators}")

	def _load_tickers_from_source(self, source: str) -> list:
		"""Load tickers from universe CSV file.

		Uses TickerYahoo if available, otherwise falls back to ISIN.

		Args:
			source: Source name (e.g., 'cac40', 'etf_pea_full')

		Returns:
			List of ticker symbols or ISINs
		"""
		try:
			universe = Universe(source)
			if not universe.exists():
				self.logger.warning(f"Universe '{source}' not found")
				return []

			tickers = universe.get_tickers()
			self.logger.debug(f"Loaded {len(tickers)} tickers from universe '{source}'")
			return tickers

		except Exception as e:
			self.logger.error(f"Failed to load tickers from universe '{source}': {e}")
			return []
