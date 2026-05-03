"""Signals agent for generating trading signals from indicators."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.flow import Flow
from agents.signals.sub_agents import MomentumAgent, TrendSignalAgent, MeanReversionAgent, VolumeAnomalyAgent


class SignalsAgent(Agent):
	"""Agent for generating trading signals from indicators.

	Orchestrates multiple signal generators (momentum, trend, mean reversion, volume)
	to provide comprehensive market signals.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process signals through multiple generators.

		Creates a Flow with signal sub-agents that analyze different aspects:
		1. Momentum - overbought/oversold conditions
		2. Trend - directional trends
		3. Mean Reversion - mean reversion opportunities
		4. Volume - volume anomalies

		Args:
			input_data: Input data (optional)

		Returns:
			Response dictionary with signal analysis results
		"""
		if input_data is None:
			input_data = {}

		# Create signals generation flow
		signals_flow = Flow("SignalsFlow", context=self.context)

		# Add signal generator steps
		signals_flow.add_step(
			MomentumAgent("MomentumSignal"),
			step_name="momentum",
			required=False
		)

		signals_flow.add_step(
			TrendSignalAgent("TrendSignal"),
			step_name="trend",
			required=False
		)

		signals_flow.add_step(
			MeanReversionAgent("MeanReversionSignal"),
			step_name="mean_reversion",
			required=False
		)

		signals_flow.add_step(
			VolumeAnomalyAgent("VolumeAnomalySignal"),
			step_name="volume_anomaly",
			required=False
		)

		# Execute the flow
		flow_result = signals_flow.process(input_data)

		# Get signal weights from strategy config
		strategy_config = self.context.get("strategy_config") or {}
		signals_config = strategy_config.get("signals") or {}
		weights = signals_config.get("weights") or {}
		total_weight = sum(weights.values()) if weights else 1.0

		# Build signal results map: signal_name -> list of tickers
		signal_results = {}
		if "execution_history" in flow_result:
			for step_history in flow_result["execution_history"]:
				step_name = step_history.get("step", "unknown")
				step_output = step_history.get("output", {})
				signal_results[step_name] = {
					"tickers": step_output.get("tickers", []),
					"strength": step_output.get("strength", 0),
				}

		# Get tickers from watchlist (if available) or fall back to all tickers
		all_tickers = self.context.get("watchlist") or self.context.get("tickers") or []
		self.logger.info(f"Analyzing signals for {len(all_tickers)} ticker(s)")
		ticker_scores = {}
		for ticker in all_tickers:
			score = 0.0
			triggered_signals = []
			for signal_name, signal_info in signal_results.items():
				signal_weight = weights.get(signal_name, 0)
				if ticker in signal_info.get("tickers", []):
					score += signal_weight
					triggered_signals.append(signal_name)

			ticker_scores[ticker] = {
				"score": score / total_weight if total_weight > 0 else 0,
				"raw_score": score,
				"triggered_signals": triggered_signals,
				"signal_count": len(triggered_signals),
			}

		# Store signals and scores in context
		self.context.set("signals", signal_results)
		self.context.set("ticker_scores", ticker_scores)

		# Sort tickers by score (descending)
		sorted_tickers = sorted(ticker_scores.items(), key=lambda x: x[1]["score"], reverse=True)

		# Log top tickers
		self.logger.info(f"Top 5 tickers by signal score:")
		for i, (ticker, score_info) in enumerate(sorted_tickers[:5], 1):
			self.logger.info(f"  {i}. {ticker}: {score_info['score']:.3f} ({score_info['signal_count']} signals)")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"signals": signal_results,
				"ticker_scores": ticker_scores,
				"sorted_tickers": [{"ticker": t, **s} for t, s in sorted_tickers],
				"top_ticker": sorted_tickers[0][0] if sorted_tickers else None,
				"top_score": sorted_tickers[0][1]["score"] if sorted_tickers else 0,
			},
			"execution_history": flow_result.get("execution_history", []),
		}
