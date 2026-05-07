"""Tests for Blacklist ticker management."""

import unittest
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from tools.universe.blacklist import Blacklist, get_blacklist, _blacklist_instance


class TestBlacklistInitialization(unittest.TestCase):
	"""Test Blacklist class initialization."""

	def test_init_sets_filepath(self):
		"""Test that initialization sets the correct filepath."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			mock_get_db.return_value = Path("/mock/db")
			blacklist = Blacklist()
			self.assertEqual(
				blacklist.filepath,
				Path("/mock/db") / "universes" / "blacklist.csv"
			)

	def test_init_sets_tickers_to_none(self):
		"""Test that initialization sets _tickers cache to None."""
		blacklist = Blacklist()
		self.assertIsNone(blacklist._tickers)


class TestBlacklistExists(unittest.TestCase):
	"""Test Blacklist.exists() method."""

	def test_exists_returns_true_when_file_exists(self):
		"""Test exists() returns True when blacklist file exists."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				blacklist_file.write_text("ticker,reason,date_added\n")

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				self.assertTrue(blacklist.exists())

	def test_exists_returns_false_when_file_missing(self):
		"""Test exists() returns False when blacklist file doesn't exist."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				self.assertFalse(blacklist.exists())


class TestBlacklistGetTickers(unittest.TestCase):
	"""Test Blacklist.get_tickers() method."""

	def test_get_tickers_returns_set(self):
		"""Test that get_tickers() returns a set."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				blacklist_file.write_text(
					"ticker,reason,date_added\nDEAD,Delisted,2026-01-01\n"
				)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				tickers = blacklist.get_tickers()
				self.assertIsInstance(tickers, set)

	def test_get_tickers_returns_uppercase(self):
		"""Test that get_tickers() returns uppercase ticker symbols."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				df = pd.DataFrame({
					"ticker": ["dead", "null"],
					"reason": ["Delisted", "Invalid"],
					"date_added": ["2026-01-01", "2026-01-01"]
				})
				df.to_csv(blacklist_file, index=False)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				tickers = blacklist.get_tickers()
				self.assertEqual(tickers, {"DEAD", "NULL"})

	def test_get_tickers_caches_result(self):
		"""Test that get_tickers() caches the result."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				blacklist_file.write_text(
					"ticker,reason,date_added\nDEAD,Delisted,2026-01-01\n"
				)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				tickers1 = blacklist.get_tickers()
				tickers2 = blacklist.get_tickers()

				# Should return the same object (cached)
				self.assertIs(tickers1, tickers2)

	def test_get_tickers_returns_empty_set_when_file_missing(self):
		"""Test that get_tickers() returns empty set when blacklist file doesn't exist."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				tickers = blacklist.get_tickers()
				self.assertEqual(tickers, set())

	def test_get_tickers_filters_empty_strings(self):
		"""Test that get_tickers() filters out empty strings."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				df = pd.DataFrame({
					"ticker": ["DEAD", "", "NULL"],
					"reason": ["Delisted", "Empty", "Invalid"],
					"date_added": ["2026-01-01", "2026-01-01", "2026-01-01"]
				})
				df.to_csv(blacklist_file, index=False)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				tickers = blacklist.get_tickers()
				self.assertEqual(tickers, {"DEAD", "NULL"})


