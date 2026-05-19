"""
Watchlist Alphas Agent - Calculate alpha factors from strategy config.

Reads alpha definitions from strategy config and calculates them for all tickers
in data_history, adding alpha columns to the data.
"""

from .agent import WatchlistAlphasAgent

__all__ = ["WatchlistAlphasAgent"]
