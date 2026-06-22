"""Per-trade record construction from a portfolio's journal.

`PortfolioMetrics._analyze_trades` (src/tools/portfolio/metrics.py) already
pairs BUY/SELL journal rows FIFO per ticker, but only returns aggregate
stats (win rate, profit factor, ...). Every StrategyTuning diagnosis stage
needs the same pairing kept at trade granularity - ticker, exit_type, dates -
so this module re-implements the pairing once and shares it.
"""

import json
from typing import Any, Dict, List, Optional
import pandas as pd

from tools.portfolio.journal import Journal


def _parse_metadata(raw: Any) -> Dict[str, Any]:
	"""Parse a journal row's `metadata` column (a JSON snapshot of OHLCV +
	every computed indicator at fill time) into a dict, or {} on failure."""
	if not raw or (isinstance(raw, float) and pd.isna(raw)):
		return {}
	if isinstance(raw, dict):
		return raw
	try:
		return json.loads(raw)
	except (TypeError, ValueError):
		return {}


def build_trade_records(portfolio_name: str, context: Optional[Any] = None) -> List[Dict[str, Any]]:
	"""Pair BUY/SELL journal rows FIFO per ticker into closed-trade records.

	Args:
		portfolio_name: Portfolio/backtest name whose journal to read.
		context: Optional AgentContext (or dict) carrying `backtest_dir` so
			`Journal` resolves the right journal file - same context used by
			the backtest run that produced it.

	Returns:
		List of dicts, one per closed (BUY+SELL paired) trade: `ticker`,
		`entry_date`, `entry_price`, `exit_date`, `exit_price`, `quantity`,
		`exit_type`, `pnl_pct`, `pnl_amount`, `holding_days`. Open (unpaired)
		BUYs are omitted - they have no realized return to diagnose.
	"""
	journal = Journal(portfolio_name, context=context)
	df = journal.load_df()
	if df.empty:
		return []

	df = df.copy()
	df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
	df["price"] = pd.to_numeric(df["price"], errors="coerce")
	df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
	df = df.dropna(subset=["created_at", "price", "quantity", "ticker", "operation"])

	records: List[Dict[str, Any]] = []

	for ticker in df["ticker"].unique():
		ticker_df = df[df["ticker"] == ticker].sort_values("created_at")
		buys = ticker_df[ticker_df["operation"].str.upper() == "BUY"]
		sells = ticker_df[ticker_df["operation"].str.upper() == "SELL"]
		paired_sell_ids = set()

		for _, buy in buys.iterrows():
			candidates = sells[
				(sells["created_at"] >= buy["created_at"]) &
				(~sells["id"].isin(paired_sell_ids))
			]
			if candidates.empty:
				continue
			sell = candidates.iloc[0]
			paired_sell_ids.add(sell["id"])

			entry_price = float(buy["price"])
			exit_price = float(sell["price"])
			qty = float(buy["quantity"])
			pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price else 0.0
			holding_days = (sell["created_at"] - buy["created_at"]).days

			exit_type = sell.get("exit_type")
			records.append({
				"ticker": ticker,
				"entry_date": buy["created_at"],
				"entry_price": entry_price,
				"exit_date": sell["created_at"],
				"exit_price": exit_price,
				"quantity": qty,
				"exit_type": str(exit_type).lower().strip() if exit_type and not pd.isna(exit_type) else "unknown",
				"pnl_pct": pnl_pct,
				"pnl_amount": (exit_price - entry_price) * qty,
				"holding_days": holding_days,
				# Full indicator snapshot at entry fill time, straight from the
				# journal - no need to reload price history just for this.
				"entry_indicators": _parse_metadata(buy.get("metadata")),
			})

	return records


def enrich_with_excursion(
	records: List[Dict[str, Any]],
	data_history: Dict[str, pd.DataFrame],
	atr_column: str = "atr_14",
) -> List[Dict[str, Any]]:
	"""Add MAE/MFE (max adverse/favorable excursion) to each trade record.

	Slices the ticker's daily OHLC between entry and exit date (inclusive)
	from `data_history` and computes, relative to the entry fill price:
	- `mae_pct` / `mfe_pct`: worst/best excursion in % terms (always set
	  when price history for the window is available).
	- `mae_atr` / `mfe_atr`: the same excursions expressed as a multiple of
	  the entry-day's `atr_column` value - read from the trade's
	  `entry_indicators` snapshot (set by `build_trade_records`) if present,
	  else from `data_history`'s entry-day row. Left `None` if neither has
	  it - callers should fall back to the `_pct` fields.

	Args:
		records: Trade records from `build_trade_records`.
		data_history: `{ticker: DataFrame}` with at least `timestamp`,
			`high`, `low`, `close` columns (the shape used throughout the
			backtest pipeline - see `tests/fixtures/data/*.parquet`).
		atr_column: Indicator column name to express excursions in ATR
			multiples, if present.

	Returns:
		A new list of records (input is not mutated) with the excursion
		fields added.
	"""
	enriched: List[Dict[str, Any]] = []

	for rec in records:
		rec = dict(rec)
		rec["mae_pct"] = None
		rec["mfe_pct"] = None
		rec["mae_atr"] = None
		rec["mfe_atr"] = None

		df = data_history.get(rec["ticker"]) if data_history else None
		if df is None or df.empty or "timestamp" not in df.columns:
			enriched.append(rec)
			continue

		window_df = df.copy()
		window_df["timestamp"] = pd.to_datetime(window_df["timestamp"], errors="coerce")
		mask = (window_df["timestamp"] >= rec["entry_date"]) & (window_df["timestamp"] <= rec["exit_date"])
		window = window_df.loc[mask].sort_values("timestamp")

		if window.empty or "low" not in window.columns or "high" not in window.columns:
			enriched.append(rec)
			continue

		entry_price = rec["entry_price"]
		worst_low = float(window["low"].min())
		best_high = float(window["high"].max())
		rec["mae_pct"] = (worst_low - entry_price) / entry_price * 100 if entry_price else None
		rec["mfe_pct"] = (best_high - entry_price) / entry_price * 100 if entry_price else None

		entry_atr = (rec.get("entry_indicators") or {}).get(atr_column)
		if entry_atr is None and atr_column in window.columns:
			entry_atr = window.iloc[0].get(atr_column)
		if entry_atr and not pd.isna(entry_atr) and entry_atr > 0:
			rec["mae_atr"] = (entry_price - worst_low) / entry_atr
			rec["mfe_atr"] = (best_high - entry_price) / entry_atr

		enriched.append(rec)

	return enriched
