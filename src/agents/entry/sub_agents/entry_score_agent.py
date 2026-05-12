"""Agent to calculate entry signal strength score."""

from typing import Any, Dict, Optional
import pandas as pd
from core.agent import Agent


class EntryScoreAgent(Agent):
	"""Calculate entry signal strength for tickers.

	Evaluates technical signals and indicators to produce entry scores.
	Higher scores indicate stronger entry signals.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Calculate entry scores for watchlist entries.

		Reads watchlist and data_history from context, evaluates technical
		indicators to produce entry scores, updates context with scores.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with entry scores
		"""
		if input_data is None:
			input_data = {}

		# Get watchlist and data history from context
		watchlist = self.context.get("watchlist")
		data_history = self.context.get("data_history") or {}

		if not watchlist:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No watchlist in context"
			}

		self.logger.debug(f"[ENTRY-SCORE] Starting entry score calculation for {len(watchlist)} tickers")

		# Calculate entry scores for each ticker
		entry_scores = {}
		scored_count = 0
		skipped_tickers = []

		for ticker in watchlist:
			if ticker not in data_history:
				skipped_tickers.append(f"{ticker}(no-data)")
				continue

			df = data_history[ticker]
			if df.empty:
				skipped_tickers.append(f"{ticker}(empty)")
				continue

			# Validate that data has at least a close column
			if 'close' not in df.columns and 'Close' not in df.columns:
				skipped_tickers.append(f"{ticker}(no-close)")
				continue

			# Get the latest row for analysis
			latest = df.iloc[-1]

			# Calculate composite entry score (0-100)
			score = self._calculate_entry_score(latest)
			entry_scores[ticker] = score
			scored_count += 1

			self.logger.debug(f"[ENTRY-SCORE] {ticker}: {score:.1f}")

		# Store scores in context
		self.context.set("entry_scores", entry_scores)

		# Log summary
		avg_score = sum(entry_scores.values()) / len(entry_scores) if entry_scores else 0
		self.logger.info(f"[ENTRY-SCORE] Scored {scored_count}/{len(watchlist)} tickers (skipped: {len(skipped_tickers)})")
		self.logger.debug(f"[ENTRY-SCORE] Skipped: {skipped_tickers}")
		self.logger.debug(f"[ENTRY-SCORE] Scores - avg: {avg_score:.1f}, min: {min(entry_scores.values()):.1f}, max: {max(entry_scores.values()):.1f}")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers_scored": scored_count,
				"total_tickers": len(watchlist),
				"average_score": avg_score,
				"max_score": max(entry_scores.values()) if entry_scores else 0,
				"min_score": min(entry_scores.values()) if entry_scores else 0,
			}
		}

	def _calculate_entry_score(self, row: pd.Series) -> float:
		"""Calculate entry score for a single ticker.

		Evaluates multiple technical indicators:
		- RSI: Oversold (< 30) or from oversold (30-50) gets higher score
		- EMA crossover: Price above EMA20 above EMA50 gets higher score
		- ADX: Strong trend (> 25) gets higher score
		- MACD: Positive and increasing gets higher score

		Args:
			row: DataFrame row with OHLCV and indicator data

		Returns:
			Entry score (0-100)
		"""
		score = 50  # Base score

		# RSI Analysis (0-20 points)
		if "rsi_14" in row.index:
			rsi = float(row["rsi_14"])
			if rsi < 30:  # Oversold, strong buy signal
				score += 20
			elif rsi < 40:  # Approaching oversold
				score += 15
			elif rsi > 70:  # Overbought, reduce score
				score -= 15
			elif rsi > 60:  # Getting overbought
				score -= 5

		# EMA Crossover Analysis (0-20 points)
		if "ema_20" in row.index and "ema_50" in row.index:
			try:
				close = float(row.get("close", 0))
				ema_20 = float(row["ema_20"])
				ema_50 = float(row["ema_50"])

				if ema_20 > ema_50:  # Bullish trend
					score += 10
					if close > ema_20:  # Price above short-term EMA
						score += 10
				elif close > ema_50:  # Price above long-term EMA
					score += 5
			except (ValueError, TypeError):
				pass

		# ADX Trend Strength (0-15 points)
		if "adx_20" in row.index:
			try:
				adx = float(row["adx_20"])
				if adx > 25:  # Strong trend
					score += 15
				elif adx > 20:  # Moderate trend
					score += 10
				elif adx < 20:  # Weak trend
					score -= 5
			except (ValueError, TypeError):
				pass

		# MACD Momentum (0-15 points)
		if "macd_12_26" in row.index:
			try:
				macd = float(row["macd_12_26"])
				if macd > 0:  # Positive momentum
					score += 8
					if macd > 0.5:  # Strong positive
						score += 7
				else:  # Negative momentum
					score -= 8
			except (ValueError, TypeError):
				pass

		# Clamp score to 0-100 range
		return max(0, min(100, score))
