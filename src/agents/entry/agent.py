"""Entry agent for analyzing trade entry points."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.flow import Flow
from agents.entry.sub_agents import EntryScoreAgent, EntryTimingAgent, EntryRRAgent
from agents.entry_order.sub_agents import PositionDuplicateFilterAgent


class EntryAgent(Agent):
	"""Agent for analyzing trade entry points.

	Orchestrates a multi-step analysis flow using sub-agents to evaluate
	entry points for watchlist tickers based on:
	- Entry signal strength (entry_score)
	- Optimal timing (entry_timing)
	- Risk/reward ratios (entry_rr)
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Analyze entry points for watchlist entries.

		Executes analysis flow with sub-agents that calculate:
		1. Entry scores - signal strength evaluation
		2. Entry timing - pattern and momentum analysis
		3. Entry RR - risk/reward ratio calculation

		Falls back to signal-scored tickers if watchlist is empty.

		Args:
			input_data: Input data (not used, uses context)

		Returns:
			Response dictionary with analysis results
		"""
		if input_data is None:
			input_data = {}

		# Get watchlist from context, fall back to signal-scored tickers if empty
		watchlist = self.context.get("watchlist")
		if not watchlist:
			# Fall back to top signal-scored tickers if watchlist is empty
			ticker_scores = self.context.get("ticker_scores") or {}
			if ticker_scores:
				# Sort by score and take top 20
				sorted_by_score = sorted(
					ticker_scores.items(),
					key=lambda x: x[1].get("score", 0),
					reverse=True
				)
				watchlist = [ticker for ticker, _ in sorted_by_score[:20]]
				self.logger.debug(f"Watchlist empty, using {len(watchlist)} top signal-scored tickers for entry analysis")
			else:
				return {
					"status": "error",
					"input": input_data,
					"output": {},
					"message": "No watchlist or signal-scored tickers in context"
				}

		# Set watchlist in context for sub-agents
		self.context.set("watchlist", watchlist)

		# Create analysis flow with sub-agents
		entry_flow = Flow("EntryAnalysisFlow", context=self.context)

		# Add position duplicate filter as first step
		entry_flow.add_step(
			PositionDuplicateFilterAgent("PositionDuplicateFilterStep"),
			required=False
		)

		# Add sub-agents in sequence
		entry_flow.add_step(
			EntryScoreAgent("EntryScoreStep"),
			required=True
		)

		entry_flow.add_step(
			EntryTimingAgent("EntryTimingStep"),
			required=False
		)

		entry_flow.add_step(
			EntryRRAgent("EntryRRStep"),
			required=False
		)

		# Execute the flow
		flow_result = entry_flow.process(input_data)

		# Check flow execution
		if flow_result.get("status") != "success":
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Entry analysis flow failed: {flow_result.get('message', 'Unknown error')}"
			}

		# Compile results from sub-agents
		entry_scores = self.context.get("entry_scores") or {}
		timing_scores = self.context.get("timing_scores") or {}
		rr_metrics = self.context.get("rr_metrics") or {}

		# Create composite entry recommendations
		recommendations = self._create_recommendations(
			watchlist, entry_scores, timing_scores, rr_metrics
		)

		# Store in context for downstream processing
		self.context.set("entry_recommendations", recommendations)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"total_analyzed": len(watchlist),
				"scored": len(entry_scores),
				"with_timing": len(timing_scores),
				"with_rr": len(rr_metrics),
				"recommendations": len(recommendations),
				"top_opportunities": self._get_top_opportunities(recommendations, 5),
				"statistics": {
					"avg_entry_score": sum(entry_scores.values()) / len(entry_scores) if entry_scores else 0,
					"avg_timing_score": sum(timing_scores.values()) / len(timing_scores) if timing_scores else 0,
					"avg_rr": sum(m["rr_ratio"] for m in rr_metrics.values()) / len(rr_metrics) if rr_metrics else 0,
				}
			},
			"execution_history": flow_result.get("execution_history", []),
		}

	def _create_recommendations(
		self,
		watchlist: list,
		entry_scores: Dict[str, float],
		timing_scores: Dict[str, float],
		rr_metrics: Dict[str, Dict[str, float]]
	) -> list:
		"""Create composite entry recommendations.

		Combines all analysis into actionable recommendations sorted by
		overall attractiveness.

		Args:
			watchlist: List of tickers
			entry_scores: Dict of ticker -> entry score
			timing_scores: Dict of ticker -> timing score
			rr_metrics: Dict of ticker -> RR metrics

		Returns:
			Sorted list of recommendations
		"""
		recommendations = []

		for ticker in watchlist:
			# Gather available metrics for this ticker
			entry_score = entry_scores.get(ticker, 0)
			timing_score = timing_scores.get(ticker, 0)
			rr_data = rr_metrics.get(ticker)

			# Skip if no scores available
			if entry_score == 0 and timing_score == 0 and not rr_data:
				continue

			# Calculate composite score
			composite_score = self._calculate_composite_score(
				entry_score, timing_score, rr_data
			)

			recommendation = {
				"ticker": ticker,
				"composite_score": round(composite_score, 2),
				"entry_score": round(entry_score, 2),
				"timing_score": round(timing_score, 2),
				"rr_ratio": rr_data["rr_ratio"] if rr_data else None,
				"entry_price": rr_data["entry_price"] if rr_data else None,
				"stop_loss": rr_data["stop_loss"] if rr_data else None,
				"take_profit": rr_data["take_profit"] if rr_data else None,
				"risk_pct": rr_data["risk_pct"] if rr_data else None,
				"reward_pct": rr_data["reward_pct"] if rr_data else None,
				"recommendation": self._get_recommendation_level(composite_score),
			}

			recommendations.append(recommendation)

		# Sort by composite score descending
		recommendations.sort(key=lambda x: x["composite_score"], reverse=True)

		return recommendations

	def _calculate_composite_score(
		self,
		entry_score: float,
		timing_score: float,
		rr_data: Optional[Dict[str, float]]
	) -> float:
		"""Calculate weighted composite score.

		Weights:
		- Entry score: 40%
		- Timing score: 35%
		- RR ratio: 25%

		Args:
			entry_score: Entry signal strength (0-100)
			timing_score: Timing quality (0-100)
			rr_data: RR metrics dict

		Returns:
			Composite score (0-100)
		"""
		score = 0

		# Entry score weight: 40%
		score += entry_score * 0.4

		# Timing score weight: 35%
		score += timing_score * 0.35

		# RR score weight: 25% (based on ratio quality)
		if rr_data and rr_data.get("rr_ratio", 0) > 0:
			rr = rr_data["rr_ratio"]
			# Convert RR ratio to 0-100 score
			# RR 1.0 = 50, RR 2.0 = 75, RR 3.0 = 90
			rr_score = min(100, 50 + (rr - 1) * 25)
			score += rr_score * 0.25
		else:
			# If no RR data, default to 50 (neutral) for the RR component
			score += 50 * 0.25

		return min(100, max(0, score))

	def _get_recommendation_level(self, score: float) -> str:
		"""Get recommendation level based on composite score.

		Args:
			score: Composite score (0-100)

		Returns:
			Recommendation level string
		"""
		if score >= 80:
			return "STRONG BUY"
		elif score >= 65:
			return "BUY"
		elif score >= 50:
			return "HOLD"
		elif score >= 35:
			return "WAIT"
		else:
			return "SKIP"

	def _get_top_opportunities(self, recommendations: list, count: int = 5) -> list:
		"""Get top N opportunities from recommendations.

		Args:
			recommendations: Sorted recommendations
			count: Number of top opportunities to return

		Returns:
			List of top N recommendations
		"""
		return [
			{
				"rank": i + 1,
				"ticker": r["ticker"],
				"score": r["composite_score"],
				"recommendation": r["recommendation"],
				"rr_ratio": r["rr_ratio"],
			}
			for i, r in enumerate(recommendations[:count])
		]
