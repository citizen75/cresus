"""Examples of using specialized job classes."""

from pathlib import Path
from tools.jobs import JobManager
from jobs import BotPremarket, BotIntraday, BotBacktest, BotDataSync


def example_premarket_job():
	"""Example: Running a pre-market trading bot."""
	print("=== Pre-Market Bot Example ===\n")

	manager = JobManager()

	# Create a pre-market job
	premarket = manager.create_job("premarket_monday")

	# Initialize specific to BotPremarket
	if isinstance(premarket, BotPremarket):
		# Run the full workflow
		summary = premarket.execute_premarket()

		print(f"Pre-market execution summary:")
		print(f"  Markets analyzed: {summary['markets_analyzed']}")
		print(f"  Tickers analyzed: {summary['tickers_analyzed']}")
		print(f"  Opportunities found: {summary['opportunities_found']}")
		print(f"  Positions ready: {summary['positions_ready']}\n")


def example_intraday_job():
	"""Example: Running an intraday trading bot."""
	print("=== Intraday Bot Example ===\n")

	manager = JobManager()

	# Create an intraday job
	intraday = manager.create_job("intraday_monday")

	# Sample portfolio
	portfolio = {
		"positions": [
			{"ticker": "AC.PA", "quantity": 100, "pnl": 250, "pnl_pct": 0.05, "current_price": 52.5},
			{"ticker": "OR.PA", "quantity": 50, "pnl": -100, "pnl_pct": -0.03, "current_price": 48.0}
		],
		"cash": 50000,
		"total_value": 150000
	}

	# Trading rules
	rules = {
		"exits": {
			"stop_loss": -0.05,
			"take_profit": 0.10,
			"time_based": None
		},
		"scale_in": {"min_strength": 0.7},
		"scale_out": {"max_loss_pct": 0.05}
	}

	# Run intraday cycle
	summary = intraday.run_intraday_cycle(portfolio, rules)

	print(f"Intraday cycle summary:")
	print(f"  Positions monitored: {summary['positions_monitored']}")
	print(f"  Trades executed: {summary['trades_executed']}")
	print(f"  Positions exited: {summary['positions_exited']}")
	print(f"  Total P&L: ${summary['total_pnl']:.2f}\n")

	# View trade log
	trades = intraday.get_trade_log()
	print(f"Trades executed: {len(trades)}")
	for trade in trades:
		print(f"  {trade['type']}: {trade['ticker']} x{trade['quantity']} @ {trade['price']}\n")


def example_backtest_job():
	"""Example: Running a backtesting job."""
	print("=== Backtest Bot Example ===\n")

	manager = JobManager()

	# Create a backtest job
	backtest = manager.create_job("backtest_momentum_cac40")

	# Backtest configuration
	config = {
		"tickers": ["AC.PA", "OR.PA", "CS.PA"],
		"start_date": "2025-01-01",
		"end_date": "2026-01-01",
		"strategy": {
			"name": "momentum",
			"parameters": {
				"rsi_period": 14,
				"rsi_overbought": 70,
				"rsi_oversold": 30
			}
		},
		"initial_capital": 100000
	}

	# Run backtest
	summary = backtest.run_backtest(config)

	print(f"Backtest summary:")
	print(f"  Trades executed: {summary['trades_executed']}")
	print(f"  Total return: {summary['total_return']:.2%}")
	print(f"  Win rate: {summary['win_rate']:.2%}")
	print(f"  Sharpe ratio: {summary['sharpe_ratio']:.2f}\n")

	# Get detailed metrics
	metrics = backtest.backtest_results
	print(f"Detailed metrics:")
	print(f"  Winning trades: {metrics.get('winning_trades', 0)}")
	print(f"  Losing trades: {metrics.get('losing_trades', 0)}")
	print(f"  Avg win: ${metrics.get('avg_win', 0):.2f}")
	print(f"  Avg loss: ${metrics.get('avg_loss', 0):.2f}\n")


