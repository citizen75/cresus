"""Ranking agent for LGBM watchlist scoring."""

from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
from core.agent import Agent


class RankAgent(Agent):
	"""Rank tickers using LGBM model predictions.

	Applies trained model to score each ticker for trading.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Rank tickers by model score.

		Args:
			input_data: Dict with 'strategy_name'

		Returns:
			Response with ranked scores
		"""
		if input_data is None:
			input_data = {}

		strategy_name = input_data.get("strategy_name")

		features_df = self.context.get("features_df")
		lgb_model = self.context.get("lgb_model")

		if features_df is None or features_df.empty:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No features available"
			}

		self.logger.info(f"[RANK] Ranking {len(features_df)} tickers")

		# Generate scores
		if lgb_model is not None:
			scores = self._score_with_model(features_df, lgb_model)
		else:
			scores = self._score_with_features(features_df)

		# Combine tickers with scores, converting numpy types to native Python floats
		scores_dict = {ticker: float(score) for ticker, score in zip(features_df["ticker"], scores)}

		# Sort by score descending
		ranked = sorted(scores_dict.items(), key=lambda x: x[1], reverse=True)

		self.logger.info(f"[RANK] Top 5 tickers: {ranked[:5]}")

		# Store ranking scores in context (don't overwrite ticker_scores which contains signal info)
		self.context.set("ranking_model_scores", scores_dict)
		self.context.set("ranked_tickers", ranked)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"scores": scores_dict,
				"ranked": ranked[:20],  # Top 20
			},
			"message": f"Ranked {len(scores_dict)} tickers"
		}

	def _score_with_model(self, features_df: pd.DataFrame, model: Any) -> np.ndarray:
		"""Score tickers using LGBM model.

		Args:
			features_df: Features DataFrame
			model: Trained LGBM model

		Returns:
			Array of scores
		"""
		try:
			# Select only numeric columns (exclude ticker, date, and other non-numeric types)
			X = features_df.drop(columns=["ticker"], errors="ignore")
			numeric_cols = [c for c in X.columns if X[c].dtype in ['float64', 'float32', 'int64', 'int32']]
			X = X[numeric_cols].fillna(0)

			# Suppress shape checking in case features changed since training
			scores = model.predict(X, predict_disable_shape_check=True)
			return scores
		except Exception as e:
			self.logger.warning(f"[RANK] Model prediction failed: {str(e)}, falling back to feature scoring")
			return self._score_with_features(features_df)

	def _score_with_features(self, features_df: pd.DataFrame) -> np.ndarray:
		"""Score tickers using simple feature-based scoring.

		Fallback when model is not available.

		Args:
			features_df: Features DataFrame

		Returns:
			Array of scores
		"""
		# Simple scoring: normalize features and take weighted sum
		X = features_df.drop(columns=["ticker"]).fillna(0)

		scores = np.zeros(len(X))

		# Weight common momentum/trend indicators
		indicator_weights = {
			"rsi_14": 0.1,
			"rsi_5": 0.1,
			"macd_12_26": 0.1,
			"adx_14": 0.1,
			"ema_10": 0.05,
			"ema_20": 0.05,
			"ema_50": 0.05,
			"volume_sma_20": 0.05,
			"sha_5_green": 0.1,
			"sha_10_green": 0.1,
			"bb_20_upper": 0.05,
			"close": 0.05,
		}

		for col, weight in indicator_weights.items():
			if col in X.columns:
				# Normalize column to 0-1
				col_data = X[col].values
				col_min = col_data.min()
				col_max = col_data.max()

				if col_max > col_min:
					normalized = (col_data - col_min) / (col_max - col_min)
				else:
					normalized = np.zeros(len(col_data))

				scores += normalized * weight

		return scores / sum(indicator_weights.values())
