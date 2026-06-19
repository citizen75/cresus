"""Watchlist sorting agent — sorts the watchlist dict by a configurable column."""

from typing import Any, Dict, Optional
from core.agent import Agent


class WatchlistSortingAgent(Agent):
    """Sort the watchlist dict by a column defined in strategy config.

    Reads strategy_config.watchlist.parameters.sorting:
        sorting:
          column: score       # key inside each ticker's dict
          order: desc         # desc (default) or asc

    Falls back to column=score, order=desc when no config is provided.
    Tickers missing the sort column are placed last regardless of direction.
    """

    def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if input_data is None:
            input_data = {}

        watchlist = self.context.get("watchlist") or {}
        if not watchlist:
            return {
                "status": "success",
                "input": input_data,
                "output": {"sorted": 0},
                "message": "Watchlist is empty, nothing to sort",
            }

        strategy_config = self.context.get("strategy_config") or {}
        sorting_config = (
            strategy_config
            .get("watchlist", {})
            .get("parameters", {})
            .get("sorting", {})
        )

        column = sorting_config.get("column", "score")
        order = sorting_config.get("order", "desc")
        ascending = order.lower() == "asc"

        sorted_watchlist = dict(sorted(
            watchlist.items(),
            key=lambda item: (
                item[1].get(column) is None,        # None values always last
                (item[1].get(column, 0) or 0) * (-1 if not ascending else 1),
            ),
        ))

        self.context.set("watchlist", sorted_watchlist)

        self.logger.info(
            f"[SORTING] Sorted {len(sorted_watchlist)} tickers "
            f"by '{column}' {order.upper()}"
        )

        return {
            "status": "success",
            "input": input_data,
            "output": {
                "sorted": len(sorted_watchlist),
                "column": column,
                "order": order,
            },
        }
