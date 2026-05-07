"""Feature engineering for market regime detection."""

from typing import Any, Dict, Optional
import numpy as np
import pandas as pd
from core.agent import Agent


class FeatureEngineerAgent(Agent):
	"""Compute cross-sectional features and factor returns.

	Reads from context:
		prices_df, returns_df, volume_df, high_df, low_df, regime_config

	Writes to context:
		features_df: DataFrame with computed features indexed by date
	"""

	def __init__(self, name: str = "FeatureEngineerAgent"):
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Compute all features."""
		if input_data is None:
			input_data = {}

		prices_df = self.context.get("prices_df")
		returns_df = self.context.get("returns_df")
		volume_df = self.context.get("volume_df")
		high_df = self.context.get("high_df")
		low_df = self.context.get("low_df")
		regime_config = self.context.get("regime_config") or {}

		if prices_df is None or prices_df.empty:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No price data in context"
			}

		try:
			features_dict = {}

			# Breadth features
			features_dict["breadth_above_sma20"] = self._compute_breadth_above_sma(prices_df, 20)
			features_dict["breadth_above_sma50"] = self._compute_breadth_above_sma(prices_df, 50)
			features_dict["breadth_above_sma200"] = self._compute_breadth_above_sma(prices_df, 200)
			features_dict["breadth_change_5d"] = self._compute_breadth_momentum(
				features_dict["breadth_above_sma50"], 5
			)
			features_dict["adv_decline_ratio"] = self._compute_adv_decline_ratio(returns_df)

			# Correlation & dispersion
			features_dict["cross_correlation"] = self._compute_cross_correlation(returns_df, 20)
			features_dict["dispersion"] = self._compute_dispersion(returns_df, 1)

			# Volatility
			features_dict["avg_atr_norm"] = self._compute_avg_atr_norm(high_df, low_df, prices_df, 14)
			features_dict["vol_regime_score"] = self._compute_vol_regime_score(
				features_dict["avg_atr_norm"], 20
			)

			# Factor returns
			factor_returns = self._compute_factor_returns(returns_df)
			features_dict.update(factor_returns)

			# Combine into single DataFrame
			features_df = pd.DataFrame(features_dict)
			features_df = features_df.sort_index()

			# Store in context
			self.context.set("features_df", features_df)
			self.context.set("feature_names", list(features_dict.keys()))

			self.logger.info(f"Computed {len(features_dict)} features, {len(features_df)} rows")

			return {
				"status": "success",
				"input": input_data,
				"output": {
					"n_features": len(features_dict),
					"feature_names": list(features_dict.keys()),
					"n_rows": len(features_df),
					"missing_ratio": float(features_df.isna().sum().sum() / (len(features_df) * len(features_dict)))
				},
				"message": f"Computed {len(features_dict)} features"
			}

		except Exception as e:
			self.logger.exception(f"Error computing features: {e}")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Feature engineering failed: {str(e)}"
			}

	def _compute_breadth_above_sma(self, prices_df: pd.DataFrame, period: int) -> pd.Series:
		"""Fraction of tickers with price > SMA(period)."""
		sma = prices_df.rolling(period).mean()
		above = (prices_df > sma).astype(int)
		breadth = above.mean(axis=1)
		return breadth

	def _compute_breadth_momentum(self, breadth_series: pd.Series, lookback: int = 5) -> pd.Series:
		"""Change in breadth over last lookback days."""
		breadth_change = breadth_series.diff(lookback)
		return breadth_change

	def _compute_adv_decline_ratio(self, returns_df: pd.DataFrame) -> pd.Series:
		"""Advancing/declining ratio: count(ret>0) / count(ret<0), daily."""
		advances = (returns_df > 0).sum(axis=1)
		declines = (returns_df < 0).sum(axis=1)

		# Avoid division by zero
		ratio = advances / declines.replace(0, 1)
		ratio = ratio.replace([np.inf, -np.inf], 1.0)

		return ratio

	def _compute_cross_correlation(self, returns_df: pd.DataFrame, window: int = 20) -> pd.Series:
		"""Rolling average pairwise correlation of returns."""
		n = len(returns_df)
		result = pd.Series(index=returns_df.index, dtype=float)

		cols = returns_df.columns
		k = len(cols)

		for i in range(window, n):
			try:
				block = returns_df.iloc[i - window:i].values
				c = np.corrcoef(block.T)

				# Mean of off-diagonal elements
				mask = ~np.eye(k, dtype=bool)
				mean_corr = np.nanmean(c[mask])

				result.iloc[i] = mean_corr if not np.isnan(mean_corr) else 0.0
			except Exception:
				result.iloc[i] = 0.0

		return result

	def _compute_dispersion(self, returns_df: pd.DataFrame, window: int = 1) -> pd.Series:
		"""Cross-sectional std dev of daily returns."""
		if window == 1:
			dispersion = returns_df.std(axis=1)
		else:
			dispersion = returns_df.rolling(window).std(axis=1)

		return dispersion

	def _compute_avg_atr_norm(
		self, high_df: pd.DataFrame, low_df: pd.DataFrame, prices_df: pd.DataFrame, period: int = 14
	) -> pd.Series:
		"""Average ATR/Close across universe."""
		tr = high_df - low_df
		atr = tr.rolling(period).mean()
		atr_norm = atr / prices_df

		# Mean across tickers
		avg_atr_norm = atr_norm.mean(axis=1)

		return avg_atr_norm

	def _compute_vol_regime_score(self, avg_atr_norm: pd.Series, window: int = 20) -> pd.Series:
		"""Trending vol vs mean-reverting score."""
		# Z-score of current ATR vs rolling mean ATR
		rolling_mean = avg_atr_norm.rolling(window).mean()
		rolling_std = avg_atr_norm.rolling(window).std()

		# Avoid division by zero
		rolling_std = rolling_std.replace(0, 1)

		z_score = (avg_atr_norm - rolling_mean) / rolling_std
		z_score = z_score.fillna(0)

		return z_score

	def _compute_factor_returns(self, returns_df: pd.DataFrame) -> Dict[str, pd.Series]:
		"""Compute 20d factor returns for all 4 factors."""
		result = {}

		# Momentum factor: long top 50% by 20d return, short bottom 50%
		momentum_ret = self._compute_factor_pnl(returns_df, rank_by="momentum", window=20)
		result["momentum_factor_return"] = momentum_ret

		# Mean reversion: opposite of momentum
		meanrev_ret = self._compute_factor_pnl(returns_df, rank_by="meanrev", window=20)
		result["meanrev_factor_return"] = meanrev_ret

		# Low volatility: long bottom 50% by vol, short top 50%
		lowvol_ret = self._compute_factor_pnl(returns_df, rank_by="lowvol", window=20)
		result["lowvol_factor_return"] = lowvol_ret

		# Quality: long (low vol AND momentum), short rest
		quality_ret = self._compute_factor_pnl(returns_df, rank_by="quality", window=20)
		result["quality_factor_return"] = quality_ret

		return result

	def _compute_factor_pnl(self, returns_df: pd.DataFrame, rank_by: str, window: int = 20) -> pd.Series:
		"""Compute daily factor P&L for a given ranking."""
		n = len(returns_df)
		result = pd.Series(index=returns_df.index, dtype=float, data=0.0)

		for i in range(window, n):
			try:
				# Trailing returns or volatility
				if rank_by in ["momentum", "meanrev"]:
					metric = returns_df.iloc[i - window:i].sum()  # 20d trailing return
				elif rank_by == "lowvol":
					metric = returns_df.iloc[i - window:i].std()  # 20d rolling vol
				elif rank_by == "quality":
					ret_metric = returns_df.iloc[i - window:i].sum()
					vol_metric = returns_df.iloc[i - window:i].std()
					metric = ret_metric - vol_metric  # High ret, low vol
				else:
					metric = pd.Series(0, index=returns_df.columns)

				# Rank and assign groups
				ranks = metric.rank()
				n_tickers = len(ranks)
				median_rank = n_tickers / 2

				if rank_by == "momentum":
					long_mask = ranks >= median_rank
					short_mask = ranks < median_rank
				elif rank_by == "meanrev":
					long_mask = ranks < median_rank  # Opposite
					short_mask = ranks >= median_rank
				elif rank_by == "lowvol":
					long_mask = ranks < median_rank  # Low vol = low metric
					short_mask = ranks >= median_rank
				elif rank_by == "quality":
					long_mask = ranks >= median_rank
					short_mask = ranks < median_rank
				else:
					long_mask = short_mask = pd.Series(False, index=returns_df.columns)

				# Compute factor return: mean(long) - mean(short) on day i+1
				if i + 1 < n:
					next_returns = returns_df.iloc[i + 1]
					long_ret = next_returns[long_mask].mean() if long_mask.any() else 0
					short_ret = next_returns[short_mask].mean() if short_mask.any() else 0
					factor_pnl = long_ret - short_ret
					result.iloc[i] = factor_pnl

			except Exception:
				result.iloc[i] = 0.0

		return result
