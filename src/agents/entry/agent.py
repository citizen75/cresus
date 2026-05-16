"""Entry agent for analyzing trade entry points."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.flow import Flow
from agents.entry.sub_agents import (
	EntryScoreAgent,
	ScoreFilterAgent,
	EntryTimingAgent,
	EntryRRAgent,
	EntryFilterAgent,
	PositionDuplicateFilterAgent,
)


class CompositeRecommendationAgent(Agent):
	"""Create composite recommendations from entry/timing/RR scores."""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Merge scores into watchlist dict as composite recommendations.

		Args:
			input_data: Input data (not used)

		Returns:
			Response with watchlist updated with scores
		"""
		if input_data is None:
			input_data = {}

		# Get scores from context
		entry_scores = self.context.get("entry_scores") or {}
		timing_scores = self.context.get("timing_scores") or {}
		rr_metrics = self.context.get("rr_metrics") or {}
		watchlist = self.context.get("watchlist") or {}

		# Merge scores into watchlist dict (watchlist now contains all recommendation data)
		merged_watchlist = self._merge_scores_into_watchlist(
			watchlist, entry_scores, timing_scores, rr_metrics
		)

		# Update watchlist in context with merged data (entry_recommendations concept is retired)
		self.context.set("watchlist", merged_watchlist)
		self.logger.info(f"[ENTRY] Merged scores into {len(merged_watchlist)} tickers in watchlist")

		return {
			"status": "success",
			"input": input_data,
			"output": {"merged_count": len(merged_watchlist)},
		}

	def _merge_scores_into_watchlist(self, watchlist, entry_scores, timing_scores, rr_metrics):
		"""Merge entry/timing/rr scores into watchlist dict values."""
		merged = {}

		for ticker in list(watchlist.keys()):
			entry_score = entry_scores.get(ticker, 0)
			timing_score = timing_scores.get(ticker, 0)
			rr_data = rr_metrics.get(ticker)

			# Skip tickers with no scores
			if entry_score == 0 and timing_score == 0 and not rr_data:
				continue

			composite_score = self._calculate_composite_score(
				entry_score, timing_score, rr_data
			)

			# Merge all data into watchlist[ticker]
			ticker_data = watchlist[ticker].copy()
			ticker_data.update({
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
			})
			merged[ticker] = ticker_data

		# Sort by composite_score descending and rebuild as dict
		sorted_merged = dict(sorted(
			merged.items(),
			key=lambda x: x[1].get("composite_score", 0),
			reverse=True
		))
		return sorted_merged

	def _calculate_composite_score(self, entry_score, timing_score, rr_data):
		"""Calculate weighted composite score."""
		score = 0
		score += entry_score * 0.4
		score += timing_score * 0.35
		if rr_data and rr_data.get("rr_ratio", 0) > 0:
			rr = rr_data["rr_ratio"]
			rr_score = min(100, 50 + (rr - 1) * 25)
			score += rr_score * 0.25
		else:
			score += 50 * 0.25
		return min(100, max(0, score))

	def _get_recommendation_level(self, score):
		"""Get recommendation level based on score."""
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
			# Fall back to all signal-scored tickers if watchlist is empty
			ticker_scores = self.context.get("ticker_scores") or {}
			if ticker_scores:
				# Use ALL signal-scored tickers, not just top 20
				# This ensures entry_filter can evaluate reversal patterns which may have lower signal scores
				watchlist = {t: {} for t in ticker_scores.keys()}
				ticker_list = list(watchlist.keys())
				self.logger.info(f"[ENTRY] Watchlist empty, using {len(watchlist)} signal-scored tickers: {ticker_list[:5]}{'...' if len(watchlist) > 5 else ''}")
			else:
				return {
					"status": "error",
					"input": input_data,
					"output": {},
					"message": "No watchlist or signal-scored tickers in context"
				}
		else:
			ticker_list = list(watchlist.keys())
			self.logger.info(f"[ENTRY] Starting entry analysis with {len(watchlist)} tickers: {ticker_list[:10]}{'...' if len(watchlist) > 10 else ''}")

		# Set watchlist in context for sub-agents
		self.context.set("watchlist", watchlist)

		#print(f"[ENTRY-0] {self.context.get('current_date')}")
		#print(f"[ENTRY-0] Watchlist: {len(watchlist)} tickers")

		# Create unified entry flow with all steps: scoring → recommendations → filtering
		entry_flow = Flow("EntryAnalysisFlow", context=self.context)

		# Step 1: Entry scoring
		entry_flow.add_step(
			EntryScoreAgent("EntryScoreStep"),
			required=True
		)

		# Step 2: Filter by minimum entry score threshold
		entry_flow.add_step(
			ScoreFilterAgent("ScoreFilterStep"),
			required=False
		)

		# Step 3: Entry timing analysis
		entry_flow.add_step(
			EntryTimingAgent("EntryTimingStep"),
			required=False
		)

		# Step 4: Risk/reward analysis
		entry_flow.add_step(
			EntryRRAgent("EntryRRStep"),
			required=False
		)

		# Step 5: Create composite recommendations from scores
		entry_flow.add_step(
			CompositeRecommendationAgent("CompositeRecommendationStep"),
			required=True
		)

		# Step 6: Filter duplicate positions
		entry_flow.add_step(
			PositionDuplicateFilterAgent("PositionDuplicateFilterStep"),
			required=False
		)

		# Step 7: Apply entry filter formula
		entry_flow.add_step(
			EntryFilterAgent("EntryFilterStep"),
			required=False
		)

		# Execute the complete entry analysis flow
		self.logger.debug("[ENTRY] Executing entry analysis flow...")
		flow_result = entry_flow.process(input_data)

		# Check flow execution
		if flow_result.get("status") != "success":
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Entry analysis flow failed: {flow_result.get('message', 'Unknown error')}"
			}

		watchlist = self.context.get("watchlist") or {}
		# Extract scores from merged watchlist dict (now single source of truth)
		entry_scores = {t: d.get("entry_score", 0) for t, d in watchlist.items()}
		timing_scores = {t: d.get("timing_score", 0) for t, d in watchlist.items()}
		rr_metrics = {t: {"rr_ratio": d.get("rr_ratio", 0)} for t, d in watchlist.items()}
		recommendations = list(watchlist.keys())  # All tickers in merged watchlist are recommendations

		# Log final summary
		avg_entry = sum(entry_scores.values()) / len(entry_scores) if entry_scores else 0
		avg_timing = sum(timing_scores.values()) / len(timing_scores) if timing_scores else 0
		avg_rr = sum(m["rr_ratio"] for m in rr_metrics.values()) / len(rr_metrics) if rr_metrics else 0

		#print(f"[ENTRY-1] Watchlist: {len(watchlist)} tickers")

		self.logger.info(f"[ENTRY] ========== ENTRY ANALYSIS SUMMARY ==========")
		self.logger.info(f"[ENTRY] Watchlist: {len(watchlist)} tickers")
		self.logger.info(f"[ENTRY] Entry scores: {len(entry_scores)}/{len(watchlist)} ({100*len(entry_scores)//len(watchlist) if watchlist else 0}%) - avg: {avg_entry:.1f}")
		self.logger.info(f"[ENTRY] Timing analysis: {len(timing_scores)}/{len(watchlist)} ({100*len(timing_scores)//len(watchlist) if watchlist else 0}%) - avg: {avg_timing:.1f}")
		self.logger.info(f"[ENTRY] Risk/Reward: {len(rr_metrics)}/{len(watchlist)} ({100*len(rr_metrics)//len(watchlist) if watchlist else 0}%) - avg RR: {avg_rr:.2f}")
		self.logger.info(f"[ENTRY] Final recommendations: {len(recommendations)}/{len(watchlist)} ({100*len(recommendations)//len(watchlist) if watchlist else 0}%)")
		if recommendations:
			top_3 = [t for t in recommendations[:3]]
			self.logger.info(f"[ENTRY] Top 3 opportunities: {', '.join(top_3)}")
		self.logger.info(f"[ENTRY] ==========================================")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"total_analyzed": len(watchlist),
				"scored": len(entry_scores),
				"with_timing": len(timing_scores),
				"with_rr": len(rr_metrics),
				"recommendations": len(recommendations),
				"top_opportunities": self._get_top_opportunities(watchlist, 5),
				"statistics": {
					"avg_entry_score": avg_entry,
					"avg_timing_score": avg_timing,
					"avg_rr": avg_rr,
				}
			},
			"execution_history": flow_result.get("execution_history", []),
		}

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

	def _get_top_opportunities(self, watchlist: dict, count: int = 5) -> list:
		"""Get top N opportunities from watchlist (already sorted by composite_score).

		Args:
			watchlist: Watchlist dict with merged scores (already sorted descending by composite_score)
			count: Number of top opportunities to return

		Returns:
			List of top N recommendations with scores
		"""
		return [
			{
				"rank": i + 1,
				"ticker": ticker,
				"score": data.get("composite_score", 0),
				"recommendation": data.get("recommendation", "HOLD"),
				"rr_ratio": data.get("rr_ratio"),
			}
			for i, (ticker, data) in enumerate(list(watchlist.items())[:count])
		]

