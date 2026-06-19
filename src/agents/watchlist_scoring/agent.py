"""Watchlist scoring agent — computes a scalar score per ticker from a formula."""

import re
from typing import Any, Dict, Optional

import pandas as pd
from core.agent import Agent


class WatchlistScoringAgent(Agent):
    """Evaluate strategy.watchlist.parameters.scoring.formula for each watchlist ticker.

    Reads the scoring formula from strategy config, evaluates it against the
    full data_history DataFrame for each ticker (so DSL shift notation like
    chgpct_20[0] works), and writes the resulting scalar as:
      - watchlist[ticker]["score"]
      - ticker_scores[ticker]["score"]

    Formula examples:
        chgpct_20[0]                                          # DSL shift notation
        mom_roc5 * 0.4 + trend_adx14 * 0.3 + vol_bb_percent * 0.3  # weighted alpha
        (rsi_14 - 50) / 50
    """

    def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if input_data is None:
            input_data = {}

        strategy_config = self.context.get("strategy_config") or {}
        formula = (
            strategy_config
            .get("watchlist", {})
            .get("parameters", {})
            .get("scoring", {})
            .get("formula")
        )

        if not formula:
            self.logger.info("[SCORING] No scoring formula configured, skipping")
            return {
                "status": "success",
                "input": input_data,
                "output": {"scored": 0},
                "message": "No scoring formula in watchlist.parameters.scoring.formula",
            }

        watchlist = self.context.get("watchlist") or {}
        data_history = self.context.get("data_history") or {}
        ticker_scores = self.context.get("ticker_scores") or {}

        tickers = list(watchlist.keys()) if isinstance(watchlist, dict) else list(watchlist)
        if not tickers:
            return {
                "status": "success",
                "input": input_data,
                "output": {"scored": 0},
                "message": "Watchlist is empty",
            }

        # Validate the formula once before the main loop so a typo/unknown
        # indicator produces one clear error rather than N identical warnings.
        probe_df = next(
            (data_history[t] for t in tickers
             if isinstance(data_history.get(t), pd.DataFrame) and not data_history[t].empty),
            None,
        )
        if probe_df is not None:
            try:
                self._evaluate_formula(formula, probe_df.copy(), tickers[0])
            except Exception as e:
                msg = f"[SCORING] Invalid formula '{formula}': {e}"
                self.logger.error(msg)
                return {
                    "status": "error",
                    "input": input_data,
                    "output": {"scored": 0, "errors": len(tickers)},
                    "message": msg,
                }

        scored = 0
        errors = []

        for ticker in tickers:
            df = data_history.get(ticker)
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue

            # Reset score to 0.0 so a prior value (e.g. WatchlistRankingAgent's
            # rank) is never silently left as the score on formula failure.
            if ticker not in ticker_scores:
                ticker_scores[ticker] = {}
            ticker_scores[ticker]["score"] = 0.0
            if isinstance(watchlist, dict):
                if not isinstance(watchlist.get(ticker), dict):
                    watchlist[ticker] = {}
                watchlist[ticker]["score"] = 0.0

            try:
                score = float(self._evaluate_formula(formula, df, ticker))
                ticker_scores[ticker]["score"] = score
                watchlist[ticker]["score"] = score
                scored += 1
            except Exception as e:
                errors.append(ticker)
                self.logger.debug(f"[SCORING] {ticker}: score=0 ({e})")

        self.context.set("watchlist", watchlist)
        self.context.set("ticker_scores", ticker_scores)

        if errors:
            self.logger.warning(f"[SCORING] {len(errors)} tickers could not be scored: {errors}")
        self.logger.info(f"[SCORING] Scored {scored}/{len(tickers)} tickers with formula: {formula}")

        return {
            "status": "success",
            "input": input_data,
            "output": {"scored": scored, "errors": len(errors)},
            "message": f"Scored {scored} tickers",
        }

    def _evaluate_formula(self, formula: str, df: pd.DataFrame, ticker: str = "") -> float:
        """Evaluate scoring formula against a ticker's full DataFrame.

        Uses evaluate_dsl_vectorized (which normalises sort order internally) so
        DSL shift notation and missing-indicator recovery both work correctly.

        Args:
            formula: DSL or arithmetic expression referencing column / alpha names
            df: Full data_history DataFrame for the ticker (any sort order)
            ticker: Ticker symbol for error context

        Returns:
            Scalar float score for the latest bar
        """
        from src.tools.formula.dsl_parser import evaluate_dsl_vectorized
        from src.tools.indicators import calculate

        def _latest(series: pd.Series) -> float:
            valid = series.dropna()
            return float(valid.iloc[-1]) if not valid.empty else 0.0

        # First attempt
        try:
            return _latest(evaluate_dsl_vectorized(formula, df))
        except Exception:
            pass

        # Recovery: calculate any missing indicators referenced in the formula
        _SKIP = {"and", "or", "not", "true", "false",
                 "close", "open", "high", "low", "volume", "abs", "max", "min"}
        names = re.findall(r"\b([a-z_][a-z0-9_]*)\b", formula)
        missing = [n for n in dict.fromkeys(names)
                   if n not in _SKIP and n not in df.columns]

        for name in missing:
            try:
                result = calculate([name], df)
                for ind_name, ind_series in result.items():
                    df[ind_name] = ind_series.values
            except Exception:
                pass

        # Retry after recovery
        return _latest(evaluate_dsl_vectorized(formula, df))


