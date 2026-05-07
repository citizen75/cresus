"""
VWAP (Volume Weighted Average Price) and Anchored VWAP Indicator

Syntax:
  vwap              → VWAP from start of data
  vwap_N            → VWAP anchored at bar N (0-indexed, e.g. vwap_10)
  vwap_YYYY-MM-DD   → VWAP anchored at date (requires date column, e.g. vwap_2024-01-15)

Returns: Series with VWAP values
"""

import pandas as pd
from typing import Optional, Union
from datetime import datetime


def calculate(
    data: pd.DataFrame,
    anchor: Optional[Union[int, str]] = None,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate VWAP (Volume Weighted Average Price).

    Args:
        data: OHLCV DataFrame
        anchor: Anchor point for VWAP calculation
                - None or "start": VWAP from beginning of data
                - int: Bar number to anchor (0-indexed)
                - str (datetime): Date string to anchor (YYYY-MM-DD)
        history_df: Optional historical data (not used for VWAP)

    Returns:
        Series with VWAP values

    Formula:
        VWAP = Cumulative(Typical Price × Volume) / Cumulative(Volume)
        where Typical Price = (High + Low + Close) / 3

    Example:
        >>> vwap = calculate(data, anchor=None)  # VWAP from start
        >>> vwap_anchored = calculate(data, anchor=10)  # VWAP from bar 10
        >>> vwap_date = calculate(data, anchor="2024-01-15")  # VWAP from date
    """
    # Get OHLCV columns (handle both uppercase and mixed case)
    def get_column(df, names):
        for name in names:
            if name in df.columns:
                return df[name]
        raise ValueError(f"Column not found: {names}")

    high = get_column(data, ["HIGH", "High"])
    low = get_column(data, ["LOW", "Low"])
    close = get_column(data, ["CLOSE", "Close"])
    volume = get_column(data, ["VOLUME", "Volume"])

    # Calculate typical price
    typical_price = (high + low + close) / 3.0

    # Determine anchor point
    anchor_idx = _get_anchor_index(data, anchor)

    # Calculate VWAP
    if anchor_idx == 0:
        # Standard VWAP from start
        vwap = _calculate_vwap(typical_price, volume)
    else:
        # Anchored VWAP from specific point
        vwap = _calculate_anchored_vwap(typical_price, volume, anchor_idx)

    return vwap


def _get_anchor_index(data: pd.DataFrame, anchor: Optional[Union[int, str]]) -> int:
    """
    Get the index where VWAP should be anchored.

    Args:
        data: DataFrame
        anchor: Anchor specification (None, int, or date string)

    Returns:
        Index to start VWAP calculation from
    """
    if anchor is None or anchor == "start" or anchor == 0:
        return 0

    if isinstance(anchor, int):
        # Anchor at specific bar
        if anchor < 0 or anchor >= len(data):
            raise ValueError(f"Anchor index {anchor} out of range [0, {len(data)-1}]")
        return anchor

    if isinstance(anchor, str):
        # Anchor at specific date
        if "DATE" in data.columns:
            date_col = "DATE"
        elif "Date" in data.columns:
            date_col = "Date"
        elif "date" in data.columns:
            date_col = "date"
        else:
            raise ValueError("Date column not found in DataFrame")

        dates = pd.to_datetime(data[date_col])
        anchor_date = pd.to_datetime(anchor)

        # Find index of first bar on or after anchor date
        matching_idx = (dates >= anchor_date).idxmax()
        if matching_idx == 0 and dates.iloc[0] > anchor_date:
            raise ValueError(f"Anchor date {anchor} is before first data point")

        return matching_idx

    raise ValueError(f"Invalid anchor type: {type(anchor)}")


def _calculate_vwap(typical_price: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate standard VWAP from start of data.

    Args:
        typical_price: Series of typical prices
        volume: Series of volumes

    Returns:
        Series with VWAP values
    """
    # Cumulative typical price × volume
    cum_tp_volume = (typical_price * volume).cumsum()

    # Cumulative volume
    cum_volume = volume.cumsum()

    # VWAP = cumulative TP×V / cumulative V
    vwap = cum_tp_volume / cum_volume

    return vwap


def _calculate_anchored_vwap(
    typical_price: pd.Series,
    volume: pd.Series,
    anchor_idx: int
) -> pd.Series:
    """
    Calculate VWAP anchored at specific point.

    Args:
        typical_price: Series of typical prices
        volume: Series of volumes
        anchor_idx: Index to anchor VWAP at

    Returns:
        Series with VWAP values (NaN before anchor point)
    """
    # Initialize result with NaN
    vwap = pd.Series(index=typical_price.index, dtype="float64")
    vwap[:anchor_idx] = pd.NA

    # Calculate VWAP from anchor point onwards
    anchor_tp = typical_price.iloc[anchor_idx:]
    anchor_volume = volume.iloc[anchor_idx:]

    # Cumulative from anchor
    cum_tp_volume = (anchor_tp * anchor_volume).cumsum()
    cum_volume = anchor_volume.cumsum()

    # Calculate VWAP values from anchor
    anchor_vwap = cum_tp_volume / cum_volume

    # Assign to result
    vwap.iloc[anchor_idx:] = anchor_vwap.values

    return vwap


def get_syntax_help() -> str:
    """Return syntax help for VWAP indicator."""
    return """
VWAP (Volume Weighted Average Price) Indicator

Syntax:
  vwap              → VWAP from start of data
  vwap_0            → VWAP from bar 0 (same as standard)
  vwap_10           → VWAP anchored at bar 10
  vwap_2024-01-15   → VWAP anchored from 2024-01-15

Formula:
  Typical Price = (High + Low + Close) / 3
  VWAP = Σ(TP × Volume) / Σ(Volume)

Use Cases:
  • Identify mean price level
  • Entry/exit levels
  • Support/resistance
  • Breakout confirmation
  • Mean reversion signals

Example in Formula:
  data['vwap'] > data['close']  # Price below VWAP (bearish)
  data['vwap'] < data['close']  # Price above VWAP (bullish)
  (data['close'] - data['vwap']) / data['vwap'] > 0.02  # 2% above VWAP
"""
