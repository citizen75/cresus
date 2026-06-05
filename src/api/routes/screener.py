"""Screener management API routes."""

from fastapi import APIRouter, HTTPException, Request, Body
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
		name = match.group(1)
		# Handle SHA indicators without period (e.g., sha_up -> sha_14_up)
		if name in ['sha_up', 'sha_down', 'sha_green', 'sha_red']:
			name = f"sha_14_{name.split('_')[1]}"  # Add default period 14
		indicators.add(name)

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
			# Handle SHA indicators without period (e.g., sha_up -> sha_14_up)
			if name in ['sha_up', 'sha_down', 'sha_green', 'sha_red']:
				name = f"sha_14_{name.split('_')[1]}"
			indicators.add(name)

	return sorted(list(indicators))


# Pydantic models for request bodies
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
async def create_screener(http_request: Request):
	"""Create a new screener.

	Accepts either JSON body or query parameters for flexibility.
	"""
	try:
		# Try to parse JSON body first
		request_data = None
		try:
			if http_request.headers.get("content-type", "").startswith("application/json"):
				body = await http_request.json()
				request_data = CreateScreenerRequest(**body)
		except:
			pass

		# Fall back to query parameters
		if request_data:
			screener_name = request_data.name
			screener_source = request_data.source
			screener_tickers = request_data.tickers
			screener_indicators = request_data.indicators
			screener_formula = request_data.formula
			screener_description = request_data.description
		else:
			# Parse from query parameters
			query_params = http_request.query_params
			screener_name = query_params.get("name")
			screener_source = query_params.get("source")
			screener_formula = query_params.get("formula")
			screener_description = query_params.get("description", "")

			# Parse tickers (can be JSON array or comma-separated)
			screener_tickers = None
			tickers_param = query_params.get("tickers")
			if tickers_param:
				try:
					screener_tickers = json.loads(tickers_param) if tickers_param.startswith('[') else tickers_param.split(',')
				except:
					screener_tickers = tickers_param.split(',')

			# Parse indicators (can be JSON array or comma-separated)
			screener_indicators = None
			indicators_param = query_params.get("indicators")
			if indicators_param:
				try:
					screener_indicators = json.loads(indicators_param) if indicators_param.startswith('[') else indicators_param.split(',')
				except:
					screener_indicators = indicators_param.split(',')

		if not screener_name:
			raise HTTPException(status_code=400, detail="Name is required")

		# Auto-extract indicators from formula if provided, otherwise use defaults
		indicators_list = screener_indicators if screener_indicators else []
		if not indicators_list:
			if screener_formula:
				indicators_list = extract_indicators_from_formula(screener_formula)
			else:
				indicators_list = ["rsi_14", "ema_20", "close"]

		config = ScreenerConfig(
			name=screener_name,
			source=screener_source,
			tickers=screener_tickers,
			indicators=indicators_list,
			formula=screener_formula,
			description=screener_description,
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
async def update_screener(name: str, http_request: Request):
	"""Update a screener.

	Accepts either JSON body or query parameters for flexibility.
	"""
	try:
		manager = ScreenerManager()
		existing = manager.get_screener(name)

		if not existing:
			raise HTTPException(status_code=404, detail=f"Screener '{name}' not found")

		# Try to parse JSON body first
		request_data = None
		try:
			if http_request.headers.get("content-type", "").startswith("application/json"):
				body = await http_request.json()
				request_data = UpdateScreenerRequest(**body)
		except:
			pass

		# Fall back to query parameters
		if request_data:
			update_source = request_data.source
			update_tickers = request_data.tickers
			update_indicators = request_data.indicators
			update_formula = request_data.formula
			update_description = request_data.description
		else:
			# Parse from query parameters
			query_params = http_request.query_params
			update_source = query_params.get("source")
			update_formula = query_params.get("formula")
			update_description = query_params.get("description")

			# Parse tickers (can be JSON array or comma-separated)
			update_tickers = None
			tickers_param = query_params.get("tickers")
			if tickers_param:
				try:
					update_tickers = json.loads(tickers_param) if tickers_param.startswith('[') else tickers_param.split(',')
				except:
					update_tickers = tickers_param.split(',')

			# Parse indicators (can be JSON array or comma-separated)
			update_indicators = None
			indicators_param = query_params.get("indicators")
			if indicators_param:
				try:
					update_indicators = json.loads(indicators_param) if indicators_param.startswith('[') else indicators_param.split(',')
				except:
					update_indicators = indicators_param.split(',')

		# Use provided values or keep existing ones
		tickers_list = update_tickers if update_tickers is not None else existing.tickers

		# Auto-extract indicators from formula if formula is being updated
		final_formula = update_formula or existing.formula
		if update_formula:
			# Formula is being updated, auto-extract indicators
			indicators_list = extract_indicators_from_formula(update_formula)
		else:
			# Formula not being updated, use provided indicators or existing ones
			indicators_list = update_indicators if update_indicators else existing.indicators

		config = ScreenerConfig(
			name=name,
			source=update_source or existing.source,
			tickers=tickers_list,
			indicators=indicators_list,
			formula=final_formula,
			description=update_description if update_description is not None else existing.description,
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
	import asyncio

	try:
		manager = ScreenerManager()
		screener = manager.get_screener(name)

		if not screener:
			raise HTTPException(status_code=404, detail=f"Screener '{name}' not found")

		# Use ScreenerAgent to run the screener in a thread pool
		# to avoid blocking the async event loop
		agent = ScreenerAgent()

		def run_blocking():
			return agent.process({
				"screener_name": name,
			})

		result = await asyncio.to_thread(run_blocking)

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


@router.post("/screener/builder")
async def screener_builder(http_request: Request):
	"""Screener builder - evaluate a formula against a universe and return live preview results.

	Accepts either JSON body or query parameters:
		formula: DSL formula string (e.g., "sha_10_green[0] && rsi_14 > 50")
		source: Universe source (e.g., "nasdaq_100", "cac40")
		tickers: Optional array of specific tickers to screen
		limit: Max tickers to process for preview (default 50 for speed)

	Returns:
		Dict with:
			status: "success" or "error"
			indicators: List of indicators extracted from formula
			matches: List of matching rows (up to 100)
			match_count: Total number of matches
			message: Status message
	"""
	try:
		# Try to parse JSON body first
		request_data = None
		try:
			if http_request.headers.get("content-type", "").startswith("application/json"):
				body = await http_request.json()
				request_data = ScreenerRequest(**body)
		except:
			pass

		# Fall back to query parameters
		if request_data:
			formula = request_data.formula
			source = request_data.source
			tickers = request_data.tickers
			limit = request_data.limit
		else:
			query_params = http_request.query_params
			formula = query_params.get("formula")
			source = query_params.get("source")
			tickers = query_params.get("tickers")
			limit = int(query_params.get("limit", 0))

			# Parse tickers if provided
			if tickers and isinstance(tickers, str):
				try:
					tickers = json.loads(tickers) if tickers.startswith('[') else tickers.split(',')
				except:
					tickers = tickers.split(',')

		if not formula or not formula.strip():
			raise HTTPException(status_code=400, detail="Formula is required")

		# Extract indicators from formula
		indicators = extract_indicators_from_formula(formula)

		# Validate source or tickers
		if not source and not tickers:
			raise HTTPException(status_code=400, detail="Either source or tickers is required")

		# Import screening dependencies
		from core.context import AgentContext

		# Create screener config
		screener_config = ScreenerConfig(
			name="_api_preview",
			source=source,
			tickers=tickers,
			indicators=indicators,
			formula=formula,
			description="API preview screener"
		)

		# Create context and run ScreenerAgent in thread pool
		import asyncio
		context = AgentContext()
		agent = ScreenerAgent("ScreenerAgent", context)

		# Pass use_cached_data=False for API to load fresh data (bypasses context cache)
		# Use limit parameter for faster preview results
		def run_blocking():
			return agent.process({
				"screener_config": screener_config,
				"use_cached_data": False,
				"max_tickers": limit,
			})

		result = await asyncio.to_thread(run_blocking)

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
	except ValueError as e:
		# DSL parsing or evaluation errors
		error_msg = str(e)
		if "Vectorized evaluation failed" in error_msg or "DSL" in error_msg:
			raise HTTPException(
				status_code=400,
				detail=f"Formula error: {error_msg}"
			)
		raise HTTPException(status_code=400, detail=error_msg)
	except Exception as e:
		# Check if it's a DSL-related error
		error_msg = str(e)
		if "Vectorized" in error_msg or "formula" in error_msg.lower() or "indicator" in error_msg.lower():
			raise HTTPException(
				status_code=400,
				detail=f"Formula evaluation error: {error_msg}"
			)
		raise HTTPException(status_code=500, detail=f"Server error: {error_msg}")
