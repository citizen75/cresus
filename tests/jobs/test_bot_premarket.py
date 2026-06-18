"""Tests for BotPremarket job."""

import pytest
import tempfile
from pathlib import Path

from jobs import BotPremarket
from core.job import JobStatus


class TestBotPremarketInitialization:
	"""Test BotPremarket initialization."""

	def test_premarket_init(self):
		"""Test creating a BotPremarket instance."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "premarket_test"
			premarket = BotPremarket("premarket_test", job_dir)

			assert premarket.name == "premarket_test"
			assert premarket.status == JobStatus.PENDING
			assert premarket.markets == []
			assert premarket.tickers_to_analyze == []
			assert premarket.signals == {}
			assert premarket.setups == []


class TestBotPremarketOperations:
	"""Test BotPremarket operations."""

	def test_fetch_overnight_data(self):
		"""Test fetching overnight data."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "premarket_test"
			premarket = BotPremarket("premarket_test", job_dir)

			markets = ["cac40", "nasdaq"]
			result = premarket.fetch_overnight_data(markets)

			assert result["markets"] == markets
			assert premarket.markets == markets

	def test_calculate_indicators(self):
		"""Test indicator calculation."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "premarket_test"
			premarket = BotPremarket("premarket_test", job_dir)

			tickers = ["AC.PA", "OR.PA"]
			indicators = ["RSI", "MACD"]
			result = premarket.calculate_indicators(tickers, indicators)

			assert len(result) == len(tickers)
			assert premarket.tickers_to_analyze == tickers

	def test_identify_opportunities(self):
		"""Test identifying opportunities."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "premarket_test"
			premarket = BotPremarket("premarket_test", job_dir)

			# First set tickers
			premarket.tickers_to_analyze = ["AC.PA", "OR.PA"]

			config = {"rsi_oversold": 30, "rsi_overbought": 70}
			opportunities = premarket.identify_opportunities(config)

			assert len(opportunities) == len(premarket.tickers_to_analyze)
			for opp in opportunities:
				assert "ticker" in opp
				assert "signal" in opp
				assert opp["signal"] == "neutral"

	def test_setup_positions(self):
		"""Test position setup."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "premarket_test"
			premarket = BotPremarket("premarket_test", job_dir)

			opportunities = [
				{"ticker": "AC.PA", "signal": "buy", "entry_price": 50.0, "stop_loss": 47.5, "target": 55.0}
			]
			portfolio_config = {"capital": 100000, "max_position_size": 5000}

			setups = premarket.setup_positions(opportunities, portfolio_config)

			assert len(setups) == 1
			assert setups[0]["ticker"] == "AC.PA"
			assert setups[0]["signal"] == "buy"


class TestBotPremarketWorkflow:
	"""Test full pre-market workflow."""

	def test_execute_premarket_success(self):
		"""Test successful pre-market execution."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "premarket_test"
			premarket = BotPremarket("premarket_test", job_dir)

			summary = premarket.execute_premarket()

			assert summary["status"] == "completed"
			assert premarket.status == JobStatus.SUCCESS
			assert "markets_analyzed" in summary
			assert "opportunities_found" in summary
			assert "positions_ready" in summary

	def test_premarket_workflow_results(self):
		"""Test results from pre-market workflow."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "premarket_test"
			premarket = BotPremarket("premarket_test", job_dir)

			premarket.execute_premarket()

			# Check stored results
			overnight_data = premarket.get_result("overnight_data")
			assert overnight_data is not None
			assert "markets" in overnight_data

			indicators = premarket.get_result("indicators")
			assert indicators is not None

			opportunities = premarket.get_result("opportunities")
			assert opportunities is not None

	def test_premarket_ready_positions(self):
		"""Test getting ready positions."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "premarket_test"
			premarket = BotPremarket("premarket_test", job_dir)

			premarket.execute_premarket()
			positions = premarket.get_ready_positions()

			assert isinstance(positions, list)

	def test_premarket_signals_summary(self):
		"""Test getting signals summary."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "premarket_test"
			premarket = BotPremarket("premarket_test", job_dir)

			premarket.execute_premarket()
			signals = premarket.get_signals_summary()

			assert isinstance(signals, dict)
