"""
Watchlist Scores Agent - Calculate scores for watchlist tickers.

Calculates composite scores for each ticker in the watchlist based on
configured alphas, indicators, and scoring rules.
"""

from .agent import WatchlistScoresAgent

__all__ = ["WatchlistScoresAgent"]
