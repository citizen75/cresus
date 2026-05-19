"""Watchlist Scores Agent - Calculate scores for tickers in watchlist."""

from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
from core.agent import Agent


class WatchlistScoresAgent(Agent):
	"""Calculate composite scores for watchlist tickers.

	Computes ticker scores based on alpha factors and technical indicators,
	providing quantitative signals for entry/exit decisions.
	"""

	def __init__(self, name: str = "WatchlistScoresAgent", context: Optional[Any] = None):
		"""Initialize watchlist scores agent.

		Args:
			name: Agent name
			context: Optional shared AgentContext
		"""
		super().__init__(name, context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Calculate scores for watchlist tickers.

		Args:
			input_data: Optional input data (unused)

		Returns:
			Response with score calculation results
		"""
		if input_data is None:
			input_data = {}

		# Get watchlist and data
		watchlist = self.context.get("watchlist") or {}
		data_history = self.context.get("data_history") or {}

		if not watchlist:
			return {
				"status": "success",
				"input": input_data,
				"output": {},
				"message": "No watchlist to score"
			}

		self.logger.info(f"[SCORES] Calculating scores for {len(watchlist)} tickers")

		# Calculate scores for each ticker
		ticker_scores = {}
		errors = []

		for ticker in watchlist.keys():
			try:
				# Get ticker data
				ticker_data = data_history.get(ticker)
				if ticker_data is None or (isinstance(ticker_data, pd.DataFrame) and ticker_data.empty):
					continue

				# Calculate score
				score = self._calculate_ticker_score(ticker, ticker_data)
				ticker_scores[ticker] = score

			except Exception as e:
				errors.append(f"{ticker}: {str(e)}")
				self.logger.debug(f"[SCORES] Error calculating score for {ticker}: {str(e)}")

		self.logger.info(f"[SCORES] Calculated scores for {len(ticker_scores)} tickers")

		# Store scores in context
		self.context.set("ticker_scores", ticker_scores)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"scores_calculated": len(ticker_scores),
				"watchlist_count": len(watchlist),
				"errors": len(errors)
			},
			"message": f"Calculated scores for {len(ticker_scores)} watchlist tickers"
		}

	def _calculate_ticker_score(self, ticker: str, ticker_data: pd.DataFrame) -> Dict[str, Any]:
		"""Calculate composite score for a single ticker.

		Args:
			ticker: Ticker symbol
			ticker_data: OHLCV DataFrame with alphas

		Returns:
			Dictionary with score components and total score
		"""
		if ticker_data.empty:
			return {"score": 0.0}

		# Get the latest row (most recent data)
		latest = ticker_data.iloc[-1]

		scores = {}

		# Momentum score (from momentum alphas)
		momentum_score = self._score_momentum(latest)
		scores["momentum"] = momentum_score

		# Trend score (from trend alphas)
		trend_score = self._score_trend(latest)
		scores["trend"] = trend_score

		# Volatility score (from volatility alphas)
		volatility_score = self._score_volatility(latest)
		scores["volatility"] = volatility_score

		# Mean reversion score
		mr_score = self._score_mean_reversion(latest)
		scores["mean_reversion"] = mr_score

		# Composite score (weighted average)
		composite = (
			momentum_score * 0.35 +
			trend_score * 0.35 +
			volatility_score * 0.20 +
			mr_score * 0.10
		)

		scores["composite"] = composite

		return scores

	def _score_momentum(self, row: pd.Series) -> float:
		"""Calculate momentum score (0-100).

		Args:
			row: DataFrame row with latest data

		Returns:
			Momentum score (0-100)
		"""
		score = 50.0  # Neutral baseline

		# ROC contribution (5d and 10d)
		if "mom_roc5" in row and pd.notna(row["mom_roc5"]):
			roc5 = row["mom_roc5"]
			# Positive ROC increases score
			score += min(25, max(-25, roc5 / 2))

		if "mom_roc10" in row and pd.notna(row["mom_roc10"]):
			roc10 = row["mom_roc10"]
			score += min(25, max(-25, roc10 / 4))

		# RSI contribution
		if "mom_rsi14" in row and pd.notna(row["mom_rsi14"]):
			rsi = row["mom_rsi14"]
			# RSI above 50 = bullish momentum
			if rsi > 50:
				score += (rsi - 50) * 0.2
			else:
				score -= (50 - rsi) * 0.2

		# Clamp to 0-100
		return max(0.0, min(100.0, score))

	def _score_trend(self, row: pd.Series) -> float:
		"""Calculate trend score (0-100).

		Args:
			row: DataFrame row with latest data

		Returns:
			Trend score (0-100)
		"""
		score = 50.0  # Neutral baseline

		# ADX contribution (trend strength)
		if "trend_adx14" in row and pd.notna(row["trend_adx14"]):
			adx = row["trend_adx14"]
			# ADX > 25 = strong trend
			if adx > 25:
				score += (adx - 25) * 0.5
			elif adx < 20:
				score -= (20 - adx) * 0.5

		# Price above EMA (uptrend signal)
		if "mom_price_above_ema20" in row and pd.notna(row["mom_price_above_ema20"]):
			if row["mom_price_above_ema20"] > 0:
				score += 15
			else:
				score -= 15

		if "mom_ema_uptrend" in row and pd.notna(row["mom_ema_uptrend"]):
			if row["mom_ema_uptrend"] > 0:
				score += 10
			else:
				score -= 10

		# Clamp to 0-100
		return max(0.0, min(100.0, score))

	def _score_volatility(self, row: pd.Series) -> float:
		"""Calculate volatility score (0-100).

		Args:
			row: DataFrame row with latest data

		Returns:
			Volatility score (0-100)
		"""
		score = 50.0  # Neutral baseline

		# Volatility as % of price
		if "vol_atr_pct" in row and pd.notna(row["vol_atr_pct"]):
			vol_pct = row["vol_atr_pct"] * 100  # Convert to percentage
			# Moderate volatility (1-3%) is good for trading
			if 1.0 <= vol_pct <= 3.0:
				score += 20
			elif vol_pct < 0.5:
				score -= 20  # Too low volatility
			elif vol_pct > 5.0:
				score -= 10  # Very high volatility can be risky

		# Volume expansion
		if "vol_expansion" in row and pd.notna(row["vol_expansion"]):
			vol_exp = row["vol_expansion"]
			# Volume above 20-day MA
			if vol_exp > 1.0:
				score += min(20, (vol_exp - 1) * 10)
			else:
				score -= 10

		# Clamp to 0-100
		return max(0.0, min(100.0, score))

	def _score_mean_reversion(self, row: pd.Series) -> float:
		"""Calculate mean reversion score (0-100).

		Args:
			row: DataFrame row with latest data

		Returns:
			Mean reversion score (0-100)
		"""
		score = 50.0  # Neutral baseline

		# RSI extremes
		if "mr_rsi_oversold" in row and pd.notna(row["mr_rsi_oversold"]):
			if row["mr_rsi_oversold"] > 0:
				score += 25  # Oversold = reversal opportunity

		if "mr_rsi_overbought" in row and pd.notna(row["mr_rsi_overbought"]):
			if row["mr_rsi_overbought"] > 0:
				score -= 25  # Overbought = reversal risk

		# Clamp to 0-100
		return max(0.0, min(100.0, score))
