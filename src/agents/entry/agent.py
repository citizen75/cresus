"""Entry agent for analyzing trade entry points."""

from typing import Any, Dict, Optional
from core.agent import Agent
from agents.entry.sub_agents import (
    EntryScoreAgent,
    ScoreFilterAgent,
    EntryTimingAgent,
    EntryRRAgent,
    EntryFilterAgent,
    PositionDuplicateFilterAgent,
)


class EntryAgent(Agent):
    """Orchestrate multi-step entry analysis for watchlist tickers.

    Pipeline (steps 2-4 are non-fatal and continue gracefully on failure):
      1. EntryScoreAgent               — signal strength (fatal: aborts on failure)
      2. ScoreFilterAgent              — drop tickers below min score threshold
      3. EntryTimingAgent              — pullback / momentum timing
      4. EntryRRAgent                  — stop-loss / take-profit / RR ratio
      5. _merge_scores_into_entries    — composite score + recommendation (inline)
      6. PositionDuplicateFilterAgent  — drop tickers with open positions
      7. EntryFilterAgent              — entry_filter formula gate
    """

    def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if input_data is None:
            input_data = {}

        watchlist = self.context.get("watchlist")
        if not watchlist:
            self.logger.info("[ENTRY] Watchlist is empty, no entry analysis")
            # Clear any "entries" left over from a previous call (e.g. yesterday's
            # watchlist). Without this, OrdersEntryAgent - which runs unconditionally
            # every day right after this agent - would re-read yesterday's already
            # filtered-and-bought entries and place a fresh duplicate order for them,
            # never having gone through PositionDuplicateFilterAgent today.
            self.context.set("entries", {})
            return {
                "status": "success",
                "input": input_data,
                "output": {"entry_count": 0},
                "message": "No tickers in watchlist",
            }

        # entries is the working dataset for this pipeline — watchlist stays untouched
        self.context.set("entries", dict(watchlist))
        tickers = list(watchlist.keys())
        self.logger.info(
            f"[ENTRY] Starting entry analysis with {len(watchlist)} tickers: "
            f"{tickers[:10]}{'...' if len(watchlist) > 10 else ''}"
        )

        try:
            self._run_sub_agent(EntryScoreAgent("EntryScoreStep"), fatal=True)
            self._run_sub_agent(ScoreFilterAgent("ScoreFilterStep"), fatal=False)
            self._run_sub_agent(EntryTimingAgent("EntryTimingStep"), fatal=False)
            self._run_sub_agent(EntryRRAgent("EntryRRStep"), fatal=False)
            self._merge_scores_into_entries()
            self._run_sub_agent(PositionDuplicateFilterAgent("PositionDuplicateFilterStep"), fatal=False)
            self._run_sub_agent(EntryFilterAgent("EntryFilterStep"), fatal=False)
        except RuntimeError as e:
            # A fatal step (EntryScoreAgent) failed before PositionDuplicateFilterAgent
            # got to run. "entries" was already set to the raw, unfiltered watchlist at
            # the top of this method - leaving it in place would let OrdersEntryAgent
            # place orders for tickers that already have an open position, since the
            # one step that checks for that never executed.
            self.context.set("entries", {})
            return {
                "status": "error",
                "input": input_data,
                "output": {},
                "message": str(e),
            }

        entries = self.context.get("entries") or {}
        self._log_summary(entries)

        return {
            "status": "success",
            "input": input_data,
            "output": {
                "total_analyzed": len(entries),
                "top_opportunities": self._get_top_opportunities(entries, 5),
            },
        }

    # ------------------------------------------------------------------
    # Pipeline step: merge context scores into entries dict
    # ------------------------------------------------------------------

    def _merge_scores_into_entries(self) -> None:
        """Merge entry/timing/rr scores into entries and sort by ranking then composite score."""
        entries = self.context.get("entries") or {}
        entry_scores = self.context.get("entry_scores") or {}
        timing_scores = self.context.get("timing_scores") or {}
        rr_metrics = self.context.get("rr_metrics") or {}

        merged = {}
        for ticker, ticker_data in entries.items():
            entry_score = entry_scores.get(ticker, 0)
            timing_score = timing_scores.get(ticker, 0)
            rr_data = rr_metrics.get(ticker)

            if entry_score == 0 and timing_score == 0 and not rr_data:
                continue

            composite_score = self._calculate_composite_score(entry_score, timing_score, rr_data)
            data = ticker_data.copy() if isinstance(ticker_data, dict) else {}
            data.update({
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
            merged[ticker] = data

        # ranking_score (LGBM) is primary sort key; composite_score is tiebreaker
        sorted_merged = dict(sorted(
            merged.items(),
            key=lambda x: (x[1].get("ranking_score", 0), x[1].get("composite_score", 0)),
            reverse=True,
        ))
        self.context.set("entries", sorted_merged)
        self.logger.info(f"[ENTRY] Merged scores into {len(sorted_merged)} tickers")

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _calculate_composite_score(
        self,
        entry_score: float,
        timing_score: float,
        rr_data: Optional[Dict[str, float]],
    ) -> float:
        """Weighted composite: entry 40%, timing 35%, RR 25%.

        RR conversion: ratio 1.0 → score 50, 2.0 → 75, 3.0 → 100.
        Neutral 50 is used when no RR data is available.
        """
        score = entry_score * 0.4 + timing_score * 0.35
        if rr_data and rr_data.get("rr_ratio", 0) > 0:
            score += min(100, 50 + (rr_data["rr_ratio"] - 1) * 25) * 0.25
        else:
            score += 50 * 0.25
        return min(100, max(0, score))

    def _get_recommendation_level(self, score: float) -> str:
        if score >= 80:
            return "STRONG BUY"
        if score >= 65:
            return "BUY"
        if score >= 50:
            return "HOLD"
        if score >= 35:
            return "WAIT"
        return "SKIP"

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def _get_top_opportunities(self, entries: dict, count: int = 5) -> list:
        return [
            {
                "rank": i + 1,
                "ticker": ticker,
                "score": data.get("composite_score", 0),
                "recommendation": data.get("recommendation", "HOLD"),
                "rr_ratio": data.get("rr_ratio"),
            }
            for i, (ticker, data) in enumerate(list(entries.items())[:count])
        ]

    def _log_summary(self, entries: dict) -> None:
        n = len(entries)
        if not n:
            return
        self.logger.info("[ENTRY] ========== ENTRY ANALYSIS SUMMARY ==========")
        self.logger.info(f"[ENTRY] Final recommendations: {n} tickers")
        top3 = list(entries.keys())[:3]
        if top3:
            self.logger.info(f"[ENTRY] Top 3 opportunities: {', '.join(top3)}")
        self.logger.info("[ENTRY] ==========================================")
