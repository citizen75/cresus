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
	"""Run a new backtest in background.

	Args:
		body: {strategy, start_date?, end_date?, portfolio_name?}

	Returns:
		Backtest ID and status (backtest runs asynchronously in background)
	"""
	strategy = body.get("strategy")
	if not strategy:
		raise HTTPException(status_code=400, detail="strategy is required")

	start_date = body.get("start_date")
	end_date = body.get("end_date")
	portfolio_name = body.get("portfolio_name")

	# Generate backtest_id first
	from datetime import date
	import uuid
	backtest_id = f"{date.today().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

	# Prepare input data, including the backtest_id for consistency with WebSocket
	input_data = {
		"strategy": strategy,
		"backtest_id": backtest_id,  # Pass ID so it's consistent throughout the flow
	}
	if start_date:
		input_data["start_date"] = start_date
	if end_date:
		input_data["end_date"] = end_date
	if portfolio_name:
		input_data["portfolio_name"] = portfolio_name

	# Run backtest in background thread (non-blocking)
	def run_backtest_bg():
		try:
			flow = BacktestFlow()
			flow.process(input_data)
		except Exception as e:
			import logging
			logger = logging.getLogger(__name__)
			logger.error(f"Backtest {backtest_id} failed: {str(e)}", exc_info=True)

	thread = threading.Thread(target=run_backtest_bg, daemon=True)
	thread.start()

	# Return immediately with backtest_id so frontend can connect to WebSocket
	return {
		"status": "success",
		"message": f"Backtest {backtest_id} started",
		"backtest_id": backtest_id,
		"strategy_name": strategy,
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
