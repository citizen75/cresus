"""Alert evaluation using DSL formulas."""

from typing import List, Dict, Any, Optional
from datetime import date
import logging

from .models import Alert, AlertSource, AlertResult
from tools.universe.universe import Universe
from tools.data.core import DataHistory
from tools.indicators import calculate
from tools.formula.dsl_parser import evaluate_dsl_vectorized
from tools.portfolio.manager import PortfolioManager

logger = logging.getLogger(__name__)


class AlertEvaluator:
    """Evaluate alerts using DSL formulas against data."""

    def __init__(self):
        """Initialize evaluator."""
        self.logger = logger

    def evaluate_alert(self, alert: Alert, target_date: Optional[date] = None) -> AlertResult:
        """Evaluate an alert and return matches.

        Args:
            alert: Alert configuration
            target_date: Date to evaluate on (default: today)

        Returns:
            AlertResult with matches and metadata
        """
        try:
            # Get tickers to evaluate
            tickers = self._get_tickers(alert)

            if not tickers:
                return AlertResult(
                    alert_name=alert.name,
                    matched=False,
                    error=f"No tickers found for source: {alert.source.value}",
                )

            # Extract indicators from formula
            indicators = self._extract_indicators(alert.formula)

            # Evaluate against each ticker
            matches = []
            for ticker in tickers:
                try:
                    result = self._evaluate_ticker(ticker, alert.formula, indicators, target_date)
                    if result:
                        matches.extend(result)
                except Exception as e:
                    self.logger.debug(f"Error evaluating {ticker}: {e}")
                    continue

            return AlertResult(
                alert_name=alert.name,
                matched=len(matches) > 0,
                matches=matches,
                tickers_checked=len(tickers),
            )

        except Exception as e:
            self.logger.error(f"Error evaluating alert {alert.name}: {e}")
            return AlertResult(
                alert_name=alert.name,
                matched=False,
                error=str(e),
            )

    def _get_tickers(self, alert: Alert) -> List[str]:
        """Get list of tickers based on alert source."""
        try:
            if alert.source == AlertSource.TICKER:
                return [alert.source_value] if alert.source_value else []

            elif alert.source == AlertSource.TICKERS:
                return [t.strip() for t in alert.source_value.split(',')] if alert.source_value else []

            elif alert.source == AlertSource.UNIVERSE:
                if not alert.source_value:
                    return []
                universe = Universe(alert.source_value)
                if universe.exists():
                    return universe.get_tickers()
                return []

            elif alert.source == AlertSource.PORTFOLIO:
                if not alert.source_value:
                    return []
                pm = PortfolioManager()
                positions = pm.get_portfolio_positions(alert.source_value)
                if positions:
                    return [p.get('ticker') for p in positions.get('positions', [])]
                return []

            elif alert.source == AlertSource.ALL_PORTFOLIOS:
                pm = PortfolioManager()
                all_portfolios = pm.list_portfolios()
                # Only include real portfolios, not paper trading simulations
                real_portfolios = [p for p in all_portfolios if p.get('type') == 'real']
                tickers = set()
                for pf in real_portfolios:
                    positions = pm.get_portfolio_positions(pf.get('name'))
                    if positions:
                        for p in positions.get('positions', []):
                            tickers.add(p.get('ticker'))
                return list(tickers)

            return []

        except Exception as e:
            self.logger.error(f"Error getting tickers for {alert.source.value}: {e}")
            return []

    def _extract_indicators(self, formula: str) -> List[str]:
        """Extract indicator names from formula."""
        import re
        indicators = set()

        # Pattern for indicators like rsi_14[0]
        pattern = r'(\w+)\[(-?\d+)\]'
        for match in re.finditer(pattern, formula):
            indicators.add(match.group(1))

        return list(indicators)

    def _evaluate_ticker(
        self,
        ticker: str,
        formula: str,
        indicators: List[str],
        target_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluate formula for a single ticker.

        Returns:
            List of matching rows
        """
        try:
            # Load historical data
            dh = DataHistory(ticker)
            history_df = dh.get_all()

            if history_df is None or history_df.empty:
                return []

            # Determine date column
            date_col = 'timestamp' if 'timestamp' in history_df.columns else 'date'

            # Sort by date
            history_df = history_df.sort_values(date_col).reset_index(drop=True)

            # Limit to last 60 days for performance
            if len(history_df) > 60:
                history_df = history_df.iloc[-60:].reset_index(drop=True)

            # Calculate missing indicators
            missing_indicators = [ind for ind in indicators if ind.lower() not in history_df.columns]

            if missing_indicators:
                indicator_results = calculate(missing_indicators, history_df)
                for indicator_name, indicator_series in indicator_results.items():
                    history_df[indicator_name.lower()] = indicator_series

            # For alerts, only evaluate the latest row (current candle [0])
            # This prevents returning all historical matches when using [0] notation
            if len(history_df) > 0:
                latest_row = history_df.iloc[-1]
                latest_dict = latest_row.to_dict()

                # Evaluate formula on latest row only
                try:
                    from tools.formula.dsl_parser import evaluate_dsl
                    if evaluate_dsl(formula, latest_dict):
                        latest_dict['ticker'] = ticker
                        return [latest_dict]
                except Exception as e:
                    self.logger.warning(f"Error evaluating formula for {ticker}: {e}")
                    # Return empty list instead of falling back to all historical matches
                    return []

            return []

        except Exception as e:
            self.logger.debug(f"Error evaluating {ticker}: {e}")
            return []
