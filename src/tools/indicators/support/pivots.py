"""
Pivot Points Indicator

Syntax: pivot_<method>
Example: pivot_classic or pivot_camarilla

Returns: Dict with pivot levels
"""

import pandas as pd
from typing import Optional, Dict


def calculate(
    data: pd.DataFrame,
    method: str = "classic",
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate Pivot Points.

    Args:
        data: OHLCV DataFrame with HIGH, LOW, CLOSE columns
        method: Pivot method ('classic', 'camarilla', 'woodie', 'demark')
        history_df: Optional historical data

    Returns:
        Dict with pivot levels

    Supported methods:
        - classic: (H + L + C) / 3, R1 = (P * 2) - L, S1 = (P * 2) - H
        - camarilla: Uses 4 resistance and 4 support levels
        - woodie: ((H + L) / 2) + C
        - demark: Uses proprietary formula
    """
    # Get OHLC
    high = data.get("HIGH", data.get("High", None))
    low = data.get("LOW", data.get("Low", None))
    close = data.get("CLOSE", data.get("Close", None))

    if any(x is None for x in [high, low, close]):
        return {
            "pivot": pd.Series([0.0] * len(data)),
            "pivot_r1": pd.Series([0.0] * len(data)),
            "pivot_s1": pd.Series([0.0] * len(data)),
        }

    # Use last values (daily pivots use previous day's OHLC)
    h = high.iloc[-1]
    l = low.iloc[-1]
    c = close.iloc[-1]

    if method == "classic":
        # Classic Pivot Points
        p = (h + l + c) / 3
        r1 = (p * 2) - l
        r2 = p + (h - l)
        s1 = (p * 2) - h
        s2 = p - (h - l)

    elif method == "camarilla":
        # Camarilla Pivot Points
        hl_range = h - l
        p = (h + l + c) / 3
        r1 = c + 1.1 * (h - l) / 4
        r2 = c + 1.1 * (h - l) / 2
        r3 = c + 1.1 * 3 * (h - l) / 4
        r4 = c + 1.1 * (h - l)
        s1 = c - 1.1 * (h - l) / 4
        s2 = c - 1.1 * (h - l) / 2
        s3 = c - 1.1 * 3 * (h - l) / 4
        s4 = c - 1.1 * (h - l)

    elif method == "woodie":
        # Woodie Pivot Points
        p = ((h + l) / 2) + c
        r1 = (p * 2) - l
        r2 = p + (h - l)
        s1 = (p * 2) - h
        s2 = p - (h - l)

    elif method == "demark":
        # DeMark Pivot Points
        if c < h and c < l:
            x = h + (c * 2) + l
        elif c > h:
            x = (c * 2) + h + l
        else:
            x = (c * 2) + h + l
        p = x / 4
        r1 = (x / 2) - l
        s1 = (x / 2) - h
        r2 = x - l
        s2 = x - h

    else:
        # Default to classic
        p = (h + l + c) / 3
        r1 = (p * 2) - l
        r2 = p + (h - l)
        s1 = (p * 2) - h
        s2 = p - (h - l)

    # Create Series (replicate across data length)
    result_len = len(data)
    pivot_series = pd.Series([p] * result_len)
    r1_series = pd.Series([r1] * result_len)
    r2_series = pd.Series([r2] * result_len)
    s1_series = pd.Series([s1] * result_len)
    s2_series = pd.Series([s2] * result_len)

    result = {
        "pivot": pivot_series,
        "pivot_p": pivot_series,
        "pivot_r1": r1_series,
        "pivot_r2": r2_series,
        "pivot_s1": s1_series,
        "pivot_s2": s2_series,
    }

    # Add camarilla extras if applicable
    if method == "camarilla":
        result["pivot_r3"] = pd.Series([r3] * result_len)
        result["pivot_r4"] = pd.Series([r4] * result_len)
        result["pivot_s3"] = pd.Series([s3] * result_len)
        result["pivot_s4"] = pd.Series([s4] * result_len)

    return result
