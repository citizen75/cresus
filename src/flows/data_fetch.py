"""Data fetch flow for syncing market data and fundamentals.

Fetches both historical and fundamental data for a given universe
using the DataManager.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from loguru import logger


class DataFetchFlow(Flow):
	"""Flow for fetching and syncing market data.

	Fetches both historical and fundamental data for all tickers
	in a specified universe with incremental updates.
	"""

	def __init__(self, universe: str = "cac40", context: Optional[Any] = None):
		"""Initialize data fetch flow with universe.

		Args:
			universe: Universe name to fetch data for (default: cac40)
			context: Optional AgentContext for shared state
		"""
		super().__init__(f"DataFetchFlow[{universe}]", context=context)
		self.universe = universe

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Fetch data for the specified universe.

		Args:
			input_data: Optional input with universe override

		Returns:
			Flow result with fetch status and statistics
		"""
		flow_input = input_data or {}
		universe = flow_input.get("universe", self.universe)

		try:
			from tools.data.manager import DataManager
			from pathlib import Path

			# Initialize DataManager with project root
			project_root = Path(__file__).parent.parent.parent
			dm = DataManager(project_root)

			logger.info(f"Starting data fetch for universe: {universe}")

			# Fetch both history and fundamental data
			result = dm.fetch_all(universe)

			if result.get("status") == "success":
				logger.info(
					f"Data fetch completed for {universe}: "
					f"history={result.get('history_fetched')}/{result.get('total')}, "
					f"fundamental={result.get('fundamental_fetched')}/{result.get('total')}"
				)
				return {
					"status": "success",
					"universe": universe,
					"message": result.get("message", "Data fetch completed"),
					"history_fetched": result.get("history_fetched", 0),
					"history_failed": result.get("history_failed", 0),
					"fundamental_fetched": result.get("fundamental_fetched", 0),
					"fundamental_failed": result.get("fundamental_failed", 0),
					"total_tickers": result.get("total", 0),
				}
			else:
				logger.error(f"Data fetch failed for {universe}: {result.get('message')}")
				return {
					"status": "error",
					"universe": universe,
					"message": result.get("message", "Data fetch failed"),
				}

		except Exception as e:
			logger.error(f"Data fetch flow error for {universe}: {e}", exc_info=True)
			return {
				"status": "error",
				"universe": universe,
				"message": f"Data fetch flow error: {e}",
			}