def example_data_sync_job():
	"""Example: Running a data synchronization job."""
	print("=== Data Sync Bot Example ===\n")

	manager = JobManager()

	# Create a data sync job
	data_sync = manager.create_job("data_sync_daily")

	# Sync configuration
	config = {
		"sources": ["yfinance"],
		"tickers": ["AC.PA", "OR.PA", "CS.PA", "GLE.PA"],
		"fields": ["close", "high", "low", "volume", "adj_close"],
		"yfinance_credentials": {}  # No auth needed for yfinance
	}

	# Run sync
	summary = data_sync.run_sync(config)

	print(f"Data sync summary:")
	print(f"  Sources synced: {summary['sources_synced']}")
	print(f"  Tickers updated: {summary['tickers_updated']}")
	print(f"  Records updated: {summary['records_updated']}")
	print(f"  Errors: {summary['errors']}\n")

	# Get detailed report
	report = data_sync.get_sync_report()
	print(f"Sync report:")
	print(f"  Sources: {', '.join(report['sources'])}")
	print(f"  Status: {report['status']}")
	print(f"  Started: {report['started_at']}")
	print(f"  Ended: {report['ended_at']}\n")


def example_job_orchestration():
	"""Example: Orchestrating multiple jobs in sequence."""
	print("=== Multi-Job Orchestration Example ===\n")

	manager = JobManager()

	# Step 1: Sync data
	print("Step 1: Syncing market data...")
	data_sync = manager.create_job("daily_sync_20260618")
	sync_config = {
		"sources": ["yfinance"],
		"tickers": ["AC.PA", "OR.PA"],
		"fields": ["close", "high", "low", "volume"]
	}
	sync_summary = data_sync.run_sync(sync_config)
	print(f"  ✓ Synced {sync_summary['tickers_updated']} tickers\n")

	# Step 2: Run backtest on synced data
	print("Step 2: Backtesting strategy...")
	backtest = manager.create_job("daily_backtest_20260618")
	backtest_config = {
		"tickers": ["AC.PA", "OR.PA"],
		"start_date": "2025-01-01",
		"end_date": "2026-01-01",
		"strategy": {"name": "momentum"},
		"initial_capital": 100000
	}
	backtest_summary = backtest.run_backtest(backtest_config)
	print(f"  ✓ Backtest completed with {backtest_summary['total_return']:.2%} return\n")

	# Step 3: Prepare premarket if backtest is good
	if backtest_summary['sharpe_ratio'] > 1.0:
		print("Step 3: Preparing pre-market setup...")
		premarket = manager.create_job("daily_premarket_20260619")
		premarket_summary = premarket.execute_premarket()
		print(f"  ✓ Found {premarket_summary['opportunities_found']} trading opportunities\n")
	else:
		print("Step 3: Skipping pre-market (Sharpe ratio too low)\n")

	# Summary
	print("=== Orchestration Complete ===")
	all_jobs = manager.list_jobs()
	print(f"Total jobs created: {len(all_jobs)}")


def example_accessing_job_results():
	"""Example: Accessing results from completed jobs."""
	print("=== Accessing Job Results Example ===\n")

	manager = JobManager()

	# Create and run a job
	backtest = manager.create_job("backtest_results_demo")
	config = {
		"tickers": ["AC.PA"],
		"start_date": "2025-01-01",
		"end_date": "2026-01-01",
		"strategy": {"name": "simple"},
		"initial_capital": 100000
	}
	backtest.run_backtest(config)

	# Access results
	print("Accessing job results:")
	print(f"  Job status: {backtest.status.value}")
	print(f"  Created: {backtest.created_at}")
	print(f"  Duration: {backtest.get_duration_seconds():.1f} seconds")

	# Get specific results
	metrics = backtest.get_result("metrics")
	report = backtest.get_result("report")

	print(f"\n  Metrics:")
	if metrics:
		print(f"    Total return: {metrics.get('total_return_pct', 0):.2%}")
		print(f"    Win rate: {metrics.get('win_rate', 0):.2%}")

	print(f"\n  Report:")
	if report:
		print(f"    Strategy: {report.get('strategy')}")
		print(f"    Trades: {report.get('trades')}\n")


if __name__ == "__main__":
	# Run all examples
	example_premarket_job()
	example_intraday_job()
	example_backtest_job()
	example_data_sync_job()
	example_job_orchestration()
	example_accessing_job_results()

	print("\n=== All Examples Complete ===")