class TestBlacklistIsBlacklisted(unittest.TestCase):
	"""Test Blacklist.is_blacklisted() method."""

	def test_is_blacklisted_returns_true_for_blacklisted_ticker(self):
		"""Test is_blacklisted() returns True for blacklisted ticker."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				blacklist_file.write_text(
					"ticker,reason,date_added\nDEAD,Delisted,2026-01-01\n"
				)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				self.assertTrue(blacklist.is_blacklisted("DEAD"))

	def test_is_blacklisted_returns_false_for_non_blacklisted_ticker(self):
		"""Test is_blacklisted() returns False for non-blacklisted ticker."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				blacklist_file.write_text(
					"ticker,reason,date_added\nDEAD,Delisted,2026-01-01\n"
				)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				self.assertFalse(blacklist.is_blacklisted("AAPL"))

	def test_is_blacklisted_case_insensitive(self):
		"""Test is_blacklisted() is case-insensitive."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				blacklist_file.write_text(
					"ticker,reason,date_added\ndead,Delisted,2026-01-01\n"
				)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				self.assertTrue(blacklist.is_blacklisted("DEAD"))
				self.assertTrue(blacklist.is_blacklisted("dead"))
				self.assertTrue(blacklist.is_blacklisted("Dead"))


class TestBlacklistAddTicker(unittest.TestCase):
	"""Test Blacklist.add_ticker() method."""

	def test_add_ticker_creates_new_file(self):
		"""Test add_ticker() creates blacklist file if it doesn't exist."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				blacklist.add_ticker("DEAD", reason="Delisted security")

				self.assertTrue(blacklist.filepath.exists())

	def test_add_ticker_writes_uppercase_ticker(self):
		"""Test add_ticker() converts ticker to uppercase."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				blacklist.add_ticker("dead", reason="Delisted security")

				df = pd.read_csv(blacklist.filepath)
				self.assertIn("DEAD", df["ticker"].values)

	def test_add_ticker_includes_date(self):
		"""Test add_ticker() includes current date."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				blacklist.add_ticker("DEAD", reason="Delisted security")

				df = pd.read_csv(blacklist.filepath)
				self.assertEqual(df.iloc[0]["date_added"], datetime.now().date().isoformat())

	def test_add_ticker_appends_to_existing_file(self):
		"""Test add_ticker() appends to existing blacklist."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				df_initial = pd.DataFrame({
					"ticker": ["DEAD"],
					"reason": ["Delisted"],
					"date_added": ["2026-01-01"]
				})
				df_initial.to_csv(blacklist_file, index=False)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				blacklist.add_ticker("NULL", reason="Invalid ticker")

				df = pd.read_csv(blacklist.filepath, keep_default_na=False, na_values=[])
				self.assertEqual(len(df), 2)
				self.assertIn("DEAD", df["ticker"].values)
				self.assertIn("NULL", df["ticker"].values)

	def test_add_ticker_invalidates_cache(self):
		"""Test add_ticker() invalidates the tickers cache."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				df_initial = pd.DataFrame({
					"ticker": ["DEAD"],
					"reason": ["Delisted"],
					"date_added": ["2026-01-01"]
				})
				df_initial.to_csv(blacklist_file, index=False)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()

				# Load and cache the tickers
				tickers1 = blacklist.get_tickers()
				self.assertEqual(tickers1, {"DEAD"})

				# Add a new ticker
				blacklist.add_ticker("NULL", reason="Invalid ticker")

				# Get tickers again - should include the new one
				tickers2 = blacklist.get_tickers()
				self.assertEqual(tickers2, {"DEAD", "NULL"})


class TestBlacklistRemoveTicker(unittest.TestCase):
	"""Test Blacklist.remove_ticker() method."""

	def test_remove_ticker_deletes_from_file(self):
		"""Test remove_ticker() deletes ticker from blacklist."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				df_initial = pd.DataFrame({
					"ticker": ["DEAD", "NULL"],
					"reason": ["Delisted", "Invalid"],
					"date_added": ["2026-01-01", "2026-01-01"]
				})
				df_initial.to_csv(blacklist_file, index=False)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				blacklist.remove_ticker("DEAD")

				df = pd.read_csv(blacklist.filepath, keep_default_na=False, na_values=[])
				self.assertNotIn("DEAD", df["ticker"].values)
				self.assertIn("NULL", df["ticker"].values)

	def test_remove_ticker_case_insensitive(self):
		"""Test remove_ticker() is case-insensitive."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				blacklist_file.write_text(
					"ticker,reason,date_added\nDEAD,Delisted,2026-01-01\nNULL,Invalid,2026-01-01\n"
				)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				blacklist.remove_ticker("dead")

				df = pd.read_csv(blacklist.filepath)
				self.assertNotIn("DEAD", df["ticker"].values)

	def test_remove_ticker_no_op_if_file_missing(self):
		"""Test remove_ticker() is no-op if blacklist file doesn't exist."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				blacklist.remove_ticker("DEAD")  # Should not raise

				self.assertFalse(blacklist.filepath.exists())

	def test_remove_ticker_invalidates_cache(self):
		"""Test remove_ticker() invalidates the tickers cache."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				df_initial = pd.DataFrame({
					"ticker": ["DEAD", "NULL"],
					"reason": ["Delisted", "Invalid"],
					"date_added": ["2026-01-01", "2026-01-01"]
				})
				df_initial.to_csv(blacklist_file, index=False)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()

				# Load and cache the tickers
				tickers1 = blacklist.get_tickers()
				self.assertEqual(tickers1, {"DEAD", "NULL"})

				# Remove a ticker
				blacklist.remove_ticker("DEAD")

				# Get tickers again - DEAD should be gone
				tickers2 = blacklist.get_tickers()
				self.assertEqual(tickers2, {"NULL"})


