"""Tests for BotBacktest job."""

import pytest
import tempfile
from pathlib import Path

from jobs import BotBacktest
from core.job import JobStatus


class TestBotBacktestInitialization:
	"""Test BotBacktest initialization."""

	def test_backtest_init(self):
		"""Test creating a BotBacktest instance."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			assert backtest.name == "backtest_test"
			assert backtest.status == JobStatus.PENDING
			assert backtest.strategy_config == {}
			assert backtest.backtest_results == {}
			assert backtest.trades == []
			assert backtest.daily_returns == []


class TestBotBacktestOperations:
	"""Test BotBacktest operations."""

	def test_load_historical_data(self):
		"""Test loading historical data."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			result = backtest.load_historical_data(
				["AC.PA", "OR.PA"],
				"2025-01-01",
				"2026-01-01"
			)

			assert result["tickers"] == 2
			assert "2025-01-01" in result["date_range"]
			assert "2026-01-01" in result["date_range"]

	def test_apply_strategy(self):
		"""Test applying strategy."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			strategy_config = {"name": "momentum", "parameters": {"rsi_period": 14}}
			result = backtest.apply_strategy(strategy_config)

			assert result["strategy"] == "momentum"
			assert backtest.strategy_config == strategy_config

	def test_simulate_trades(self):
		"""Test trade simulation."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			trades = backtest.simulate_trades(100000)

			assert isinstance(trades, list)
			assert len(trades) > 0
			for trade in trades:
				assert "type" in trade
				assert "ticker" in trade
				assert "price" in trade

	def test_calculate_metrics(self):
		"""Test calculating metrics."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			trades = [
				{"pnl": 250, "pnl_pct": 0.05},
				{"pnl": -100, "pnl_pct": -0.03},
				{"pnl": 500, "pnl_pct": 0.10}
			]

			metrics = backtest.calculate_metrics(trades)

			assert "total_trades" in metrics
			assert metrics["total_trades"] == 3
			assert "win_rate" in metrics
			assert "total_pnl" in metrics
			assert metrics["total_pnl"] == 650

	def test_calculate_metrics_empty(self):
		"""Test calculating metrics with no trades."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			metrics = backtest.calculate_metrics([])

			assert metrics == {}

	def test_generate_report(self):
		"""Test generating backtest report."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			backtest.strategy_config = {"name": "test_strategy"}
			backtest.backtest_results = {"total_return_pct": 0.15, "win_rate": 0.55}
			backtest.trades = [{"type": "buy"}, {"type": "sell"}]

			report = backtest.generate_report()

			assert report["strategy"] == "test_strategy"
			assert report["trades"] == 2


class TestBotBacktestWorkflow:
	"""Test full backtest workflow."""

	def test_run_backtest_success(self):
		"""Test successful backtest."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			config = {
				"tickers": ["AC.PA"],
				"start_date": "2025-01-01",
				"end_date": "2026-01-01",
				"strategy": {"name": "momentum"},
				"initial_capital": 100000
			}

			summary = backtest.run_backtest(config)

			assert summary["status"] == "completed"
			assert backtest.status == JobStatus.SUCCESS
			assert "total_return" in summary
			assert "win_rate" in summary

	def test_backtest_results_storage(self):
		"""Test that backtest results are stored."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			config = {
				"tickers": ["AC.PA"],
				"start_date": "2025-01-01",
				"end_date": "2026-01-01",
				"strategy": {"name": "momentum"},
				"initial_capital": 100000
			}

			backtest.run_backtest(config)

			# Check stored results
			data_summary = backtest.get_result("data_summary")
			assert data_summary is not None

			strategy_summary = backtest.get_result("strategy_summary")
			assert strategy_summary is not None

			metrics = backtest.get_result("metrics")
			assert metrics is not None

			report = backtest.get_result("report")
			assert report is not None

	def test_backtest_trades_summary(self):
		"""Test getting trades summary."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			backtest.run_backtest({
				"tickers": ["AC.PA"],
				"start_date": "2025-01-01",
				"end_date": "2026-01-01",
				"strategy": {"name": "momentum"},
				"initial_capital": 100000
			})

			summary = backtest.get_trades_summary()

			assert "total_trades" in summary
			assert "trades" in summary

	def test_export_report(self):
		"""Test exporting report."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "backtest_test"
			backtest = BotBacktest("backtest_test", job_dir)

			report_path = backtest.export_report("json")

			assert "backtest_report" in report_path
			assert report_path.endswith(".json")
