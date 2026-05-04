"""Strategy agent for executing trading strategies."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from core.agent import Agent
from tools.strategy.strategy import StrategyManager
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
					project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", "."))
					strategy_manager = StrategyManager(project_root)
					strategy_result = strategy_manager.load_strategy(strategy_name)
					if strategy_result.get("status") == "success":
						strategy_config = strategy_result.get("data", {})
						self.context.set("strategy_config", strategy_config)
			except Exception as e:
				self.logger.warning(f"Failed to load strategy config: {str(e)}")

		tickers = input_data.get("tickers", [])

		# If no tickers in input, load from strategy universe
		if not tickers and strategy_config:
			universe = strategy_config.get("universe")
			if universe:
				tickers = self._load_tickers_from_source(universe)
				self.logger.info(f"Loaded {len(tickers)} tickers from universe '{universe}'")

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
