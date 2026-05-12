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
			# For explicit project_root (e.g., tests), use db/local/strategies for backward compatibility
			self.strategies_dir = self.project_root / "db" / "local" / "strategies"
		else:
			# Find project root by looking for config directory
			self.project_root = self._find_project_root()
			# For normal operation, use ~/.cresus/db/strategies
			from utils.env import get_db_root
			db_root = get_db_root()
			self.strategies_dir = db_root / "strategies"

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

		Looks for YAML file first, then falls back to JSON.

		Args:
			strategy_name: Name of the strategy

		Returns:
			Path to the strategy file (YAML or JSON)
		"""
		yaml_file = self.strategies_dir / f"{strategy_name}.yml"
		if yaml_file.exists():
			return yaml_file

		json_file = self.strategies_dir / f"{strategy_name}.json"
		if json_file.exists():
			return json_file

		# Return YAML path by default (for new files)
		return yaml_file

	def save_strategy(self, strategy_name: str, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Save a strategy to db/local/strategies only if changed.

		Saves as YAML if file exists as .yml, otherwise defaults to YAML format.
		Only saves if the configuration has changed.

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

			# Check if file exists and compare with existing content
			if strategy_file.exists():
				# Load existing strategy
				with open(strategy_file, "r") as f:
					if strategy_file.suffix.lower() == ".yml":
						existing_data = yaml.safe_load(f)
					else:
						existing_data = json.load(f)

				# Compare: if no changes, return without saving
				if existing_data == strategy_data:
					return {
						"status": "success",
						"message": f"Strategy '{strategy_name}' unchanged, no save needed",
						"file": str(strategy_file),
						"changed": False,
					}

			# Save as YAML (there are changes or file doesn't exist)
			with open(strategy_file, "w") as f:
				yaml.dump(strategy_data, f, default_flow_style=False, sort_keys=False)

			return {
				"status": "success",
				"message": f"Strategy '{strategy_name}' saved successfully",
				"file": str(strategy_file),
				"size": strategy_file.stat().st_size,
				"changed": True,
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Failed to save strategy: {str(e)}",
				"error_type": type(e).__name__,
			}

	def load_strategy(self, strategy_name: str) -> Dict[str, Any]:
		"""Load strategy configuration by name.

		Supports both YAML and JSON file formats.

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
					"message": f"Strategy '{strategy_name}' not found",
					"error_type": "FileNotFoundError",
				}

			with open(strategy_file, "r") as f:
				# Load YAML or JSON based on file extension
				if strategy_file.suffix.lower() == ".yml":
					strategy_data = yaml.safe_load(f)
				else:
					strategy_data = json.load(f)

			return {
				"status": "success",
				"data": strategy_data,
				"name": strategy_data.get("name"),
				"description": strategy_data.get("description"),
				"source": strategy_data.get("source"),
				"file": str(strategy_file),
			}
		except (json.JSONDecodeError, yaml.YAMLError) as e:
			return {
				"status": "error",
				"message": f"File parsing error: {str(e)}",
				"error_type": type(e).__name__,
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

		Supports both YAML and JSON file formats.

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

			# Get both YAML and JSON strategy files
			strategy_files = sorted(
				list(self.strategies_dir.glob("*.yml")) +
				list(self.strategies_dir.glob("*.json"))
			)

			for strategy_file in strategy_files:
				try:
					with open(strategy_file, "r") as f:
						# Load YAML or JSON based on file extension
						if strategy_file.suffix.lower() == ".yml":
							strategy_data = yaml.safe_load(f)
						else:
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

		Supports both YAML and JSON file formats.

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

			# Get both YAML and JSON strategy files
			strategy_files = sorted(
				list(self.strategies_dir.glob("*.yml")) +
				list(self.strategies_dir.glob("*.json"))
			)

			for strategy_file in strategy_files:
				try:
					with open(strategy_file, "r") as f:
						# Load YAML or JSON based on file extension
						if strategy_file.suffix.lower() == ".yml":
							strategy_data = yaml.safe_load(f)
						else:
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
		"""Validate strategy configuration against template schema.

		Args:
			strategy_name: Strategy name to validate

		Returns:
			Dict with validation results including issues and required fixes
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
			required_fields = []
			optional_fields = []

			# Required top-level fields
			required = ["name", "universe", "description", "engine", "indicators"]
			for field in required:
				if not strategy_data.get(field):
					issues.append(f"Missing required field: {field}")
					required_fields.append(field)

			# Validate sections
			sections = {
				"watchlist": ["enabled", "parameters"],
				"signals": ["enabled", "weights", "parameters"],
				"entry": ["enabled", "parameters"],
				"order": ["enabled", "parameters"],
				"exit": ["enabled", "parameters"],
				"backtest": ["initial_capital"],
			}

			for section, required_keys in sections.items():
				if section not in strategy_data:
					issues.append(f"Missing section: {section}")
				else:
					section_data = strategy_data[section]
					for key in required_keys:
						if key not in section_data:
							issues.append(f"Missing {section}.{key}")

			# Validate entry.parameters has required sub-keys
			if "entry" in strategy_data and "parameters" in strategy_data["entry"]:
				entry_params = strategy_data["entry"]["parameters"]
				if "position_size" not in entry_params:
					issues.append("Missing entry.parameters.position_size")

			# Validate order.parameters has required sub-keys
			if "order" in strategy_data and "parameters" in strategy_data["order"]:
				order_params = strategy_data["order"]["parameters"]
				if "position_sizing" not in order_params:
					issues.append("Missing order.parameters.position_sizing")

			# Validate exit.parameters has required sub-keys
			if "exit" in strategy_data and "parameters" in strategy_data["exit"]:
				exit_params = strategy_data["exit"]["parameters"]
				if "stop_loss" not in exit_params:
					issues.append("Missing exit.parameters.stop_loss (required for risk management)")
				if "holding_period" not in exit_params:
					issues.append("Missing exit.parameters.holding_period")

			valid = len(issues) == 0

			return {
				"status": "success",
				"strategy": strategy_name,
				"valid": valid,
				"issues": issues,
				"issue_count": len(issues),
				"required_fields": required_fields,
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Validation failed: {str(e)}",
				"error_type": type(e).__name__,
				"valid": False,
			}

	def check_strategy(self, strategy_name: str) -> Dict[str, Any]:
		"""Check strategy compliance with template and identify issues.

		Args:
			strategy_name: Strategy name to check

		Returns:
			Dict with detailed compliance report
		"""
		validation = self.validate_strategy_config(strategy_name)
		return validation

	def fix_strategy(self, strategy_name: str, dry_run: bool = False) -> Dict[str, Any]:
		"""Fix strategy configuration by adding missing fields and fixing issues.

		Adds missing required fields with default values and comments invalid keys.

		Args:
			strategy_name: Strategy name to fix
			dry_run: If True, don't save changes, just show what would be fixed

		Returns:
			Dict with fix results
		"""
		try:
			result = self.load_strategy(strategy_name)
			if result["status"] != "success":
				return {
					"status": "error",
					"message": f"Strategy not found: {strategy_name}",
				}

			strategy_data = result["data"].copy()
			changes = []

			# Template structure for default values
			template = self._load_template()

			# Identify invalid top-level keys
			valid_top_keys = set(template.keys())
			invalid_keys = []
			invalid_nested_keys = {}  # Track invalid nested keys

			# Track top-level keys from strategy not in template
			for key in strategy_data.keys():
				if key not in valid_top_keys and not key.startswith("_") and not key.startswith("#"):
					invalid_keys.append(key)
					changes.append(f"Commented invalid key: {key}")

			# Build clean_data strictly following template key order
			clean_data = {}
			for template_key in template.keys():
				if template_key in strategy_data:
					clean_data[template_key] = strategy_data[template_key]

			# Add missing required top-level fields
			required_fields = ["name", "universe", "description", "engine", "indicators"]
			for field in required_fields:
				if field not in clean_data and field in template:
					clean_data[field] = template[field]
					changes.append(f"Added missing field: {field}")

			# Add missing sections with defaults (in template order)
			sections = ["watchlist", "signals", "entry", "order", "exit", "backtest"]
			for section in sections:
				if section not in clean_data and section in template:
					clean_data[section] = template[section].copy() if isinstance(template[section], dict) else template[section]
					changes.append(f"Added missing section: {section}")

			# Add missing weights and parameters to signals section
			if "signals" in clean_data:
				if "weights" not in clean_data["signals"] and "weights" in template.get("signals", {}):
					clean_data["signals"]["weights"] = template["signals"]["weights"].copy()
					changes.append("Added signals.weights section")
				if "parameters" not in clean_data["signals"] and "parameters" in template.get("signals", {}):
					clean_data["signals"]["parameters"] = template["signals"]["parameters"].copy()
					changes.append("Added signals.parameters section")

			# Validate required sub-fields in sections
			if "entry" in clean_data:
				if "parameters" not in clean_data["entry"]:
					clean_data["entry"]["parameters"] = template["entry"]["parameters"].copy()
					changes.append("Added entry.parameters section")
				else:
					# Add missing sub-parameters from template in template order
					entry_params = clean_data["entry"]["parameters"]
					for param_key, param_value in template.get("entry", {}).get("parameters", {}).items():
						if param_key not in entry_params:
							entry_params[param_key] = param_value
							changes.append(f"Added entry.parameters.{param_key}")

			if "order" in clean_data:
				if "parameters" not in clean_data["order"]:
					clean_data["order"]["parameters"] = template["order"]["parameters"].copy()
					changes.append("Added order.parameters section")
				else:
					# Add missing sub-parameters from template in template order
					order_params = clean_data["order"]["parameters"]
					for param_key, param_value in template.get("order", {}).get("parameters", {}).items():
						if param_key not in order_params:
							order_params[param_key] = param_value
							changes.append(f"Added order.parameters.{param_key}")

			if "exit" in clean_data:
				if "parameters" not in clean_data["exit"]:
					clean_data["exit"]["parameters"] = template["exit"]["parameters"].copy()
					changes.append("Added exit.parameters section")
				else:
					# Add missing sub-parameters from template in template order
					exit_params = clean_data["exit"]["parameters"]
					for param_key, param_value in template.get("exit", {}).get("parameters", {}).items():
						if param_key not in exit_params:
							exit_params[param_key] = param_value
							changes.append(f"Added exit.parameters.{param_key}")

			# Validate nested keys within sections and maintain template order
			for section_name in ["entry", "order", "exit"]:
				if section_name in clean_data and "parameters" in clean_data[section_name]:
					section_params = clean_data[section_name]["parameters"]
					template_params = template.get(section_name, {}).get("parameters", {})
					invalid_params = []

					# Identify invalid parameters
					for param_key in list(section_params.keys()):
						if param_key not in template_params:
							invalid_params.append(param_key)
							changes.append(f"Commented invalid nested key: {section_name}.parameters.{param_key}")

					# Rebuild parameters in template order, excluding invalid ones
					if invalid_params or template_params:
						invalid_nested_keys[f"{section_name}.parameters"] = invalid_params
						ordered_params = {}

						# Add parameters in template order
						for template_param in template_params.keys():
							if template_param in section_params:
								ordered_params[template_param] = section_params[template_param]

						# Add any valid parameters not in template (at the end)
						for param_key in section_params.keys():
							if param_key not in template_params and param_key not in invalid_params:
								ordered_params[param_key] = section_params[param_key]

						clean_data[section_name]["parameters"] = ordered_params

			# Note: signals.weights is flexible - users can define custom weights
			# We don't validate individual weight keys since users may use different signal names

			# Save if not dry run
			if not dry_run and changes:
				file_path = self._get_strategy_file(strategy_name)
				# First load original file to get invalid sections
				original_file_path = self._get_strategy_file(strategy_name)
				original_invalid_sections = ""
				if original_file_path.exists():
					with open(original_file_path, 'r') as f:
						original_content = f.read()
						# Extract invalid top-level sections from original file
						for invalid_key in invalid_keys:
							original_invalid_sections += self._extract_key_section(original_content, invalid_key)
						# Extract invalid nested keys from original file
						for nested_path, nested_keys in invalid_nested_keys.items():
							if original_invalid_sections and not original_invalid_sections.endswith('\n\n'):
								original_invalid_sections += '\n'
							original_invalid_sections += f"# [{nested_path}]\n"
							for nested_key in nested_keys:
								original_invalid_sections += self._extract_nested_key_section(original_content, nested_path, nested_key)

				# Reorder clean_data to match template key order
				ordered_data = {}
				for template_key in template.keys():
					if template_key in clean_data:
						ordered_data[template_key] = clean_data[template_key]

				# Save clean data with template key order
				with open(file_path, 'w') as f:
					yaml.dump(ordered_data, f, default_flow_style=False, sort_keys=False)

				# Append commented invalid sections
				if original_invalid_sections:
					with open(file_path, 'a') as f:
						f.write("\n# ===== COMMENTED OUT (INVALID KEYS) =====\n")
						f.write(original_invalid_sections)

				changes.append(f"Saved fixed strategy to {file_path}")

			return {
				"status": "success",
				"strategy": strategy_name,
				"changes": changes,
				"change_count": len(changes),
				"dry_run": dry_run,
			}

		except Exception as e:
			return {
				"status": "error",
				"message": f"Fix failed: {str(e)}",
				"error_type": type(e).__name__,
			}

	def _extract_key_section(self, content: str, key: str) -> str:
		"""Extract a YAML key section from content and comment it out.

		Args:
			content: YAML file content
			key: Key to extract and comment

		Returns:
			Commented out section string
		"""
		lines = content.split('\n')
		result_lines = []
		in_section = False
		section_indent = -1

		for line in lines:
			# Check if this line starts the key section
			if line.strip().startswith(f"{key}:"):
				in_section = True
				section_indent = len(line) - len(line.lstrip())
				result_lines.append(f"# {line}")
			elif in_section:
				# Check if we're still in the section (based on indentation)
				if line.strip() and not line.startswith(' ' * (section_indent + 1)) and not line.startswith('\t'):
					# Unindented line means section ended
					in_section = False
				else:
					# Still in section, comment it out
					result_lines.append(f"# {line}")

		return '\n'.join(result_lines) + '\n' if result_lines else ""

	def _extract_nested_key_section(self, content: str, parent_path: str, key: str) -> str:
		"""Extract a nested YAML key and comment it out.

		Args:
			content: YAML file content
			parent_path: Parent path (e.g., 'entry.parameters')
			key: Key to extract and comment

		Returns:
			Commented out section string
		"""
		lines = content.split('\n')
		result_lines = []
		in_parent = False
		in_key = False
		parent_indent = -1
		key_indent = -1
		parent_parts = parent_path.split('.')

		for i, line in enumerate(lines):
			stripped = line.strip()

			# Check if we're finding the parent section (first level)
			if not in_parent and stripped.startswith(f"{parent_parts[0]}:"):
				in_parent = True
				parent_indent = len(line) - len(line.lstrip())
				continue

			if in_parent:
				# Check if we're at a sibling or lower indent (parent ended)
				if stripped and not line.startswith(' ' * (parent_indent + 1)) and not line.startswith('\t'):
					in_parent = False
					continue

				# Look for nested parent (e.g., 'parameters' under 'entry')
				if len(parent_parts) > 1:
					nested_parent = parent_parts[1]
					if stripped.startswith(f"{nested_parent}:"):
						key_indent = len(line) - len(line.lstrip())

						# Now look for the actual key within this nested parent
						for j in range(i + 1, len(lines)):
							nested_line = lines[j]
							nested_stripped = nested_line.strip()

							# End of nested parent section
							if nested_stripped and not nested_line.startswith(' ' * (key_indent + 1)) and not nested_line.startswith('\t'):
								break

							# Found the key
							if nested_stripped.startswith(f"{key}:"):
								nested_key_indent = len(nested_line) - len(nested_line.lstrip())
								result_lines.append(f"# {nested_line}")

								# Include all sub-lines of this key
								for k in range(j + 1, len(lines)):
									sub_line = lines[k]
									sub_stripped = sub_line.strip()

									# End of this key's content
									if sub_stripped and not sub_line.startswith(' ' * (nested_key_indent + 1)) and not sub_line.startswith('\t'):
										break

									result_lines.append(f"# {sub_line}")
								break

		return '\n'.join(result_lines) + '\n' if result_lines else ""

	def _load_template(self) -> Dict[str, Any]:
		"""Load the strategy template from init/templates/strategy.yml.

		Returns:
			Dict with template structure
		"""
		try:
			template_file = self.project_root / "init" / "templates" / "strategy.yml"
			if not template_file.exists():
				# Return inline minimal template if file doesn't exist
				return {
					"name": "template_name",
					"universe": "cac40",
					"description": "Strategy description",
					"engine": "TaModel",
					"indicators": [],
					"watchlist": {"enabled": True, "parameters": {}},
					"signals": {"enabled": True, "weights": {}, "parameters": {}},
					"entry": {"enabled": True, "parameters": {}},
					"order": {"enabled": True, "parameters": {}},
					"exit": {"enabled": True, "parameters": {}},
					"backtest": {"initial_capital": 10000},
				}

			with open(template_file, 'r') as f:
				return yaml.safe_load(f) or {}

		except Exception:
			# Return minimal template structure on error
			return {
				"name": "template_name",
				"universe": "cac40",
				"description": "Strategy description",
				"engine": "TaModel",
				"indicators": [],
				"watchlist": {"enabled": True, "parameters": {}},
				"signals": {"enabled": True, "weights": {}, "parameters": {}},
				"entry": {"enabled": True, "parameters": {}},
				"order": {"enabled": True, "parameters": {}},
				"exit": {"enabled": True, "parameters": {}},
				"backtest": {"initial_capital": 10000},
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
