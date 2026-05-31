"""Screener management API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
import re
import pandas as pd

from tools.screener import ScreenerManager, ScreenerConfig
from agents.screener.agent import ScreenerAgent

router = APIRouter(tags=["screener"])


def extract_indicators_from_formula(formula: str) -> List[str]:
	"""Extract indicator names from a DSL formula.

	Args:
		formula: DSL formula string (e.g., "sha_10_green[0] && rsi_14 > 50")

	Returns:
		List of unique indicator names found in the formula
	"""
	indicators = set()

	# Pattern 1: indicator[shift] notation
	# Matches: sha_10_green[0], ema_20[-1], rsi_14[2]
	pattern1 = r'(\w+)\[(-?\d+)\]'
	for match in re.finditer(pattern1, formula):
		indicators.add(match.group(1))

	# Pattern 2: bare indicator names (without shift notation)
	# Remove already captured indicators from formula to avoid double-matching
	formula_copy = re.sub(pattern1, '', formula)

	# Look for indicator-like names (lowercase with underscores, typically with numbers)
	# Examples: sha_10_green, ema_20, rsi_14, adx_14
	pattern2 = r'\b([a-z_][a-z0-9_]*)\b'
	for match in re.finditer(pattern2, formula_copy):
		name = match.group(1)
		# Skip logical operators, comparison operators as words, and common keywords
		skip_words = {'and', 'or', 'not', 'true', 'false', 'if', 'else'}
		# Skip OHLCV column names (these are data columns, not indicators)
		skip_columns = {'open', 'high', 'low', 'close', 'volume', 'date', 'timestamp', 'ticker', 'symbol'}
		if name not in skip_words and name not in skip_columns:
			indicators.add(name)

	return sorted(list(indicators))


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
async def create_screener(request: CreateScreenerRequest):
	"""Create a new screener."""
	try:
		# Auto-extract indicators from formula if provided, otherwise use defaults
		indicators_list = request.indicators if request.indicators else []
		if not indicators_list:
			if request.formula:
				indicators_list = extract_indicators_from_formula(request.formula)
			else:
				indicators_list = ["rsi_14", "ema_20", "close"]

		config = ScreenerConfig(
			name=request.name,
			source=request.source,
			tickers=request.tickers,
			indicators=indicators_list,
			formula=request.formula,
			description=request.description,
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
	request: UpdateScreenerRequest,
):
	"""Update a screener."""
	try:
		manager = ScreenerManager()
		existing = manager.get_screener(name)

		if not existing:
			raise HTTPException(status_code=404, detail=f"Screener '{name}' not found")

		# Use provided values or keep existing ones
		tickers_list = request.tickers if request.tickers is not None else existing.tickers

		# Auto-extract indicators from formula if formula is being updated
		final_formula = request.formula or existing.formula
		if request.formula:
			# Formula is being updated, auto-extract indicators
			indicators_list = extract_indicators_from_formula(request.formula)
		else:
			# Formula not being updated, use provided indicators or existing ones
			indicators_list = request.indicators if request.indicators else existing.indicators

		config = ScreenerConfig(
			name=name,
			source=request.source or existing.source,
			tickers=tickers_list,
			indicators=indicators_list,
			formula=final_formula,
			description=request.description if request.description is not None else existing.description,
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


class ScreenerRequest(BaseModel):
	formula: str
	source: Optional[str] = None
	tickers: Optional[List[str]] = None
	limit: int = 0


class CreateScreenerRequest(BaseModel):
	name: str
	source: Optional[str] = None
	tickers: Optional[List[str]] = None
	indicators: Optional[List[str]] = None
	formula: Optional[str] = None
	description: str = ""


class UpdateScreenerRequest(BaseModel):
	source: Optional[str] = None
	tickers: Optional[List[str]] = None
	indicators: Optional[List[str]] = None
	formula: Optional[str] = None
	description: Optional[str] = None


@router.post("/screener/builder")
async def screener_builder(request: ScreenerRequest):
	"""Screener builder - evaluate a formula against a universe and return live preview results.

	Args:
		request.formula: DSL formula string (e.g., "sha_10_green[0] && rsi_14 > 50")
		request.source: Universe source (e.g., "nasdaq_100", "cac40")
		request.tickers: Optional array of specific tickers to screen
		request.limit: Max tickers to process for preview (default 50 for speed)

	Returns:
		Dict with:
			status: "success" or "error"
			indicators: List of indicators extracted from formula
			matches: List of matching rows (up to 100)
			match_count: Total number of matches
			message: Status message
	"""
	try:
		if not request.formula or not request.formula.strip():
			raise HTTPException(status_code=400, detail="Formula is required")

		# Extract indicators from formula
		indicators = extract_indicators_from_formula(request.formula)

		# Validate source or tickers
		if not request.source and not request.tickers:
			raise HTTPException(status_code=400, detail="Either source or tickers is required")

		# Import screening dependencies
		from core.context import AgentContext

		# Create screener config
		screener_config = ScreenerConfig(
			name="_api_preview",
			source=request.source,
			tickers=request.tickers,
			indicators=indicators,
			formula=request.formula,
			description="API preview screener"
		)

		# Create context and run ScreenerAgent
		context = AgentContext()
		agent = ScreenerAgent("ScreenerAgent", context)

		# Pass use_cached_data=False for API to load fresh data (bypasses context cache)
		# Use limit parameter for faster preview results
		result = agent.process({
			"screener_config": screener_config,
			"use_cached_data": False,
			"max_tickers": request.limit,
		})

		if result.get("status") != "success":
			raise HTTPException(status_code=400, detail=result.get("message", "Screening failed"))

		return {
			"status": "success",
			"indicators": indicators,
			"matches": result.get("matches", [])[:100],  # Return first 100 matches
			"match_count": result.get("match_count", 0),
			"tickers_processed": result.get("tickers_processed", 0),
			"tickers_skipped": result.get("tickers_skipped", 0),
			"screening_date": result.get("screening_date", ""),
			"message": result.get("message", "Screening complete"),
		}

	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