class TestBlacklistSingleton(unittest.TestCase):
	"""Test Blacklist singleton pattern."""

	def test_get_blacklist_returns_singleton(self):
		"""Test get_blacklist() returns same instance."""
		# Reset the global instance for this test
		import tools.universe.blacklist as blacklist_module
		original = blacklist_module._blacklist_instance
		blacklist_module._blacklist_instance = None

		try:
			instance1 = get_blacklist()
			instance2 = get_blacklist()
			self.assertIs(instance1, instance2)
		finally:
			blacklist_module._blacklist_instance = original

	def test_get_blacklist_creates_instance_on_first_call(self):
		"""Test get_blacklist() creates instance on first call."""
		# Reset the global instance for this test
		import tools.universe.blacklist as blacklist_module
		original = blacklist_module._blacklist_instance
		blacklist_module._blacklist_instance = None

		try:
			instance = get_blacklist()
			self.assertIsNotNone(instance)
			self.assertIsInstance(instance, Blacklist)
		finally:
			blacklist_module._blacklist_instance = original


class TestBlacklistErrorHandling(unittest.TestCase):
	"""Test Blacklist error handling."""

	def test_get_tickers_handles_missing_ticker_column(self):
		"""Test get_tickers() handles CSV without ticker column."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				blacklist_file.write_text(
					"name,reason,date_added\nDEAD,Delisted,2026-01-01\n"
				)

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				tickers = blacklist.get_tickers()
				self.assertEqual(tickers, set())

	def test_get_tickers_handles_invalid_csv(self):
		"""Test get_tickers() handles invalid CSV gracefully."""
		with patch("tools.universe.blacklist.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()
				blacklist_file = universes_dir / "blacklist.csv"
				blacklist_file.write_text("invalid csv content\nno headers here")

				mock_get_db.return_value = tmpdir
				blacklist = Blacklist()
				tickers = blacklist.get_tickers()
				self.assertEqual(tickers, set())


class TestUniverseBlacklistIntegration(unittest.TestCase):
	"""Test Universe integration with Blacklist."""

	@patch("tools.universe.universe.get_blacklist")
	def test_universe_filters_blacklisted_tickers(self, mock_get_blacklist):
		"""Test that Universe.get_tickers() filters blacklisted tickers."""
		from tools.universe.universe import Universe

		# Mock blacklist
		mock_blacklist = MagicMock()
		mock_blacklist.get_tickers.return_value = {"AC.PA"}
		mock_get_blacklist.return_value = mock_blacklist

		with patch("tools.universe.universe.get_db_root") as mock_get_db:
			with tempfile.TemporaryDirectory() as tmpdir:
				tmpdir = Path(tmpdir)
				universes_dir = tmpdir / "universes"
				universes_dir.mkdir()

				# Create a test universe file
				universe_file = universes_dir / "test_universe.csv"
				universe_file.write_text(
					"TickerYahoo,Name,ISIN\nAC.PA,Accor,FR0000120404\nAI.PA,Air Liquide,FR0000120073\n"
				)

				mock_get_db.return_value = tmpdir
				universe = Universe("test_universe")
				tickers = universe.get_tickers()

				# AC.PA should be filtered out
				self.assertNotIn("AC.PA", tickers)
				self.assertIn("AI.PA", tickers)


if __name__ == "__main__":
	unittest.main()
