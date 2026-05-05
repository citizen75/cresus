"""Agent to calculate entry risk/reward ratios."""

from typing import Any, Dict, Optional
import pandas as pd
from core.agent import Agent
from tools.strategy.strategy import StrategyManager
from tools.strategy.config_evaluator import ConfigEvaluator


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

		Uses strategy configuration formulas if available, otherwise
		falls back to support/resistance level detection.

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

			# Try to load strategy config for exit formulas
			strategy_name = self.context.get("strategy_name") if self.context else None
			exit_config = {}
			
			if strategy_name:
				try:
					strategy_manager = StrategyManager()
					strategy_result = strategy_manager.load_strategy(strategy_name)
					if strategy_result.get("status") == "success":
						strategy_data = strategy_result.get("data", {})
						exit_config = strategy_data.get("exit", {}).get("parameters", {})
				except Exception as e:
					self.logger.debug(f"Could not load strategy config: {e}")

			# Prepare data context for formula evaluation
			data_context = {
				"close": current_price,
				"atr_14": float(latest.get("atr_14", 0)),
				"high": float(latest.get("high", 0)),
				"low": float(latest.get("low", 0)),
			}

			# Try to evaluate stop_loss formula from config
			stop_loss = None
			if "stop_loss" in exit_config:
				sl_formula = exit_config["stop_loss"].get("formula")
				if sl_formula:
					stop_loss = ConfigEvaluator.evaluate_formula(sl_formula, data_context)

			# Try to evaluate take_profit formula from config
			take_profit = None
			if "take_profit" in exit_config:
				tp_formula = exit_config["take_profit"].get("formula")
				if tp_formula:
					take_profit = ConfigEvaluator.evaluate_formula(tp_formula, data_context)

			# If config formulas didn't work, use fallback support/resistance method
			if stop_loss is None or take_profit is None:
				# Identify support (lowest low in recent period) and resistance (highest high)
				lookback = min(20, len(df))
				recent_data = df.iloc[-lookback:]

				low_col = "low" if "low" in df.columns else "close"
				high_col = "high" if "high" in df.columns else "close"

				recent_low = float(recent_data[low_col].min())
				recent_high = float(recent_data[high_col].max())

				# Ensure support < current_price < resistance
				support = min(recent_low, recent_high)
				resistance = max(recent_low, recent_high)

				# If support >= current_price, use ATR-based fallback
				if support >= current_price:
					atr = data_context.get("atr_14", 0)
					support = current_price - (atr * 2)
					resistance = current_price + (atr * 3)
				elif resistance <= current_price:
					atr = data_context.get("atr_14", 0)
					resistance = current_price + (atr * 3)

				# Safety checks
				if support >= current_price:
					support = current_price * 0.97
				if resistance <= current_price:
					resistance = current_price * 1.05

				# Use fallback values if config formulas didn't evaluate
				if stop_loss is None:
					stop_loss = support
				if take_profit is None:
					take_profit = resistance

			# Calculate risk and reward
			risk = current_price - stop_loss
			reward = take_profit - current_price

			if risk <= 0 or reward <= 0:
				return None

			rr_ratio = reward / risk

			return {
				"entry_price": round(current_price, 4),
				"support_level": round(stop_loss, 4),
				"resistance_level": round(take_profit, 4),
				"stop_loss": round(stop_loss, 4),
				"take_profit": round(take_profit, 4),
				"risk_amount": round(risk, 4),
				"reward_amount": round(reward, 4),
				"rr_ratio": round(rr_ratio, 2),
				"risk_pct": round((risk / current_price) * 100, 2),
				"reward_pct": round((reward / current_price) * 100, 2),
			}

		except Exception as e:
			self.logger.warning(f"Error calculating RR: {e}")
			return None
