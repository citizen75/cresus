"""Agent to calculate optimal entry timing."""

from typing import Any, Dict, Optional
import pandas as pd
from core.agent import Agent


class EntryTimingAgent(Agent):
	"""Calculate optimal entry timing for tickers.

	Evaluates price patterns and momentum to determine entry timing quality.
	Timing score indicates how favorable the current moment is for entry.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Calculate entry timing scores for watchlist entries.

		Reads watchlist and data_history from context, evaluates patterns,
		produces timing scores, updates context with scores.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with timing scores
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

		# Calculate timing scores for each ticker
		timing_scores = {}
		scored_count = 0

		for ticker in watchlist:
			if ticker not in data_history:
				self.logger.warning(f"No data for {ticker}, skipping timing score")
				continue

			df = data_history[ticker]
			if len(df) < 5:  # Need at least 5 days for analysis
				continue

			# Calculate timing score based on recent price action
			score = self._calculate_timing_score(df)
			timing_scores[ticker] = score
			scored_count += 1

			self.logger.debug(f"Timing score for {ticker}: {score:.2f}")

		# Store scores in context
		self.context.set("timing_scores", timing_scores)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers_scored": scored_count,
				"total_tickers": len(watchlist),
				"average_timing": sum(timing_scores.values()) / len(timing_scores) if timing_scores else 0,
				"optimal_count": sum(1 for s in timing_scores.values() if s > 70),
			}
		}

	def _calculate_timing_score(self, df: pd.DataFrame) -> float:
		"""Calculate timing score based on price patterns and momentum.

		Evaluates:
		- Pullback from recent high (ideal entry is 5-15% pullback)
		- Momentum strength and direction
		- Support level bounce potential
		- Volume confirmation

		Args:
			df: DataFrame with OHLCV and indicator data

		Returns:
			Timing score (0-100)
		"""
		score = 50  # Base score

		try:
			# Get recent data
			latest = df.iloc[-1]
			prev_data = df.iloc[-5:] if len(df) >= 5 else df

			# Calculate pullback from recent high
			high_5d = prev_data["high"].max() if "high" in df.columns else prev_data.get("close", pd.Series()).max()
			close = float(latest.get("close", 0))

			if close > 0 and high_5d > 0:
				pullback_pct = (1 - close / high_5d) * 100

				# Ideal pullback is 5-15%
				if 5 <= pullback_pct <= 15:
					score += 20  # Perfect pullback zone
				elif 2 <= pullback_pct < 5:
					score += 15  # Minor pullback
				elif 15 < pullback_pct <= 25:
					score += 10  # Deeper pullback, still viable
				elif pullback_pct < 2:
					score -= 5  # Near all-time high, riskier
				elif pullback_pct > 25:
					score += 5  # Deep pullback, could be continuation

			# Momentum analysis - check if price bouncing up
			if len(prev_data) >= 3:
				recent_close = float(df.iloc[-1].get("close", 0))
				prev_close = float(df.iloc[-2].get("close", 0))
				prev_prev_close = float(df.iloc[-3].get("close", 0))

				if recent_close > prev_close > prev_prev_close:  # Uptrend forming
					score += 15
				elif recent_close > prev_close:  # Today up
					score += 10
				elif recent_close < prev_close < prev_prev_close:  # Downtrend, not ideal
					score -= 10

			# Volume confirmation (if available)
			if "volume" in df.columns:
				try:
					latest_vol = float(latest.get("volume", 0))
					avg_vol = prev_data["volume"].mean()

					if latest_vol > avg_vol * 1.2:  # Above average volume
						score += 10
					elif latest_vol > avg_vol * 0.8:  # Normal volume
						score += 5
				except (ValueError, TypeError):
					pass

			# Intraday volatility (if available)
			if "high" in df.columns and "low" in df.columns:
				try:
					high = float(latest.get("high", 0))
					low = float(latest.get("low", 0))
					current_vol = ((high - low) / low * 100) if low > 0 else 0

					if 1 <= current_vol <= 3:  # Moderate volatility
						score += 5
					elif current_vol > 5:  # High volatility, timing is harder
						score -= 5
				except (ValueError, TypeError):
					pass

		except Exception as e:
			self.logger.warning(f"Error calculating timing score: {e}")

		# Clamp score to 0-100 range
		return max(0, min(100, score))
