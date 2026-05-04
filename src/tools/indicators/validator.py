"""
Data Validator - Validate OHLCV data and formulas.
"""

import pandas as pd
from typing import List, Tuple
from .utils.errors import ColumnError, InsufficientDataError


class DataValidator:
    """Validate OHLCV data for indicator calculations."""

    @staticmethod
    def validate_ohlcv(
        data: pd.DataFrame,
        require_columns: List[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate OHLCV DataFrame.

        Args:
            data: DataFrame to validate
            require_columns: Specific columns to require (defaults to all)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(data, pd.DataFrame):
            return False, "Data must be a pandas DataFrame"

        if data.empty:
            return False, "Data cannot be empty"

        # Normalize column names to uppercase
        data_cols = {col.upper() for col in data.columns}

        # Check required columns
        if require_columns is None:
            require_columns = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]

        missing = [col for col in require_columns if col not in data_cols]
        if missing:
            return False, f"Missing required columns: {missing}"

        return True, ""

    @staticmethod
    def validate_data(
        data: pd.DataFrame,
        require_columns: List[str] = None,
        min_rows: int = 2
    ) -> None:
        """
        Validate OHLCV data, raise on error.

        Args:
            data: DataFrame to validate
            require_columns: Specific columns to require
            min_rows: Minimum number of rows required

        Raises:
            ColumnError: If required columns missing
            InsufficientDataError: If data is empty or has too few rows
        """
        is_valid, error = DataValidator.validate_ohlcv(data, require_columns)
        if not is_valid:
            if "empty" in error.lower() or "rows" in error.lower():
                raise InsufficientDataError(error)
            else:
                raise ColumnError(error)

        if len(data) < min_rows:
            raise InsufficientDataError(
                f"Insufficient data: {len(data)} rows < {min_rows} required"
            )

    @staticmethod
    def normalize_data(data: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize OHLCV DataFrame.

        Args:
            data: Input DataFrame

        Returns:
            DataFrame with:
            - Uppercase column names
            - Reset index
            - No NaN values in OHLCV
        """
        # Normalize column names
        df = data.copy()
        df.columns = df.columns.str.upper()

        # Reset index
        df = df.reset_index(drop=True)

        # Ensure numeric types
        for col in ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Check for NaN in OHLCV
        required_cols = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]
        for col in required_cols:
            if col in df.columns and df[col].isna().any():
                # Forward fill then backward fill to handle edge cases
                df[col] = df[col].ffill().bfill()

        return df

    @staticmethod
    def get_safe_column(data: pd.DataFrame, col_name: str) -> pd.Series:
        """
        Get column from DataFrame with normalization.

        Args:
            data: DataFrame
            col_name: Column name (case-insensitive)

        Returns:
            Series with normalized name

        Raises:
            ColumnError: If column not found
        """
        # Try exact match first
        if col_name in data.columns:
            return data[col_name].reset_index(drop=True)

        # Try uppercase
        upper_name = col_name.upper()
        if upper_name in data.columns:
            return data[upper_name].reset_index(drop=True)

        # Try lowercase
        lower_name = col_name.lower()
        for col in data.columns:
            if col.lower() == lower_name:
                return data[col].reset_index(drop=True)

        raise ColumnError(f"Column '{col_name}' not found in data")
