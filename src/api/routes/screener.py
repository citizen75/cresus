"""Screener management API routes."""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
import json

from tools.screener import ScreenerManager, ScreenerConfig
from agents.screener.agent import ScreenerAgent

router = APIRouter(tags=["screener"])


@router.get("/screener/screeners")
async def list_screeners():
	"""List all screeners."""
	try:
		manager = ScreenerManager()
		screener_names = manager.list_screeners()

		# Get full details for each screener
		screeners = []
		for name in screener_names:
			screener = manager.get_screener(name)
			if screener:
				screeners.append(screener.to_dict())

		return {
			"status": "success",
			"screeners": screeners,
			"total": len(screeners),
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/screeners/{name}")
async def get_screener(name: str):
	"""Get screener configuration."""
	try:
		manager = ScreenerManager()
		screener = manager.get_screener(name)

		if not screener:
			raise HTTPException(status_code=404, detail=f"Screener '{name}' not found")

		return {
			"status": "success",
			"screener": screener.to_dict(),
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/screener/screeners")
async def create_screener(
	name: str,
	source: Optional[str] = None,
	tickers: Optional[str] = None,
	indicators: Optional[str] = None,
	formula: Optional[str] = None,
	description: str = "",
):
	"""Create a new screener."""
	try:
		# Parse JSON arrays if provided
		tickers_list = []
		if tickers:
			try:
				tickers_list = json.loads(tickers)
			except json.JSONDecodeError:
				raise HTTPException(status_code=400, detail="Invalid JSON in tickers")

		indicators_list = []
		if indicators:
			try:
				indicators_list = json.loads(indicators)
			except json.JSONDecodeError:
				raise HTTPException(status_code=400, detail="Invalid JSON in indicators")

		# Set default indicators if not provided
		if not indicators_list:
			indicators_list = ["rsi_14", "ema_20", "close"]

		config = ScreenerConfig(
			name=name,
			source=source,
			tickers=tickers_list,
			indicators=indicators_list,
			formula=formula,
			description=description,
		)

		manager = ScreenerManager()
		success, message = manager.create_screener(config)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.put("/screener/screeners/{name}")
async def update_screener(
	name: str,
	source: Optional[str] = None,
	tickers: Optional[str] = None,
	indicators: Optional[str] = None,
	formula: Optional[str] = None,
	description: Optional[str] = None,
):
	"""Update a screener."""
	try:
		manager = ScreenerManager()
		existing = manager.get_screener(name)

		if not existing:
			raise HTTPException(status_code=404, detail=f"Screener '{name}' not found")

		# Parse JSON arrays if provided
		tickers_list = existing.tickers
		if tickers:
			try:
				tickers_list = json.loads(tickers)
			except json.JSONDecodeError:
				raise HTTPException(status_code=400, detail="Invalid JSON in tickers")

		indicators_list = existing.indicators
		if indicators:
			try:
				indicators_list = json.loads(indicators)
			except json.JSONDecodeError:
				raise HTTPException(status_code=400, detail="Invalid JSON in indicators")

		config = ScreenerConfig(
			name=name,
			source=source or existing.source,
			tickers=tickers_list,
			indicators=indicators_list,
			formula=formula or existing.formula,
			description=description if description is not None else existing.description,
		)

		success, message = manager.update_screener(config)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.delete("/screener/screeners/{name}")
async def delete_screener(name: str):
	"""Delete a screener."""
	try:
		manager = ScreenerManager()
		success, message = manager.delete_screener(name)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/screener/screeners/{name}/run")
async def run_screener(name: str):
	"""Run a screener."""
	try:
		manager = ScreenerManager()
		screener = manager.get_screener(name)

		if not screener:
			raise HTTPException(status_code=404, detail=f"Screener '{name}' not found")

		# Use ScreenerAgent to run the screener
		agent = ScreenerAgent()

		result = agent.process({
			"screener_name": name,
		})

		# Save result if successful
		result_id = None
		if result.get("status") == "success":
			success, message, result_id = manager.save_result(
				name,
				result.get("matches", []),
				{
					"tickers_processed": result.get("tickers_processed"),
					"tickers_skipped": result.get("tickers_skipped"),
				},
			)

			if not success:
				raise HTTPException(status_code=400, detail=message)

		return {
			"status": result.get("status"),
			"message": result.get("message"),
			"result_id": result_id,
			"matches": result.get("matches", []),
			"tickers_processed": result.get("tickers_processed", 0),
			"tickers_skipped": result.get("tickers_skipped", 0),
			"match_count": result.get("match_count", 0),
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/screeners/{name}/results")
async def list_screener_results(name: str):
	"""List results for a screener."""
	try:
		manager = ScreenerManager()
		results = manager.list_results(name)

		return {
			"status": "success",
			"results": [
				{
					"result_id": result_id,
					"timestamp": timestamp.isoformat(),
				}
				for result_id, timestamp in results
			],
			"total": len(results),
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/screeners/{name}/results/{result_id}")
async def get_screener_result(name: str, result_id: str):
	"""Get screener result data."""
	try:
		manager = ScreenerManager()
		data = manager.get_result(name, result_id)

		if data is None:
			raise HTTPException(status_code=404, detail=f"Result '{result_id}' not found")

		return {
			"status": "success",
			"data": data,
			"total": len(data),
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.delete("/screener/screeners/{name}/results/{result_id}")
async def delete_screener_result(name: str, result_id: str):
	"""Delete a specific screener result."""
	try:
		manager = ScreenerManager()
		success, message = manager.delete_result(name, result_id)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/screener/screeners/{name}/results/clear")
async def clear_screener_results(name: str):
	"""Clear all results for a screener."""
	try:
		manager = ScreenerManager()
		success, message = manager.clear_results(name)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
