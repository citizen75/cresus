"""Strategy API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from functools import lru_cache
from typing import Dict, Any
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
	strategy_names = _list_strategy_files()
	
	strategies = []
	for name in strategy_names:
		strategy = _load_strategy(name)
		if strategy:
			strategies.append({
				"name": name,
				"description": strategy.get("description", ""),
				"universe": strategy.get("universe", ""),
				"engine": strategy.get("engine", ""),
			})
	
	return {"strategies": strategies}


@router.get("/{name}")
async def get_strategy(name: str):
	"""Get strategy configuration by name."""
	strategy = _load_strategy(name)
	
	if not strategy:
		raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
	
	return {"strategy": strategy}


@router.put("/{name}")
async def update_strategy(name: str, update: StrategyUpdate):
	"""Update strategy configuration by name.
	
	Supports partial updates - only specified fields are updated.
	Uses StrategyManager to persist changes to YAML file.
	"""
	# Load existing strategy
	strategy = _load_strategy(name)
	
	if not strategy:
		raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
	
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
		strategy_manager = StrategyManager()
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

