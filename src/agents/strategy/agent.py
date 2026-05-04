"""Strategy agent for executing trading strategies."""

import csv
import os
from pathlib import Path
from typing import Any, Dict, Optional
from core.agent import Agent
from tools.strategy.strategy import StrategyManager


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

		Args:
			source: Source name (e.g., 'cac40')

		Returns:
			List of ticker symbols
		"""
		project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", "."))
		universe_file = project_root / "db" / "global" / "list" / f"{source}.csv"

		if not universe_file.exists():
			self.logger.warning(f"Universe file not found: {universe_file}")
			return []

		tickers = []
		try:
			with open(universe_file, "r") as f:
				reader = csv.reader(f)
				next(reader)  # Skip header (Name, Isin, TickerYahoo, Market, Currency)
				for row in reader:
					if row and len(row) > 2:
						# Column 2 is TickerYahoo (e.g., 'AADA.PA')
						tickers.append(row[2].strip())
		except Exception as e:
			self.logger.error(f"Failed to load tickers from {universe_file}: {e}")
			return []

		return tickers
