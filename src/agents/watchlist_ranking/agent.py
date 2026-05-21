"""Watchlist ranking agent using LGBM model."""

from typing import Any, Dict, Optional
from core.agent import Agent
from agents.watchlist_ranking.sub_agents import FeaturesAgent, TrainAgent, RankAgent


class WatchlistRankingAgent(Agent):
	"""Agent for ranking tickers using LGBM model.

	Orchestrates a machine learning pipeline:
	1. Extract features from historical data
	2. Train LGBM model on features and labels
	3. Rank tickers by model predictions
	"""

	def __init__(self, name: str = "WatchlistRankingAgent", context: Optional[Any] = None):
		"""Initialize watchlist ranking agent.

		Args:
			name: Agent name
			context: Optional shared AgentContext
		"""
		super().__init__(name, context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process watchlist ranking pipeline.

		Executes:
		1. Features extraction from data_history
		2. Model training (if training mode)
		3. Ticker ranking by model scores

		Args:
			input_data: Input with optional mode='train'|'rank'

		Returns:
			Response with ranked watchlist scores
		"""
		if input_data is None:
			input_data = {}

		# Check for mode in input_data first, then context (for flows that set it in context)
		mode = input_data.get("mode") or self.context.get("ranking_mode") or "rank"
		strategy_name = input_data.get("strategy_name") or self.context.get("strategy_name")

		self.logger.info(f"[WATCHLIST-RANKING] Starting {mode} mode for {strategy_name}")
		watchlist_before = self.context.get("watchlist")
		self.logger.debug(f"[WATCHLIST-RANKING] Watchlist at start: {type(watchlist_before)} with {len(watchlist_before) if watchlist_before else 0} items")

		# Step 1: Extract features
		features_agent = FeaturesAgent("FeaturesStep", self.context)
		features_result = features_agent.process(input_data)

		if features_result.get("status") != "success":
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Features extraction failed: {features_result.get('message')}"
			}

		# Step 2: Train or load model
		train_agent = TrainAgent("TrainStep", self.context)
		train_result = train_agent.process({
			"mode": mode,
			"strategy_name": strategy_name,
		})

		if train_result.get("status") != "success":
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Model training failed: {train_result.get('message')}"
			}

		# If training mode, return training result
		if mode == "train":
			return {
				"status": "success",
				"input": input_data,
				"output": train_result.get("output", {}),
				"message": train_result.get("message", "Model trained successfully")
			}

		# Step 3: Rank tickers (for rank mode)
		rank_agent = RankAgent("RankStep", self.context)
		rank_result = rank_agent.process({
			"strategy_name": strategy_name,
		})

		if rank_result.get("status") != "success":
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Ranking failed: {rank_result.get('message')}"
			}

		# Store ranking scores in context and update watchlist
		output = rank_result.get("output", {})
		scores = output.get("scores", {})
		self.context.set("ranking_scores", scores)
		self.context.set("ranked_tickers", output.get("ranked", []))

		# Merge ranking scores into ticker_scores to preserve signal metadata
		self._merge_ranking_into_scores(scores)

		# Update watchlist with ranking scores and sort
		watchlist = self.context.get("watchlist")
		watchlist_len = len(watchlist) if isinstance(watchlist, (dict, list)) else 0
		self.logger.warning(f"[WATCHLIST-RANKING] Watchlist before update: {type(watchlist).__name__} with {watchlist_len} items (watchlist bool={bool(watchlist)})")

		# Force update even if watchlist appears empty but scores exist
		if watchlist or scores:
			if not watchlist:
				# Watchlist is empty but we have scores - create it from scores
				self.logger.warning(f"[WATCHLIST-RANKING] Watchlist is empty, creating from {len(scores)} ranking scores")
				watchlist = {ticker: {} for ticker in scores.keys()}

		if watchlist:
			if isinstance(watchlist, dict):
				# Dict format: {ticker: {data}}
				# Add ranking_score to each ticker's data and sort by it
				self.logger.info(f"[WATCHLIST-RANKING] Processing dict watchlist with {len(watchlist)} tickers")
				count_added = 0
				for ticker, data in watchlist.items():
					if isinstance(data, dict):
						# Convert numpy float64 to native Python float for JSON serialization
						score = scores.get(ticker, 0)
						data["ranking_score"] = float(score) if score is not None else 0
						count_added += 1
				self.logger.info(f"[WATCHLIST-RANKING] Added ranking_score to {count_added} watchlist items")

				# Check that ranking_score was actually added
				if watchlist:
					first_ticker = list(watchlist.keys())[0]
					first_data = watchlist[first_ticker]
					self.logger.info(f"[WATCHLIST-RANKING] First ticker '{first_ticker}' data keys: {list(first_data.keys())}")

				# Sort dict by ranking_score descending (convert to ordered dict-like structure)
				sorted_items = sorted(watchlist.items(), key=lambda x: x[1].get("ranking_score", 0) if isinstance(x[1], dict) else 0, reverse=True)
				sorted_watchlist = {ticker: data for ticker, data in sorted_items}
				self.context.set("watchlist", sorted_watchlist)
				self.logger.info(f"[WATCHLIST-RANKING] Updated watchlist: {len(sorted_watchlist)} tickers ranked by LGBM scores")

			elif isinstance(watchlist, list):
				# List format: [{ticker: ..., ...}]
				# Add ranking_score to each item and sort
				for item in watchlist:
					if isinstance(item, dict):
						ticker = item.get("ticker", "")
						# Convert numpy float64 to native Python float for JSON serialization
						score = scores.get(ticker, 0)
						item["ranking_score"] = float(score) if score is not None else 0

				# Sort list by ranking_score descending
				sorted_watchlist = sorted(watchlist, key=lambda x: x.get("ranking_score", 0) if isinstance(x, dict) else 0, reverse=True)
				self.context.set("watchlist", sorted_watchlist)
				self.logger.info(f"[WATCHLIST-RANKING] Updated watchlist: {len(sorted_watchlist)} tickers ranked by LGBM scores")

		return {
			"status": "success",
			"input": input_data,
			"output": output,
			"message": f"Ranked {len(scores)} tickers, sorted {len(watchlist) if watchlist else 0} watchlist items"
		}

	def _merge_ranking_into_scores(self, ranking_scores: Dict[str, float]) -> None:
		"""Merge LGBM ranking scores into ticker_scores while preserving signal metadata.

		Adds ranking_model_score to each ticker's score info, allowing downstream
		processors to use both signal scores and model predictions.

		Args:
			ranking_scores: Dict of ticker -> ranking score from LGBM model
		"""
		ticker_scores = self.context.get("ticker_scores") or {}

		if not ticker_scores:
			# If no signal scores yet, create structure with just ranking scores
			ticker_scores = {
				ticker: {
					"ranking_model_score": float(score),
					"score": float(score),  # Use ranking score as primary
					"raw_score": float(score),
					"triggered_signals": [],
					"signal_count": 0,
				}
				for ticker, score in ranking_scores.items()
			}
		else:
			# Merge ranking scores into existing signal scores
			for ticker, score in ranking_scores.items():
				if ticker in ticker_scores:
					# Preserve existing signal data, add ranking score
					ticker_scores[ticker]["ranking_model_score"] = float(score)
					# Use ranking score as primary score for entry decisions
					ticker_scores[ticker]["score"] = float(score)
				else:
					# Ticker has ranking score but no signals, create entry
					ticker_scores[ticker] = {
						"ranking_model_score": float(score),
						"score": float(score),
						"raw_score": float(score),
						"triggered_signals": [],
						"signal_count": 0,
					}

		self.context.set("ticker_scores", ticker_scores)
		self.logger.info(f"[WATCHLIST-RANKING] Merged ranking scores into ticker_scores for {len(ticker_scores)} tickers")

	def train(self, strategy_name: str) -> Dict[str, Any]:
		"""Train LGBM model for a strategy.

		Args:
			strategy_name: Strategy to train model for

		Returns:
			Training result
		"""
		return self.process({
			"mode": "train",
			"strategy_name": strategy_name,
		})

	def rank(self, strategy_name: str) -> Dict[str, Any]:
		"""Rank tickers using trained LGBM model.

		Args:
			strategy_name: Strategy to rank tickers for

		Returns:
			Ranking result with ticker scores
		"""
		return self.process({
			"mode": "rank",
			"strategy_name": strategy_name,
		})
