"""Indicator caching and management.

Stores calculated indicators in parquet files per ticker.
Cache is automatically invalidated when OHLCV data changes.
"""

from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import hashlib
from loguru import logger

from utils.env import get_db_root


class IndicatorCache:
    """Manage cached indicators per ticker."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.cache_dir = get_db_root() / "cache" / "indicators"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_filepath = self.cache_dir / f"{self.ticker}.parquet"

    def get_cached_indicators(self, ohlcv_df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Load cached indicators if they match the current OHLCV data.

        Args:
            ohlcv_df: Current OHLCV data

        Returns:
            Dict of cached indicators, empty dict if cache is invalid or missing
        """
        try:
            if not self.cache_filepath.exists():
                logger.debug(f"{self.ticker}: No cache file found")
                return {}

            # Check if cache is still valid by comparing last row hash
            data_hash = self._get_data_hash(ohlcv_df)
            cache_df = pd.read_parquet(self.cache_filepath)

            # Verify cache has metadata column
            if "_data_hash" not in cache_df.columns:
                logger.debug(f"{self.ticker}: Cache missing metadata, invalidating")
                return {}

            cached_hash = cache_df["_data_hash"].iloc[0] if len(cache_df) > 0 else None

            # Log data info for debugging
            last_row = ohlcv_df.iloc[-1]
            logger.debug(f"{self.ticker}: Cache validation - last row date={last_row.get('TIMESTAMP', '?')}, close={last_row.get('CLOSE', '?')}, volume={last_row.get('VOLUME', '?')}")
            logger.debug(f"{self.ticker}: Data hash computed: '{data_hash}' vs cached: '{cached_hash}'")

            if data_hash == cached_hash:
                # Cache is valid - return all columns except metadata
                indicators = {col: cache_df[col] for col in cache_df.columns if col != "_data_hash"}
                logger.debug(f"{self.ticker}: Cache hit - using {len(indicators)} cached indicators")
                return indicators
            else:
                logger.debug(f"{self.ticker}: Cache invalidated (data hash mismatch)")
                return {}

        except Exception as e:
            logger.warning(f"{self.ticker}: Error loading cache: {e}")
            return {}

    def save_indicators(self, indicators: Dict[str, pd.Series], ohlcv_df: pd.DataFrame) -> None:
        """Save calculated indicators with data hash for validation.

        Args:
            indicators: Dict of indicator Series
            ohlcv_df: OHLCV data used for calculation
        """
        try:
            if not indicators:
                logger.debug(f"{self.ticker}: No indicators to cache")
                return

            # Create DataFrame with indicators
            df = pd.DataFrame(indicators)

            # Add data hash as metadata for cache validation
            data_hash = self._get_data_hash(ohlcv_df)
            df["_data_hash"] = data_hash

            last_row = ohlcv_df.iloc[-1]
            logger.debug(f"{self.ticker}: Saving cache with hash '{data_hash}' (date={last_row.get('TIMESTAMP', '?')}, close={last_row.get('CLOSE', '?')}, volume={last_row.get('VOLUME', '?')})")

            # Write to a temp file then rename into place. A direct write left a
            # half-written/corrupted parquet file readable by a concurrent reader
            # whenever two processes raced on the same ticker (e.g. a stale extra
            # gateway instance), and pyarrow segfaults outright on malformed
            # parquet rather than raising a catchable Python exception.
            tmp_path = self.cache_filepath.with_suffix(".parquet.tmp")
            df.to_parquet(tmp_path, index=False)
            tmp_path.replace(self.cache_filepath)
            logger.info(f"{self.ticker}: Saved {len(indicators)} indicators to cache: {list(indicators.keys())}")
        except Exception as e:
            logger.warning(f"{self.ticker}: Error saving indicator cache: {e}")

    def invalidate(self) -> None:
        """Delete cached indicators for this ticker."""
        try:
            if self.cache_filepath.exists():
                self.cache_filepath.unlink()
                logger.debug(f"{self.ticker}: Invalidated indicator cache")
        except Exception as e:
            logger.warning(f"{self.ticker}: Error invalidating cache: {e}")

    @staticmethod
    def _get_data_hash(ohlcv_df: pd.DataFrame) -> str:
        """Get hash of OHLCV data to detect changes.

        Includes the row count and first row alongside the last row: hashing
        only the last row let a stale, shorter cached indicator Series pass
        as a "hit" whenever the history window grew by prepending older rows
        (the most recent row - and therefore the old hash - never changes),
        merging a too-short Series onto a now-longer DataFrame downstream.
        """
        try:
            if ohlcv_df.empty:
                return ""

            # Access UPPERCASE column names (after normalization)
            first_row = ohlcv_df.iloc[0]
            last_row = ohlcv_df.iloc[-1]

            hash_str = (
                f"{len(ohlcv_df)}:"
                f"{first_row.get('TIMESTAMP', '')}:"
                f"{last_row.get('TIMESTAMP', '')}:{last_row.get('CLOSE', 0)}:{last_row.get('VOLUME', 0)}"
            )
            return hashlib.md5(hash_str.encode()).hexdigest()
        except Exception:
            return ""
