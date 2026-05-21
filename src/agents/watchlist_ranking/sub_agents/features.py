"""Features extraction agent for LGBM ranking."""

from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
from core.agent import Agent


class FeaturesAgent(Agent):
	"""Extract features from data_history for LGBM model.

	Transforms OHLCV + indicators into feature matrix for model training/ranking.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Extract features from historical data.

		If data_history is already in context with calculated indicators/alphas,
		simply extracts them. Otherwise, calculates features (delegates to WatchlistAlphasAgent
		if alphas not already calculated).

		Creates a feature matrix with:
		- Price features (open, high, low, close, volume)
		- Indicator features (all calculated indicators)
		- Alpha features (if pre-calculated by WatchlistAlphasAgent)

		Args:
			input_data: Input data (optional)

		Returns:
			Response with features DataFrame in context
		"""
		if input_data is None:
			input_data = {}

		data_history = self.context.get("data_history") or {}
		tickers = list(data_history.keys())

		self.logger.info(f"[FEATURES] Extracting features from {len(tickers)} tickers")

		if not data_history:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No data_history in context (use WatchlistAlphasAgent to calculate)"
			}

		# Check if alphas were already calculated by WatchlistAlphasAgent
		alpha_names = self.context.get("alpha_names") or []
		if alpha_names:
			self.logger.info(f"[FEATURES] Using pre-calculated alphas from WatchlistAlphasAgent: {len(alpha_names)} alphas")

		# Build feature matrix: columns are features, rows are (ticker, date) pairs
		features_list = []
		ticker_date_pairs = []

		for ticker in tickers:
			df = data_history[ticker]
			if df.empty:
				continue

			# Get latest row (most recent date, since data is sorted newest-first)
			row = df.iloc[0].to_dict()

			# Extract ALL available features from row (including pre-calculated alphas)
			features = self._extract_row_features(row)
			features["ticker"] = ticker

			features_list.append(features)
			ticker_date_pairs.append((ticker, row.get("timestamp")))

		# Convert to DataFrame
		features_df = pd.DataFrame(features_list)

		self.logger.info(f"[FEATURES] Extracted {len(features_df)} ticker-date pairs with {len(features_df.columns)} features")
		self.logger.debug(f"[FEATURES] Feature columns: {list(features_df.columns)}")

		# Store in context
		self.context.set("features_df", features_df)
		self.context.set("ticker_date_pairs", ticker_date_pairs)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"features_count": len(features_df),
				"feature_columns": len(features_df.columns) - 1,  # Exclude ticker column
			},
			"message": f"Extracted features for {len(features_df)} tickers"
		}

	def _extract_row_features(self, row: Dict[str, Any]) -> Dict[str, Any]:
		"""Extract features from a single data row.

		Converts row data into feature dict, handling missing values.

		Args:
			row: Data row (from DataFrame)

		Returns:
			Features dict
		"""
		features = {}

		# Price features (use safe access with defaults)
		for col in ["open", "high", "low", "close", "volume"]:
			features[col] = float(row.get(col, 0))

		# All indicator columns (everything else except metadata)
		exclude_cols = {"timestamp", "ticker", "open", "high", "low", "close", "volume", "Dividends", "Stock Splits"}

		for col, value in row.items():
			if col not in exclude_cols:
				try:
					features[col] = float(value) if pd.notna(value) else 0.0
				except (ValueError, TypeError):
					features[col] = 0.0

		# Handle NaN values - replace with 0 (will be improved with imputation)
		for key in features:
			if pd.isna(features[key]):
				features[key] = 0.0

		return features
