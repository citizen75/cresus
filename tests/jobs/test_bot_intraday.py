"""Tests for BotIntraday job."""

import pytest
import tempfile
from pathlib import Path

from jobs import BotIntraday
from core.job import JobStatus


class TestBotIntradayInitialization:
	"""Test BotIntraday initialization."""

	def test_intraday_init(self):
		"""Test creating a BotIntraday instance."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "intraday_test"
			intraday = BotIntraday("intraday_test", job_dir)

			assert intraday.name == "intraday_test"
			assert intraday.status == JobStatus.PENDING
			assert intraday.active_positions == []
			assert intraday.trades_executed == []
			assert intraday.market_events == []


class TestBotIntradayOperations:
	"""Test BotIntraday operations."""

	def test_monitor_positions(self):
		"""Test monitoring positions."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "intraday_test"
			intraday = BotIntraday("intraday_test", job_dir)

			portfolio = {
				"positions": [
					{"ticker": "AC.PA", "pnl": 250, "pnl_pct": 0.05},
					{"ticker": "OR.PA", "pnl": -100, "pnl_pct": -0.03}
				]
			}

			status = intraday.monitor_positions(portfolio)

			assert status["positions_count"] == 2
			assert status["winning_positions"] == 1
			assert status["losing_positions"] == 1

	def test_check_exit_conditions(self):
		"""Test checking exit conditions."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "intraday_test"
			intraday = BotIntraday("intraday_test", job_dir)

			intraday.active_positions = [
				{"ticker": "AC.PA", "pnl": 500, "pnl_pct": 0.12, "current_price": 52.5},
				{"ticker": "OR.PA", "pnl": -200, "pnl_pct": -0.06, "current_price": 48.0}
			]

			rules = {"stop_loss": -0.05, "take_profit": 0.10}
			exits = intraday.check_exit_conditions(rules)

			# Should have exits based on conditions
			assert isinstance(exits, list)

	def test_execute_scale_in(self):
		"""Test scaling in to a position."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "intraday_test"
			intraday = BotIntraday("intraday_test", job_dir)

			trade = intraday.execute_scale_in("AC.PA", 100, 50.0)

			assert trade["type"] == "scale_in"
			assert trade["ticker"] == "AC.PA"
			assert trade["quantity"] == 100
			assert trade["price"] == 50.0
			assert len(intraday.trades_executed) == 1

	def test_execute_scale_out(self):
		"""Test scaling out of a position."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "intraday_test"
			intraday = BotIntraday("intraday_test", job_dir)

			trade = intraday.execute_scale_out("AC.PA", 50, 51.0)

			assert trade["type"] == "scale_out"
			assert trade["ticker"] == "AC.PA"
			assert trade["quantity"] == 50
			assert trade["price"] == 51.0
			assert len(intraday.trades_executed) == 1

	def test_record_market_event(self):
		"""Test recording market events."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "intraday_test"
			intraday = BotIntraday("intraday_test", job_dir)

			intraday.record_market_event("gap", "Large gap up on open", {"gap_size": 0.05})

			assert len(intraday.market_events) == 1
			assert intraday.market_events[0]["type"] == "gap"


class TestBotIntradayWorkflow:
	"""Test full intraday workflow."""

	def test_run_intraday_cycle_success(self):
		"""Test successful intraday cycle."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "intraday_test"
			intraday = BotIntraday("intraday_test", job_dir)

			portfolio = {
				"positions": [
					{"ticker": "AC.PA", "quantity": 100, "pnl": 250, "pnl_pct": 0.05, "current_price": 52.5}
				]
			}

			rules = {
				"exits": {"stop_loss": -0.05, "take_profit": 0.10},
				"scale_in": {"min_strength": 0.7},
				"scale_out": {"max_loss_pct": 0.05}
			}

			summary = intraday.run_intraday_cycle(portfolio, rules)

			assert summary["status"] == "completed"
			assert intraday.status == JobStatus.SUCCESS

	def test_intraday_trade_log(self):
		"""Test getting trade log."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "intraday_test"
			intraday = BotIntraday("intraday_test", job_dir)

			# Execute some trades
			intraday.execute_scale_in("AC.PA", 100, 50.0)
			intraday.execute_scale_out("AC.PA", 50, 51.0)

			trades = intraday.get_trade_log()

			assert len(trades) == 2
			assert trades[0]["type"] == "scale_in"
			assert trades[1]["type"] == "scale_out"

	def test_intraday_market_events_log(self):
		"""Test getting market events log."""
		with tempfile.TemporaryDirectory() as tmpdir:
			job_dir = Path(tmpdir) / "intraday_test"
			intraday = BotIntraday("intraday_test", job_dir)

			intraday.record_market_event("gap", "Gap up", {})
			intraday.record_market_event("breakout", "Breakout", {})

			events = intraday.get_market_events_log()

			assert len(events) == 2
