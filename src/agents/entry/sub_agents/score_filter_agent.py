"""Agent to filter watchlist by minimum entry score threshold."""

from typing import Any, Dict, Optional
from core.agent import Agent


class ScoreFilterAgent(Agent):
	"""Filter watchlist tickers by minimum entry score.

	Removes tickers with entry_score below configured threshold.
	Early filtering gate to focus analysis on strongest signals.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Filter watchlist by entry score threshold.

		Reads entry_scores from context and strategy config to determine
		minimum acceptable score, removes tickers below threshold.

		Args:
			input_data: Input data (not used, uses context)

		Returns:
			Response with filtering results
		"""
		if input_data is None:
			input_data = {}

		# Get config and context data
		strategy_config = self.context.get("strategy_config") or {}
		entry_config = strategy_config.get("entry", {}).get("parameters", {})
		score_filter_config = entry_config.get("score_filter", {})

		# Get threshold from config, default to 0 (no filter)
		min_score = score_filter_config.get("min", 0)

		if min_score <= 0:
			# No filtering if threshold is 0 or not configured
			return {
				"status": "success",
				"input": input_data,
				"output": {"filtered_count": 0, "passed_count": 0},
				"message": "No score filter configured (min threshold <= 0)"
			}

		# Get data from context
		watchlist = self.context.get("watchlist") or {}
		entry_scores = self.context.get("entry_scores") or {}

		if not watchlist:
			return {
				"status": "success",
				"input": input_data,
				"output": {"filtered_count": 0, "passed_count": 0},
				"message": "No watchlist to filter"
			}

		self.logger.info(f"[SCORE-FILTER] Filtering by minimum entry score: {min_score}")

		# Filter watchlist by entry score
		original_count = len(watchlist)
		filtered_watchlist = {}
		blocked_count = 0
		passed_tickers = []

		for ticker in list(watchlist.keys()):
			score = entry_scores.get(ticker, 0)

			if score >= min_score:
				filtered_watchlist[ticker] = watchlist[ticker]
				passed_tickers.append(ticker)
			else:
				blocked_count += 1
				self.logger.debug(f"[SCORE-FILTER] {ticker}: BLOCKED (score {score:.2f} < min {min_score})")

		# Update context with filtered watchlist
		self.context.set("watchlist", filtered_watchlist)

		# Log summary
		self.logger.info(f"[SCORE-FILTER] Results: {len(filtered_watchlist)} passed, {blocked_count} blocked")
		if passed_tickers:
			self.logger.debug(f"[SCORE-FILTER] Passed: {passed_tickers[:5]}{'...' if len(passed_tickers) > 5 else ''}")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"original_count": original_count,
				"filtered_count": blocked_count,
				"passed_count": len(filtered_watchlist),
				"min_score_threshold": min_score,
			},
			"message": f"Filtered {blocked_count} tickers below score threshold {min_score}"
		}
