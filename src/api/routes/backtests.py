"""Backtest API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from functools import lru_cache
import sys
import threading
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from tools.backtest.manager import BacktestManager
from flows.backtest import BacktestFlow
from tools.strategy.strategy import StrategyManager
from tools.portfolio.portfolio_distribution import PortfolioDistribution

router = APIRouter(prefix="/backtests", tags=["backtests"])


@lru_cache(maxsize=1)
def _get_backtest_manager() -> BacktestManager:
	"""Get cached BacktestManager instance."""
	return BacktestManager()


@lru_cache(maxsize=1)
def _get_strategy_manager() -> StrategyManager:
	"""Get cached StrategyManager instance."""
	return StrategyManager()


@lru_cache(maxsize=1)
def _get_backtest_flow() -> BacktestFlow:
	"""Get cached BacktestFlow instance."""
	return BacktestFlow()


@router.get("")
async def list_backtests(strategy: Optional[str] = Query(None)) -> Dict[str, Any]:
	"""List all backtests, optionally filtered by strategy.

	Args:
		strategy: Optional strategy name to filter by

	Returns:
		List of backtest summaries
	"""
	manager = _get_backtest_manager()
	backtests = manager.list_backtests(strategy)

	return {
		"status": "success",
		"backtests": backtests,
		"total": len(backtests),
	}


@router.get("/{strategy_name}/{backtest_id}")
async def get_backtest(strategy_name: str, backtest_id: str) -> Dict[str, Any]:
	"""Get detailed backtest results.

	Args:
		strategy_name: Strategy name
		backtest_id: Backtest ID

	Returns:
		Detailed backtest data
	"""
	manager = _get_backtest_manager()
	result = manager.get_backtest(strategy_name, backtest_id)

	if result.get("status") != "success":
		raise HTTPException(status_code=404, detail=result.get("message", "Not found"))

	return result


@router.post("")
async def run_backtest(body: Dict[str, Any]) -> Dict[str, Any]:
	"""Run a backtest or live mode execution.

	If start_date and end_date provided: runs historical backtest via BacktestFlow
	Otherwise: runs live mode (PreMarketFlow) for current watchlist generation

	Args:
		body: {
			strategy (required),
			start_date? (YYYY-MM-DD),
			end_date? (YYYY-MM-DD),
			portfolio_name?
		}

	Returns:
		backtest_id and status for historical backtest, or watchlist_path for live mode
	"""
	import uuid
	from datetime import datetime

	strategy = body.get("strategy")
	if not strategy:
		raise HTTPException(status_code=400, detail="strategy is required")

	start_date = body.get("start_date")
	end_date = body.get("end_date")
	portfolio_name = body.get("portfolio_name") or strategy

	# Determine if this is a historical backtest or live mode
	if start_date and end_date:
		# Historical backtest
		backtest_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

		def run_backtest_bg():
			try:
				flow = _get_backtest_flow()
				result = flow.process({
					"strategy": strategy,
					"start_date": start_date,
					"end_date": end_date,
					"portfolio_name": portfolio_name,
					"backtest_id": backtest_id,
				})

				if result.get("status") != "success":
					import logging
					logger = logging.getLogger(__name__)
					logger.error(f"BacktestFlow for {strategy} failed: {result.get('message')}")
			except Exception as e:
				import logging
				logger = logging.getLogger(__name__)
				logger.error(f"BacktestFlow for {strategy} failed: {str(e)}", exc_info=True)

		thread = threading.Thread(target=run_backtest_bg, daemon=True)
		thread.start()

		return {
			"status": "success",
			"message": f"Backtest {backtest_id} started for {strategy}",
			"backtest_id": backtest_id,
			"strategy": strategy,
			"start_date": start_date,
			"end_date": end_date,
		}
	else:
		# Live mode (PreMarketFlow)
		def run_premarket_bg():
			try:
				from flows.premarket import PreMarketFlow
				flow = PreMarketFlow(strategy)
				result = flow.process({
					"portfolio_name": portfolio_name,
					"save_enabled": True,
				})

				if result.get("status") != "success":
					import logging
					logger = logging.getLogger(__name__)
					logger.error(f"PreMarketFlow for {strategy} failed: {result.get('message')}")
			except Exception as e:
				import logging
				logger = logging.getLogger(__name__)
				logger.error(f"PreMarketFlow for {strategy} failed: {str(e)}", exc_info=True)

		thread = threading.Thread(target=run_premarket_bg, daemon=True)
		thread.start()

		# Return immediately with strategy info
		return {
			"status": "success",
			"message": f"Strategy {strategy} running in live mode",
			"strategy_name": strategy,
			"portfolio_name": portfolio_name,
			"watchlist_path": f"~/.cresus/db/portfolios/{portfolio_name}/watchlist.csv",
		}


@router.get("/compare")
async def compare_backtests(items: str = Query(...)) -> Dict[str, Any]:
	"""Compare multiple backtests.

	Args:
		items: Comma-separated list of "strategy:backtest_id" pairs

	Returns:
		Comparison data
	"""
	manager = _get_backtest_manager()

	# Parse items string: "strategy1:id1,strategy2:id2"
	compare_items = []
	for item in items.split(","):
		parts = item.strip().split(":")
		if len(parts) == 2:
			compare_items.append(
				{
					"strategy": parts[0].strip(),
					"backtest_id": parts[1].strip(),
				}
			)

	if not compare_items:
		raise HTTPException(status_code=400, detail="Invalid items format")

	result = manager.get_backtests_for_compare(compare_items)

	if result.get("status") != "success":
		raise HTTPException(status_code=400, detail="Failed to load comparison data")

	return result


@router.get("/{strategy_name}/{backtest_id}/metrics")
async def get_backtest_metrics(strategy_name: str, backtest_id: str) -> Dict[str, Any]:
	"""Get backtest metrics.

	Args:
		strategy_name: Strategy name
		backtest_id: Backtest ID

	Returns:
		Backtest metrics
	"""
	manager = _get_backtest_manager()
	metrics = manager.get_metrics(strategy_name, backtest_id)

	if not metrics:
		raise HTTPException(status_code=404, detail="Metrics not found")

	return {
		"status": "success",
		"strategy_name": strategy_name,
		"backtest_id": backtest_id,
		"metrics": metrics,
	}


@router.get("/{strategy_name}/{backtest_id}/history")
async def get_backtest_history(strategy_name: str, backtest_id: str) -> Dict[str, Any]:
	"""Get portfolio history with evolving metrics.

	Returns daily equity curve with metrics calculated at each point in time.
	Used for real-time updates during backtest execution.

	Args:
		strategy_name: Strategy name
		backtest_id: Backtest ID

	Returns:
		Historical data with daily metrics
	"""
	manager = _get_backtest_manager()
	result = manager.get_portfolio_history(strategy_name, backtest_id)

	if result.get("status") != "success":
		raise HTTPException(status_code=404, detail=result.get("message"))

	return result


@router.get("/{strategy_name}/{backtest_id}/distribution")
async def get_backtest_distribution(strategy_name: str, backtest_id: str) -> Dict[str, Any]:
	"""Get return distribution for a backtest's portfolio.

	Args:
		strategy_name: Strategy name
		backtest_id: Backtest ID

	Returns:
		Distribution data with deciles, trade counts, and cumulative P&L
	"""
	try:
		# Get the backtest manager and directory
		manager = _get_backtest_manager()

		# Get backtest directory from manager
		from pathlib import Path
		from utils.env import get_db_root
		db_root = get_db_root()
		backtest_dir = db_root / "backtests" / strategy_name / backtest_id

		if not backtest_dir.exists():
			raise HTTPException(status_code=404, detail="Backtest not found")

		# Use strategy_name as the portfolio name (matching backtest behavior)
		portfolio_name = strategy_name

		# Create context for PortfolioDistribution to use backtest directory
		context = {
			"backtest_dir": str(backtest_dir),
		}

		# Calculate distribution for the portfolio with backtest context
		distributor = PortfolioDistribution(portfolio_name, context=context)
		calc_result = distributor.calculate()

		if calc_result.get("status") != "success":
			raise HTTPException(status_code=400, detail=calc_result.get("message"))

		# Return in same format as other backtest endpoints
		return {
			"status": "success",
			"data": {
				"strategy_name": strategy_name,
				"backtest_id": backtest_id,
				"distribution": calc_result.get("distribution", []),
				"statistics": calc_result.get("statistics", {}),
				"trades": calc_result.get("trades", []),  # Closed trades with metadata
			}
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error calculating distribution: {str(e)}")


@router.delete("/{strategy_name}/{backtest_id}")
async def delete_backtest(strategy_name: str, backtest_id: str) -> Dict[str, Any]:
	"""Delete a backtest.

	Args:
		strategy_name: Strategy name
		backtest_id: Backtest ID

	Returns:
		Status message
	"""
	manager = _get_backtest_manager()
	result = manager.delete_backtest(strategy_name, backtest_id)

	if result.get("status") != "success":
		raise HTTPException(status_code=400, detail=result.get("message"))

	return result


@router.get("/strategy/{strategy_name}/watchlist")
async def get_strategy_watchlist(strategy_name: str) -> Dict[str, Any]:
	"""Get watchlist for a strategy (from portfolio directory).

	Loads watchlist from ~/.cresus/db/portfolios/{strategy_name}/watchlist.csv

	Args:
		strategy_name: Strategy name

	Returns:
		Watchlist data
	"""
	from pathlib import Path
	from utils.env import get_db_root
	import pandas as pd

	db_root = get_db_root()
	watchlist_file = db_root / "portfolios" / strategy_name / "watchlist.csv"

	if not watchlist_file.exists():
		return {
			"status": "success",
			"data": {"watchlist": []},
			"message": f"No watchlist data available for strategy {strategy_name}"
		}

	try:
		df = pd.read_csv(watchlist_file)
		watchlist = df.to_dict('records')

		return {
			"status": "success",
			"data": {"watchlist": watchlist}
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error loading watchlist: {str(e)}")


@router.get("/{strategy_name}/{backtest_id}/watchlist")
async def get_backtest_watchlist(strategy_name: str, backtest_id: str) -> Dict[str, Any]:
	"""Get watchlist for a backtest (legacy - for backtests run in sandbox mode).

	Args:
		strategy_name: Strategy name
		backtest_id: Backtest ID

	Returns:
		Watchlist data
	"""
	from pathlib import Path
	from utils.env import get_db_root
	import pandas as pd

	db_root = get_db_root()
	backtest_dir = db_root / "backtests" / strategy_name / backtest_id

	if not backtest_dir.exists():
		raise HTTPException(status_code=404, detail="Backtest not found")

	# Look for watchlist file in backtest/watchlist subdirectory
	watchlist_file = backtest_dir / "watchlist" / f"{strategy_name}.csv"

	if not watchlist_file.exists():
		return {
			"status": "success",
			"data": {"watchlist": []},
			"message": "No watchlist data available for this backtest"
		}

	try:
		df = pd.read_csv(watchlist_file)
		watchlist = df.to_dict('records')

		return {
			"status": "success",
			"data": {"watchlist": watchlist}
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error loading watchlist: {str(e)}")


@router.post("/{strategy_name}/{backtest_id}/watchlist/regenerate")
async def regenerate_backtest_watchlist(strategy_name: str, backtest_id: str) -> Dict[str, Any]:
	"""Reload watchlist for a backtest (it's generated during backtest execution).

	The watchlist is already saved during backtest. This endpoint reloads it from disk.

	Args:
		strategy_name: Strategy name
		backtest_id: Backtest ID

	Returns:
		Watchlist data
	"""
	from pathlib import Path
	from utils.env import get_db_root
	import pandas as pd

	db_root = get_db_root()
	backtest_dir = db_root / "backtests" / strategy_name / backtest_id

	if not backtest_dir.exists():
		raise HTTPException(status_code=404, detail="Backtest not found")

	try:
		watchlist_file = backtest_dir / "watchlist" / f"{strategy_name}.csv"

		if not watchlist_file.exists():
			return {
				"status": "success",
				"data": {"watchlist": []},
				"message": "Watchlist not available for this backtest"
			}

		df = pd.read_csv(watchlist_file)
		watchlist = df.to_dict('records')

		return {
			"status": "success",
			"data": {"watchlist": watchlist},
			"message": "Watchlist loaded successfully"
		}
	except Exception as e:
		import logging
		logger = logging.getLogger(__name__)
		logger.error(f"Error loading watchlist: {str(e)}", exc_info=True)
		raise HTTPException(status_code=500, detail=f"Error loading watchlist: {str(e)}")
