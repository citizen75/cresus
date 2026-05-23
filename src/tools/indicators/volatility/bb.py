"""
Bollinger Bands Indicator

Syntax: bb_<period>_<std_dev> or bollinger_bands_<period>_<std_dev>
Example: bb_20_2

Returns: Dict with 'bb_upper', 'bb_middle', 'bb_lower' Series

Uses pandas-ta library for canonical implementation.
"""

import pandas as pd
import pandas_ta_classic as pandas_ta
from typing import Optional, Dict
from ..utils.helpers import get_close


def calculate(
    data: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2,
    history_df: Optional[pd.DataFrame] = None,
    **kwargs
) -> Dict[str, pd.Series]:
    """
    Calculate Bollinger Bands using pandas-ta.

    Args:
        data: OHLCV DataFrame
        period: SMA period (default: 20)
        std_dev: Standard deviation multiplier (default: 2)
        history_df: Optional historical data for extended lookback

    Returns:
        Dict with keys:
            - 'bb': Upper band
            - 'bb_upper': Upper band
            - 'bb_middle': Middle band (SMA)
            - 'bb_lower': Lower band
    """
    # Get close prices
    close = get_close(data)

    # Use history if provided
    if history_df is not None:
        hist_close = get_close(history_df)
        combined = pd.concat([hist_close, close], ignore_index=True)
    else:
        combined = close

    # Calculate Bollinger Bands using pandas-ta
    # pandas-ta supports lower_std and upper_std parameters
    bb_df = pandas_ta.bbands(combined, length=period, lower_std=std_dev, upper_std=std_dev)

    # Extract only current period
    result_len = len(data)

    # Find the columns in the result (names follow pattern BBL_<period>_<lower>_<upper>, etc.)
    # Extract by column position: BBL (0), BBM (1), BBU (2)
    if len(bb_df.columns) >= 3:
        lower = bb_df.iloc[:, 0].iloc[-result_len:].reset_index(drop=True)
        middle = bb_df.iloc[:, 1].iloc[-result_len:].reset_index(drop=True)
        upper = bb_df.iloc[:, 2].iloc[-result_len:].reset_index(drop=True)
    else:
        # Fallback: calculate manually if pandas-ta doesn't return expected format
        from ..utils.helpers import get_close as get_close_local
        close_data = get_close_local(data)
        sma = combined.rolling(window=period, min_periods=1).mean()
        std = combined.rolling(window=period, min_periods=1).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        middle = sma
        result_len = len(data)
        lower = lower.iloc[-result_len:].reset_index(drop=True)
        middle = middle.iloc[-result_len:].reset_index(drop=True)
        upper = upper.iloc[-result_len:].reset_index(drop=True)

    return {
        "bb": upper,
        "bb_upper": upper,
        "bb_middle": middle,
        "bb_lower": lower,
    }
