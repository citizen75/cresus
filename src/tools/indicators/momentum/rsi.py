"""
RSI (Relative Strength Index) Indicator

Syntax: rsi_<period>
Example: rsi_14

Returns: Series with RSI values (0-100)

The RSI measures the magnitude of recent price changes to evaluate
overbought or oversold conditions. RSI oscillates between 0 and 100.

Key Thresholds:
  - RSI > 70: Overbought condition (potential reversal)
  - RSI < 30: Oversold condition (potential bounce)
  - 50: Neutral level (equal up/down momentum)

Uses pandas-ta library for canonical implementation with Wilder's smoothing.
"""

import pandas as pd
import pandas_ta_classic as pandas_ta
from typing import Optional
from ..utils.helpers import get_close, validate_rsi_output, ColumnError


def calculate(
    data: pd.DataFrame,
    period: int = 14,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.Series:
    """
    Calculate RSI (Relative Strength Index) using pandas-ta.

    Args:
        data: OHLCV DataFrame with CLOSE column
        period: RSI period (default: 14)
        history_df: Optional historical data for extended lookback

    Returns:
        Series with RSI values (0-100)

    Raises:
        ValueError: If CLOSE column not found

    Example:
        >>> import pandas as pd
        >>> data = pd.DataFrame({'Close': [100, 101, 102, 101, 103]})
        >>> rsi_values = calculate(data, period=14)
        >>> print(rsi_values)  # [50, 50, 50, 50, 50] (approximate)
    """
    # Get close prices with error handling
    try:
        close = get_close(data)
    except ColumnError as e:
        raise ValueError(f"RSI calculation failed: {str(e)}") from e

    # Use history if provided
    if history_df is not None:
        try:
            hist_close = get_close(history_df)
            combined = pd.concat([hist_close, close], ignore_index=True)
        except (ColumnError, KeyError):
            combined = close
    else:
        combined = close

    # Calculate RSI using pandas-ta
    try:
        rsi = pandas_ta.rsi(combined, length=period)
    except Exception as e:
        raise ValueError(f"RSI calculation failed with pandas-ta: {str(e)}") from e

    # Extract only current period
    result_len = len(data)
    rsi = rsi.iloc[-result_len:].reset_index(drop=True)

    # Fill NaN with 50 (neutral)
    rsi = rsi.fillna(50)

    # Validate output
    try:
        validate_rsi_output(rsi)
    except Exception as e:
        raise ValueError(f"RSI output validation failed: {str(e)}") from e

    return rsi
