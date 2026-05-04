"""Agent to calculate entry risk/reward ratios."""

from typing import Any, Dict, Optional
import pandas as pd
from core.agent import Agent


class EntryRRAgent(Agent):
	"""Calculate risk/reward ratios for entries.

	Evaluates support/resistance levels to determine optimal stop-loss and
	take-profit levels, producing risk/reward metrics for each ticker.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Calculate risk/reward ratios for watchlist entries.

		Reads watchlist and data_history from context, identifies support
		and resistance levels, calculates RR ratios, updates context.

		Args:
			input_data: Input data (not used, uses context instead)

		Returns:
			Response with RR metrics
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

		# Calculate RR for each ticker
		rr_metrics = {}
		valid_count = 0
		avg_rr = 0

		for ticker in watchlist:
			if ticker not in data_history:
				self.logger.warning(f"No data for {ticker}, skipping RR calculation")
				continue

			df = data_history[ticker]
			if len(df) < 10:  # Need at least 10 days for meaningful analysis
				continue

			# Calculate RR metrics
			metrics = self._calculate_rr(df)
			if metrics and metrics.get("rr_ratio", 0) > 0:
				rr_metrics[ticker] = metrics
				valid_count += 1
				avg_rr += metrics["rr_ratio"]

				self.logger.debug(
					f"RR for {ticker}: {metrics['rr_ratio']:.2f} "
					f"(SL: {metrics['stop_loss']:.2f}, TP: {metrics['take_profit']:.2f})"
				)

		# Store metrics in context
		self.context.set("rr_metrics", rr_metrics)

		avg_rr = avg_rr / valid_count if valid_count > 0 else 0

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"tickers_evaluated": valid_count,
				"total_tickers": len(watchlist),
				"average_rr": round(avg_rr, 2),
				"good_rr_count": sum(1 for m in rr_metrics.values() if m["rr_ratio"] >= 1.5),
				"excellent_rr_count": sum(1 for m in rr_metrics.values() if m["rr_ratio"] >= 2.0),
			}
		}

	def _calculate_rr(self, df: pd.DataFrame) -> Optional[Dict[str, float]]:
		"""Calculate risk/reward metrics for a ticker.

		Identifies support level (for stop-loss) and resistance level
		(for take-profit) to calculate the RR ratio.

		Args:
			df: DataFrame with OHLCV data

		Returns:
			Dict with RR metrics or None
		"""
		try:
			latest = df.iloc[-1]
			current_price = float(latest.get("close", 0))

			if current_price <= 0:
				return None

			# Identify support (lowest low in recent period)
			lookback = min(20, len(df))
			recent_data = df.iloc[-lookback:]

			low_col = "low" if "low" in df.columns else "close"
			high_col = "high" if "high" in df.columns else "close"

			support = float(recent_data[low_col].min())
			resistance = float(recent_data[high_col].max())

			# If current price is at support/resistance, use ATR for calculation
			if support >= current_price * 0.98:  # Too close to support
				if "atr_14" in df.columns:
					atr = float(latest.get("atr_14", 0))
					support = current_price - (atr * 2)
				else:
					support = current_price * 0.97  # 3% below current

			if resistance <= current_price * 1.02:  # Too close to resistance
				if "atr_14" in df.columns:
					atr = float(latest.get("atr_14", 0))
					resistance = current_price + (atr * 3)
				else:
					resistance = current_price * 1.05  # 5% above current

			# Calculate risk and reward
			risk = current_price - support
			reward = resistance - current_price

			if risk <= 0:
				return None

			rr_ratio = reward / risk

			return {
				"entry_price": round(current_price, 4),
				"support_level": round(support, 4),
				"resistance_level": round(resistance, 4),
				"stop_loss": round(support, 4),
				"take_profit": round(resistance, 4),
				"risk_amount": round(risk, 4),
				"reward_amount": round(reward, 4),
				"rr_ratio": round(rr_ratio, 2),
				"risk_pct": round((risk / current_price) * 100, 2),
				"reward_pct": round((reward / current_price) * 100, 2),
			}

		except Exception as e:
			self.logger.warning(f"Error calculating RR: {e}")
			return None
