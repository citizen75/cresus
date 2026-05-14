"""Strategy API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from functools import lru_cache
from typing import Dict, Any, Optional
import os
from pathlib import Path
import yaml
from tools.strategy import StrategyManager


class StrategyUpdate(BaseModel):
	"""Strategy update request model."""
	entry: Dict[str, Any] = None
	exit: Dict[str, Any] = None
	watchlist: Dict[str, Any] = None
	signals: Dict[str, Any] = None
	
	class Config:
		extra = "allow"  # Allow additional fields


def _get_strategies_dir() -> Path:
	"""Get path to strategies directory."""
	project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", "."))
	return project_root / "db" / "local" / "strategies"


def _load_strategy(name: str) -> Dict[str, Any]:
	"""Load a single strategy YAML file."""
	strategies_dir = _get_strategies_dir()
	strategy_path = strategies_dir / f"{name}.yml"
	
	if not strategy_path.exists():
		return None
	
	try:
		with open(strategy_path, 'r') as f:
			strategy = yaml.safe_load(f)
		return strategy
	except Exception as e:
		print(f"Error loading strategy {name}: {e}")
		return None


def _list_strategy_files() -> list:
	"""List all available strategy files."""
	strategies_dir = _get_strategies_dir()
	
	if not strategies_dir.exists():
		return []
	
	return [f.stem for f in strategies_dir.glob("*.yml")]


router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("")
async def list_strategies():
	"""List all available strategies."""
	strategy_manager = StrategyManager()
	result = strategy_manager.list_strategies()

	if result.get("status") != "success":
		return {"strategies": []}

	return {"strategies": result.get("strategies", [])}


@router.get("/{name}")
async def get_strategy(name: str):
	"""Get strategy configuration by name."""
	strategy_manager = StrategyManager()
	result = strategy_manager.load_strategy(name)

	if result.get("status") != "success":
		raise HTTPException(status_code=404, detail=result.get("message"))

	return {"strategy": result.get("data")}


@router.put("/{name}")
async def update_strategy(name: str, update: StrategyUpdate):
	"""Update strategy configuration by name.

	Supports partial updates - only specified fields are updated.
	Uses StrategyManager to persist changes to YAML file.
	"""
	strategy_manager = StrategyManager()

	# Load existing strategy
	load_result = strategy_manager.load_strategy(name)
	if load_result.get("status") != "success":
		raise HTTPException(status_code=404, detail=load_result.get("message"))

	strategy = load_result.get("data")

	try:
		# Apply updates - merge nested objects
		if update.entry is not None:
			strategy["entry"] = {**strategy.get("entry", {}), **update.entry}

		if update.exit is not None:
			strategy["exit"] = {**strategy.get("exit", {}), **update.exit}

		if update.watchlist is not None:
			strategy["watchlist"] = {**strategy.get("watchlist", {}), **update.watchlist}

		if update.signals is not None:
			strategy["signals"] = {**strategy.get("signals", {}), **update.signals}

		# Handle any additional fields from extra="allow"
		update_dict = update.dict(exclude_none=True, exclude_unset=True)
		for key, value in update_dict.items():
			if key not in ["entry", "exit", "watchlist", "signals"]:
				strategy[key] = value

		# Use StrategyManager to save
		result = strategy_manager.save_strategy(name, strategy)

		if result.get("status") == "error":
			raise HTTPException(status_code=400, detail=result.get("message"))

		return {
			"status": "success",
			"message": f"Strategy '{name}' updated successfully",
			"changed": result.get("changed", True),
			"strategy": strategy
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to update strategy: {str(e)}")


@router.post("/{name}/duplicate")
async def duplicate_strategy(name: str, new_name: Optional[str] = Query(None)):
	"""Duplicate an existing strategy with a new name.

	Creates a copy of the strategy configuration with a new unique name.
	If new_name is not provided, generates one by appending _copy to the original name.
	"""
	strategy_manager = StrategyManager()

	# Load existing strategy
	load_result = strategy_manager.load_strategy(name)
	if load_result.get("status") != "success":
		raise HTTPException(status_code=404, detail=load_result.get("message"))

	strategy = load_result.get("data")

	try:
		# Generate new name if not provided
		if not new_name:
			base_name = name
			counter = 1
			strategies_dir = _get_strategies_dir()
			while (strategies_dir / f"{base_name}_copy_{counter}.yml").exists():
				counter += 1
			new_name = f"{base_name}_copy_{counter}"
		else:
			# Validate new name doesn't already exist
			strategies_dir = _get_strategies_dir()
			if (strategies_dir / f"{new_name}.yml").exists():
				raise HTTPException(status_code=400, detail=f"Strategy '{new_name}' already exists")

		# Save the duplicated strategy
		result = strategy_manager.save_strategy(new_name, strategy)

		if result.get("status") == "error":
			raise HTTPException(status_code=400, detail=result.get("message"))

		return {
			"status": "success",
			"message": f"Strategy duplicated successfully",
			"original_name": name,
			"new_name": new_name,
			"strategy": strategy
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to duplicate strategy: {str(e)}")


@router.delete("/{name}")
async def delete_strategy(name: str):
	"""Delete a strategy by name.

	Permanently removes the strategy YAML/JSON file.
	Uses StrategyManager to ensure correct path handling.
	"""
	strategy_manager = StrategyManager()

	# Try to load the strategy to verify it exists
	load_result = strategy_manager.load_strategy(name)
	if load_result.get("status") != "success":
		raise HTTPException(status_code=404, detail=load_result.get("message"))

	try:
		# Delete both .yml and .json files if they exist
		strategies_dir = strategy_manager.strategies_dir
		yml_path = strategies_dir / f"{name}.yml"
		json_path = strategies_dir / f"{name}.json"

		deleted = False
		if yml_path.exists():
			yml_path.unlink()
			deleted = True
		if json_path.exists():
			json_path.unlink()
			deleted = True

		if not deleted:
			raise HTTPException(status_code=404, detail=f"Strategy '{name}' file not found")

		return {
			"status": "success",
			"message": f"Strategy '{name}' deleted successfully"
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to delete strategy: {str(e)}")

