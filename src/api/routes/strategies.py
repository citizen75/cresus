"""Strategy API endpoints."""

from fastapi import APIRouter, HTTPException
from functools import lru_cache
from typing import Dict, Any
import os
from pathlib import Path
import yaml


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
