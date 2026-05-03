"""Strategy manager for reading and writing trading strategies.

Provides a StrategyManager class to:
- Load strategy by name from JSON files in db/local/strategies
- Save strategy configurations
- Extract agent configurations from strategies
- Get tickers list from strategy source
- Retrieve momentum scoring parameters from strategy
- List and validate strategies
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))


class StrategyManager:
	"""Manager for reading and writing trading strategy configurations.

	Handles persistence of strategies in db/local/strategies directory with
	automatic folder creation.
	"""

	def __init__(self, project_root: Optional[Path] = None):
		"""Initialize StrategyManager with optional project root.

		Args:
			project_root: Optional path to project root. If None, searches from current file.
		"""
		if project_root:
			self.project_root = Path(project_root)
		else:
			# Find project root by looking for config directory
			self.project_root = self._find_project_root()

		# Strategies are stored in db/local/strategies
		self.strategies_dir = self.project_root / "db" / "local" / "strategies"
		self._ensure_strategies_dir()

	def _find_project_root(self) -> Path:
		"""Find project root by walking up from this file."""
		current = Path(__file__).resolve().parent

		while current != current.parent:
			if (current / "config").exists() or (current / "db").exists():
				return current
			current = current.parent

		# Fallback to parent of src
		return Path(__file__).resolve().parent.parent.parent.parent

	def _ensure_strategies_dir(self) -> None:
		"""Create strategies directory if it doesn't exist."""
		self.strategies_dir.mkdir(parents=True, exist_ok=True)

	def _get_strategy_file(self, strategy_name: str) -> Path:
		"""Get the full path for a strategy file.

		Args:
			strategy_name: Name of the strategy

		Returns:
			Path to the strategy JSON file
		"""
		return self.strategies_dir / f"{strategy_name}.json"

	def save_strategy(self, strategy_name: str, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Save a strategy to db/local/strategies.

		Args:
			strategy_name: Name of the strategy
			strategy_data: Strategy configuration dictionary

		Returns:
			Result dictionary with status and details
		"""
		try:
			self._ensure_strategies_dir()
			strategy_file = self._get_strategy_file(strategy_name)

			# Ensure strategy_data has a name field
			if "name" not in strategy_data:
				strategy_data["name"] = strategy_name

			with open(strategy_file, "w") as f:
				json.dump(strategy_data, f, indent=2)

			return {
				"status": "success",
				"message": f"Strategy '{strategy_name}' saved successfully",
				"file": str(strategy_file),
				"size": strategy_file.stat().st_size,
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Failed to save strategy: {str(e)}",
				"error_type": type(e).__name__,
			}

	def load_strategy(self, strategy_name: str) -> Dict[str, Any]:
		"""Load strategy configuration by name.

		Args:
			strategy_name: Name of the strategy

		Returns:
			Dict with strategy configuration or error status
		"""
		try:
			strategy_file = self._get_strategy_file(strategy_name)

			if not strategy_file.exists():
				return {
					"status": "error",
					"message": f"Strategy '{strategy_name}' not found at {strategy_file}",
					"error_type": "FileNotFoundError",
				}

			with open(strategy_file, "r") as f:
				strategy_data = json.load(f)

			return {
				"status": "success",
				"data": strategy_data,
				"name": strategy_data.get("name"),
				"description": strategy_data.get("description"),
				"source": strategy_data.get("source"),
				"file": str(strategy_file),
			}
		except json.JSONDecodeError as e:
			return {
				"status": "error",
				"message": f"JSON parsing error: {str(e)}",
				"error_type": "JSONError",
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Failed to load strategy: {str(e)}",
				"error_type": type(e).__name__,
			}

	def delete_strategy(self, strategy_name: str) -> Dict[str, Any]:
		"""Delete a strategy file.

		Args:
			strategy_name: Name of the strategy to delete

		Returns:
			Result dictionary with status
		"""
		try:
			strategy_file = self._get_strategy_file(strategy_name)

			if not strategy_file.exists():
				return {
					"status": "error",
					"message": f"Strategy '{strategy_name}' not found",
					"error_type": "FileNotFoundError",
				}

			strategy_file.unlink()

			return {
				"status": "success",
				"message": f"Strategy '{strategy_name}' deleted successfully",
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Failed to delete strategy: {str(e)}",
				"error_type": type(e).__name__,
			}

	def list_strategies(self) -> Dict[str, Any]:
		"""List all available strategies.

		Returns:
			Dict with list of strategy names and metadata
		"""
		try:
			strategies_info = []

			if not self.strategies_dir.exists():
				return {
					"status": "success",
					"strategies": [],
					"total_count": 0,
					"directory": str(self.strategies_dir),
				}

			for strategy_file in sorted(self.strategies_dir.glob("*.json")):
				try:
					with open(strategy_file, "r") as f:
						strategy_data = json.load(f)

					strategies_info.append({
						"name": strategy_data.get("name"),
						"description": strategy_data.get("description", "No description"),
						"source": strategy_data.get("source"),
						"file": strategy_file.name,
						"modified": strategy_file.stat().st_mtime,
					})
				except Exception:
					# Skip files that can't be parsed
					continue

			return {
				"status": "success",
				"strategies": strategies_info,
				"total_count": len(strategies_info),
				"directory": str(self.strategies_dir),
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Failed to list strategies: {str(e)}",
				"error_type": type(e).__name__,
			}

	def get_strategy_by_source(self, source_name: str) -> Dict[str, Any]:
		"""Get all strategies filtered by data source.

		Args:
			source_name: Source name (e.g., 'cac40')

		Returns:
			Dict with list of strategies for this source
		"""
		try:
			strategies_info = []

			if not self.strategies_dir.exists():
				return {
					"status": "success",
					"source": source_name,
					"strategies": [],
					"total_count": 0,
				}

			for strategy_file in sorted(self.strategies_dir.glob("*.json")):
				try:
					with open(strategy_file, "r") as f:
						strategy_data = json.load(f)

					if strategy_data.get("source") == source_name:
						strategies_info.append({
							"name": strategy_data.get("name"),
							"description": strategy_data.get("description", "No description"),
							"source": source_name,
							"file": strategy_file.name,
						})
				except Exception:
					continue

			return {
				"status": "success",
				"source": source_name,
				"strategies": strategies_info,
				"total_count": len(strategies_info),
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Failed to get strategies by source: {str(e)}",
				"error_type": type(e).__name__,
			}

	def find_strategy_by_name(self, strategy_name: str) -> Dict[str, Any]:
		"""Find and load a strategy by its name.

		Args:
			strategy_name: Strategy name to find

		Returns:
			Dict with strategy data or error status
		"""
		return self.load_strategy(strategy_name)

	def get_agent_config(self, strategy_name: str, agent_name: str) -> Dict[str, Any]:
		"""Extract specific agent configuration from strategy.

		Args:
			strategy_name: Strategy name
			agent_name: Agent name

		Returns:
			Dict with agent configuration or error status
		"""
		try:
			result = self.load_strategy(strategy_name)

			if result["status"] != "success":
				return result

			strategy_data = result["data"]

			if "agents" not in strategy_data:
				return {
					"status": "error",
					"message": f"No agents section in strategy '{strategy_name}'",
					"error_type": "NotFound",
				}

			agents_config = strategy_data["agents"]

			if agent_name not in agents_config:
				available = list(agents_config.keys())
				return {
					"status": "error",
					"message": f"Agent '{agent_name}' not found in strategy",
					"error_type": "NotFound",
					"available_agents": available,
				}

			return {
				"status": "success",
				"config": agents_config[agent_name],
				"strategy": strategy_name,
				"agent": agent_name,
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Failed to get agent config: {str(e)}",
				"error_type": type(e).__name__,
			}

	def validate_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
		"""Validate strategy configuration completeness.

		Args:
			strategy_name: Strategy name to validate

		Returns:
			Dict with validation results
		"""
		try:
			result = self.load_strategy(strategy_name)

			if result["status"] != "success":
				return {
					"status": "error",
					"message": f"Strategy not found: {strategy_name}",
					"valid": False,
				}

			strategy_data = result["data"]
			issues = []

			if not strategy_data.get("name"):
				issues.append("Missing strategy name")

			if not strategy_data.get("source"):
				issues.append("Missing source")

			if not strategy_data.get("agents"):
				issues.append("Missing agents section")

			valid = len(issues) == 0

			return {
				"status": "success",
				"strategy": strategy_name,
				"valid": valid,
				"issues": issues,
				"issue_count": len(issues),
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Validation failed: {str(e)}",
				"error_type": type(e).__name__,
				"valid": False,
			}


def load_strategy(strategy_name: str) -> Dict[str, Any]:
    """
    Load strategy configuration by name from YAML file.

    Args:
        strategy_name: Name of the strategy (e.g., 'flow_cac_1')

    Returns:
        Dict with strategy configuration or error status

    Examples:
        >>> result = load_strategy('flow_cac_1')
        >>> print(result['status'])
        'success'
        >>> print(result['data']['name'])
        'flow_cac_1'
    """
    try:
        # Try to load from config/strategies/{strategy_name}.yml
        strategy_file = STRATEGIES_PATH / f"{strategy_name}.yml"

        if not strategy_file.exists():
            return {
                "status": "error",
                "message": f"Strategy '{strategy_name}' not found at {strategy_file}",
                "error_type": "FileNotFoundError",
            }

        with open(strategy_file, "r") as f:
            config_dict = yaml.safe_load(f) or {}

        # Extract strategy from strategies list
        strategies = config_dict.get("strategies", [])
        if not strategies:
            return {
                "status": "error",
                "message": f"No strategies found in {strategy_file}",
                "error_type": "NotFound",
            }

        # Get first strategy (usually there's only one per file)
        strategy_data = strategies[0]

        return {
            "status": "success",
            "data": strategy_data,
            "name": strategy_data.get("name"),
            "description": strategy_data.get("description"),
            "source": strategy_data.get("data", {}).get("source"),
        }

    except yaml.YAMLError as e:
        return {
            "status": "error",
            "message": f"YAML parsing error: {str(e)}",
            "error_type": "YAMLError",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load strategy: {str(e)}",
            "error_type": type(e).__name__,
        }


def get_tickers_from_source(source_name: str) -> Dict[str, Any]:
    """
    Get tickers list from strategy data source.

    Note: Tickers are fetched from ListExchange source, not stored directly in YAML.
    Currently returns source reference; actual tickers would come from ListExchange service.

    Args:
        source_name: Source name (e.g., 'cac40')

    Returns:
        Dict with source info or error status

    Examples:
        >>> result = get_tickers_from_source('cac40')
        >>> print(result['source'])
        'cac40'
    """
    try:
        # Find first strategy with this source
        for strategy_file in STRATEGIES_PATH.glob("*.yml"):
            with open(strategy_file, "r") as f:
                config_dict = yaml.safe_load(f) or {}

            strategies = config_dict.get("strategies", [])
            for strategy_data in strategies:
                if strategy_data.get("data", {}).get("source") == source_name:
                    return {
                        "status": "success",
                        "source": source_name,
                        "strategy_name": strategy_data.get("name"),
                        "note": "Tickers are fetched from ListExchange service, not stored in strategy YAML",
                        "tickers": [],
                        "tickers_count": 0,
                    }

        return {
            "status": "error",
            "message": f"No strategies found for source '{source_name}'",
            "error_type": "NotFound",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get tickers: {str(e)}",
            "error_type": type(e).__name__,
        }


def get_agent_config(
    strategy_name: str, agent_name: str
) -> Dict[str, Any]:
    """
    Extract specific agent configuration from strategy.

    Args:
        strategy_name: Strategy name (e.g., 'flow_cac_1')
        agent_name: Agent name (e.g., 'MomentumScoringAgent')

    Returns:
        Dict with agent configuration or error status

    Examples:
        >>> result = get_agent_config('flow_cac_1', 'MomentumScoringAgent')
        >>> print(result['config']['windows'])
        {'short_term_days': 5, 'mid_term_days': 15, ...}
    """
    try:
        strategy_result = load_strategy(strategy_name)

        if strategy_result["status"] != "success":
            return strategy_result

        strategy_data = strategy_result["data"]

        # Look for agent config in strategy
        if "agents" not in strategy_data:
            return {
                "status": "error",
                "message": f"No agents section in strategy '{strategy_name}'",
                "error_type": "NotFound",
            }

        agents_config = strategy_data["agents"]

        if agent_name not in agents_config:
            available = list(agents_config.keys())
            return {
                "status": "error",
                "message": (
                    f"Agent '{agent_name}' not found in strategy. "
                    f"Available: {available}"
                ),
                "error_type": "NotFound",
                "available_agents": available,
            }

        agent_config = agents_config[agent_name]

        return {
            "status": "success",
            "config": agent_config,
            "strategy": strategy_name,
            "agent": agent_name,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get agent config: {str(e)}",
            "error_type": type(e).__name__,
        }


def _load_tickers_from_source(source_name: str) -> List[str]:
    """
    Load ticker list from source file.

    Args:
        source_name: Source name (e.g., 'cac40', 'dax', 'crypto')

    Returns:
        List of ticker symbols

    Examples:
        >>> tickers = _load_tickers_from_source('cac40')
        >>> print(tickers[:3])
        ['AC.PA', 'ALO.PA', 'BNP.PA']
    """
    try:
        # Walk up the directory tree to find the config directory
        current = Path(__file__).resolve().parent
        while current != current.parent:
            config_path = current / "config"
            
            # Try workspace location first
            workspace_path = config_path / "workspace" / "finance" / "tickers" / f"{source_name}.json"
            if workspace_path.exists():
                with open(workspace_path, "r") as f:
                    data = yaml.safe_load(f)
                    return data.get("tickers", [])
            
            # Try legacy location
            legacy_path = config_path / "tickers" / f"{source_name}.json"
            if legacy_path.exists():
                with open(legacy_path, "r") as f:
                    data = yaml.safe_load(f)
                    return data.get("tickers", [])
            
            current = current.parent
        
        # Fallback: try from project root
        fallback_workspace = Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "workspace" / "finance" / "tickers" / f"{source_name}.json"
        if fallback_workspace.exists():
            with open(fallback_workspace, "r") as f:
                data = yaml.safe_load(f)
                return data.get("tickers", [])
        
        return []

    except Exception as e:
        return []


def get_momentum_config(strategy_name: str) -> Dict[str, Any]:
    """
    Extract MomentumScoringAgent parameters from strategy.

    Args:
        strategy_name: Strategy name

    Returns:
        Dict with momentum scoring configuration

    Examples:
        >>> result = get_momentum_config('flow_cac_1')
        >>> print(result['parameters']['windows']['short_term_days'])
        5
    """
    try:
        agent_result = get_agent_config(strategy_name, "MomentumScoringAgent")

        if agent_result["status"] != "success":
            return agent_result

        agent_config = agent_result["config"]

        # Extract momentum parameters if embedded
        # Format: Either direct parameters or nested under 'parameters'
        if isinstance(agent_config, dict):
            if "parameters" in agent_config:
                parameters = agent_config["parameters"]
            else:
                # Use entire agent config as parameters
                parameters = agent_config
        else:
            parameters = agent_config

        # Merge with strategy metadata
        strategy_result = load_strategy(strategy_name)
        strategy_data = strategy_result.get("data", {})

        # Load tickers from source if needed
        tickers_config = strategy_data.get("tickers", {})
        if isinstance(tickers_config, dict) and "source" in tickers_config:
            # Load from source file
            source_name = tickers_config["source"]
            tickers = _load_tickers_from_source(source_name)
        else:
            # Use direct list if provided
            tickers = tickers_config if isinstance(tickers_config, list) else []

        return {
            "status": "success",
            "strategy_name": strategy_name,
            "parameters": parameters,
            "data": {
                "tickers": tickers,
                "windows": parameters.get("windows", {}),
                "weights": parameters.get("weights", {}),
                "regime_adjustments": parameters.get("regime_adjustments", {}),
                "normalization": parameters.get("normalization", {}),
            },
            "metadata": {
                "strategy_id": strategy_name,
                "agent": "MomentumScoringAgent",
                "version": parameters.get("version", "1.0"),
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get momentum config: {str(e)}",
            "error_type": type(e).__name__,
        }


def list_strategies() -> Dict[str, Any]:
    """
    List all available strategies from config/strategies/ directory.

    Returns:
        Dict with list of strategy names and metadata

    Examples:
        >>> result = list_strategies()
        >>> print(result['strategies'])
        [{'name': 'flow_cac_1', 'description': '...', 'source': 'cac40'}, ...]
    """
    try:
        strategies_info = []

        # Scan config/strategies/ directory for YAML files
        for strategy_file in sorted(STRATEGIES_PATH.glob("*.yml")):
            try:
                with open(strategy_file, "r") as f:
                    config_dict = yaml.safe_load(f) or {}

                strategies = config_dict.get("strategies", [])
                for strategy_data in strategies:
                    strategies_info.append(
                        {
                            "name": strategy_data.get("name"),
                            "description": strategy_data.get("description", "No description"),
                            "source": strategy_data.get("data", {}).get("source"),
                            "file": strategy_file.name,
                        }
                    )
            except Exception as e:
                # Skip files that can't be parsed
                continue

        return {
            "status": "success",
            "strategies": strategies_info,
            "total_count": len(strategies_info),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list strategies: {str(e)}",
            "error_type": type(e).__name__,
        }


def get_strategy_by_source(source_name: str) -> Dict[str, Any]:
    """
    Get all strategies filtered by data source.

    Args:
        source_name: Source name (e.g., 'cac40')

    Returns:
        Dict with list of strategies for this source

    Examples:
        >>> result = get_strategy_by_source('cac40')
        >>> print(result['strategies'])
        [{'name': 'flow_cac_1', ...}, ...]
    """
    try:
        strategies_info = []

        # Scan config/strategies/ directory for YAML files
        for strategy_file in sorted(STRATEGIES_PATH.glob("*.yml")):
            try:
                with open(strategy_file, "r") as f:
                    config_dict = yaml.safe_load(f) or {}

                strategies = config_dict.get("strategies", [])
                for strategy_data in strategies:
                    if strategy_data.get("data", {}).get("source") == source_name:
                        strategies_info.append(
                            {
                                "name": strategy_data.get("name"),
                                "description": strategy_data.get("description", "No description"),
                                "source": source_name,
                                "has_momentum_config": "MomentumScoringAgent"
                                in (strategy_data.get("agents", {})),
                                "file": strategy_file.name,
                            }
                        )
            except Exception as e:
                # Skip files that can't be parsed
                continue

        return {
            "status": "success",
            "source": source_name,
            "strategies": strategies_info,
            "total_count": len(strategies_info),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get strategies by source: {str(e)}",
            "error_type": type(e).__name__,
        }


def find_strategy_by_name(strategy_name: str) -> Dict[str, Any]:
    """
    Find and load a strategy by its internal name.

    Searches through all YAML files to find a strategy with the given name.
    Handles cases where strategy name != filename (e.g., strategy name "momentum"
    is in file "momentum_cac.yml").

    Args:
        strategy_name: Strategy name to find (internal name, not filename)

    Returns:
        Dict with strategy data or error status

    Examples:
        >>> result = find_strategy_by_name('momentum')
        >>> print(result['status'])
        'success'
        >>> print(result['data']['name'])
        'momentum'
    """
    try:
        # Search through all strategy files
        for strategy_file in STRATEGIES_PATH.glob("*.yml"):
            try:
                with open(strategy_file, "r") as f:
                    config_dict = yaml.safe_load(f) or {}

                strategies = config_dict.get("strategies", [])
                for strategy_data in strategies:
                    if strategy_data.get("name") == strategy_name:
                        return {
                            "status": "success",
                            "data": strategy_data,
                            "name": strategy_data.get("name"),
                            "description": strategy_data.get("description"),
                            "source": strategy_data.get("data", {}).get("source"),
                            "file": strategy_file.name,
                        }
            except Exception as e:
                # Skip files that can't be parsed
                continue

        # Not found
        return {
            "status": "error",
            "message": f"Strategy '{strategy_name}' not found",
            "error_type": "NotFound",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to find strategy: {str(e)}",
            "error_type": type(e).__name__,
        }


def validate_strategy_config(strategy_name: str) -> Dict[str, Any]:
    """
    Validate strategy configuration completeness.

    Args:
        strategy_name: Strategy name to validate

    Returns:
        Dict with validation results

    Examples:
        >>> result = validate_strategy_config('flow_cac_1')
        >>> print(result['valid'])
        True
    """
    try:
        result = load_strategy(strategy_name)

        if result["status"] != "success":
            return {
                "status": "error",
                "message": f"Strategy not found: {strategy_name}",
                "valid": False,
            }

        strategy_data = result["data"]

        # Validation checks
        issues = []

        if not strategy_data.get("name"):
            issues.append("Missing strategy name")

        if not strategy_data.get("data"):
            issues.append("Missing data section")
        else:
            data = strategy_data.get("data", {})
            if not data.get("source"):
                issues.append("Missing data.source (tickers source)")
            if not data.get("indicators"):
                issues.append("Missing data.indicators")

        if not strategy_data.get("agents"):
            issues.append("Missing agents section")
        else:
            agents = strategy_data.get("agents", {})
            if "MomentumScoringAgent" not in agents:
                issues.append("MomentumScoringAgent not configured")

        valid = len(issues) == 0

        return {
            "status": "success",
            "strategy": strategy_name,
            "valid": valid,
            "issues": issues,
            "issue_count": len(issues),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Validation failed: {str(e)}",
            "error_type": type(e).__name__,
            "valid": False,
        }
