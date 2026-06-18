"""Tests for BotDataSync job."""

import pytest
import tempfile
from pathlib import Path

from jobs import BotDataSync
from core.job import JobStatus


class TestBotDataSyncInitialization:
	"""Test BotDataSync initialization."""

	def test_data_sync_init(self):
		"""Test creating a BotDataSync instance."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			assert data_sync.name == "data_sync_test"
			assert data_sync.status == JobStatus.PENDING
			assert data_sync.sources == []
			assert data_sync.data_fetched == {}
			assert data_sync.validation_errors == []
			assert data_sync.sync_stats == {}


class TestBotDataSyncOperations:
	"""Test BotDataSync operations."""

	def test_connect_to_source(self):
		"""Test connecting to data source."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			result = data_sync.connect_to_source("yfinance", {})

			assert result is True
			assert "yfinance" in data_sync.sources

	def test_fetch_ticker_data(self):
		"""Test fetching ticker data."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			result = data_sync.fetch_ticker_data(
				"yfinance",
				["AC.PA", "OR.PA"],
				["close", "high", "low"]
			)

			assert result["source"] == "yfinance"
			assert result["tickers_fetched"] == 2
			assert result["fields"] == 3

	def test_validate_data(self):
		"""Test validating data."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			data = {
				"AC.PA": {"close": 50.0, "high": 51.0, "low": 49.0},
				"OR.PA": {"close": 30.0, "high": 31.0, "low": 29.0}
			}

			result = data_sync.validate_data(data)

			assert "total_checks" in result
			assert "errors" in result
			assert "valid" in result

	def test_reconcile_data(self):
		"""Test reconciling data from multiple sources."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			# Setup data fetched from two sources
			data_sync.data_fetched["yfinance"] = {
				"AC.PA": {"close": 50.0},
				"OR.PA": {"close": 30.0}
			}
			data_sync.data_fetched["iex"] = {
				"AC.PA": {"close": 50.1}
			}

			result = data_sync.reconcile_data("yfinance", "iex")

			assert result["primary_source"] == "yfinance"
			assert result["secondary_source"] == "iex"
			assert "discrepancies" in result

	def test_update_database(self):
		"""Test updating database."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			data = {
				"AC.PA": {"close": 50.0},
				"OR.PA": {"close": 30.0}
			}

			result = data_sync.update_database(data)

			assert "records_updated" in result
			assert "records_inserted" in result
			assert "total_size_bytes" in result

	def test_get_sync_status(self):
		"""Test getting sync status."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			data_sync.connect_to_source("yfinance", {})

			status = data_sync.get_sync_status()

			assert "sources" in status
			assert status["sources"] == 1
			assert "data_points_fetched" in status
			assert "validation_errors" in status


class TestBotDataSyncWorkflow:
	"""Test full data sync workflow."""

	def test_run_sync_success(self):
		"""Test successful data sync."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			config = {
				"sources": ["yfinance"],
				"tickers": ["AC.PA", "OR.PA"],
				"fields": ["close", "high", "low", "volume"],
				"yfinance_credentials": {}
			}

			summary = data_sync.run_sync(config)

			assert summary["status"] == "completed"
			assert data_sync.status == JobStatus.SUCCESS
			assert "sources_synced" in summary
			assert "tickers_updated" in summary

	def test_sync_results_storage(self):
		"""Test that sync results are stored."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			config = {
				"sources": ["yfinance"],
				"tickers": ["AC.PA"],
				"fields": ["close", "high", "low"],
				"yfinance_credentials": {}
			}

			data_sync.run_sync(config)

			# Check stored results
			connection_result = data_sync.get_result("connection_yfinance")
			assert connection_result is not None

			fetch_result = data_sync.get_result("fetch_yfinance")
			assert fetch_result is not None

			validation_result = data_sync.get_result("validation")
			assert validation_result is not None

	def test_get_sync_report(self):
		"""Test getting detailed sync report."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			config = {
				"sources": ["yfinance"],
				"tickers": ["AC.PA"],
				"fields": ["close", "high", "low"],
				"yfinance_credentials": {}
			}

			data_sync.run_sync(config)

			report = data_sync.get_sync_report()

			assert "sources" in report
			assert "status" in report
			assert report["status"] == "success"
			assert "created_at" in report

	def test_get_error_details(self):
		"""Test getting error details."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "data_sync_test"
			data_sync = BotDataSync("data_sync_test", job_dir)

			# Add validation errors
			data_sync.validation_errors = [
				{"ticker": "AC.PA", "error": "missing_data", "severity": "high"}
			]

			errors = data_sync.get_error_details()

			assert len(errors) == 1
			assert errors[0]["ticker"] == "AC.PA"
