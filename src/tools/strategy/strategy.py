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
		"""Validate strategy configuration against template schema (dynamic).

		Derives required structure from template instead of hardcoding field names.

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
			template = self._load_template()
			issues = []

			# Dynamically validate structure against template
			self._validate_structure_against_template(
				strategy_data, template, "", issues
			)

			# Validate indicators
			indicator_issues = self._validate_indicators(strategy_data)
			issues.extend(indicator_issues)

			# Validate formulas
			formula_issues = self._validate_formulas(strategy_data)
			issues.extend(formula_issues)

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

	def _validate_structure_against_template(
		self,
		data: Any,
		template: Any,
		path: str,
		issues: List[str]
	) -> None:
		"""Recursively validate data structure against template.

		Args:
			data: Strategy data to validate
			template: Template structure to validate against
			path: Current path for error messages (e.g., "entry.parameters")
			issues: List to accumulate issues
		"""
		# Both should be dicts
		if not isinstance(data, dict) or not isinstance(template, dict):
			return

		# Check for missing fields from template
		for template_key, template_value in template.items():
			current_path = f"{path}.{template_key}" if path else template_key

			if template_key not in data:
				# Missing field from template
				issues.append(f"Missing: {current_path}")
			else:
				# Recursively validate nested structures
				data_value = data[template_key]

				if isinstance(template_value, dict) and isinstance(data_value, dict):
					# Both are dicts - recurse
					self._validate_structure_against_template(
						data_value, template_value, current_path, issues
					)
				elif isinstance(template_value, list) and isinstance(data_value, list):
					# Both are lists - check if list of dicts (e.g., indicators)
					if template_value and isinstance(template_value[0], dict):
						# List of dicts - validate each item
						for i, data_item in enumerate(data_value):
							if isinstance(data_item, dict):
								self._validate_structure_against_template(
									data_item, template_value[0],
									f"{current_path}[{i}]", issues
								)
					# For simple lists (like indicators list), just ensure it's a list
				elif type(template_value) != type(data_value):
					# Type mismatch (but allow some flexibility for scalar values)
					if not isinstance(data_value, (str, int, float, bool, type(None))):
						issues.append(f"Type mismatch at {current_path}: expected {type(template_value).__name__}, got {type(data_value).__name__}")

		# Check for extra fields in data not in template
		for data_key in data.keys():
			if data_key not in template and not data_key.startswith("_") and not data_key.startswith("#"):
				current_path = f"{path}.{data_key}" if path else data_key
				issues.append(f"Unexpected field: {current_path} (not in template)")

	def _build_clean_data(
		self,
		data: Dict[str, Any],
		template: Dict[str, Any],
		changes: List[str]
	) -> Dict[str, Any]:
		"""Build clean data by filling missing fields and removing invalid ones (dynamic).

		Recursively processes data structure following template.

		Args:
			data: Strategy data
			template: Template structure
			changes: List to accumulate change descriptions

		Returns:
			Clean data dict following template structure
		"""
		clean_data = {}

		# Process template keys in order
		for template_key, template_value in template.items():
			if template_key in data:
				data_value = data[template_key]

				if isinstance(template_value, dict) and isinstance(data_value, dict):
					# Recursively clean nested dict
					clean_data[template_key] = self._build_clean_data(
						data_value, template_value, changes
					)
				elif isinstance(template_value, list) and isinstance(data_value, list):
					# Keep lists as-is (don't validate individual items)
					clean_data[template_key] = data_value
				else:
					# Keep scalar values
					clean_data[template_key] = data_value
			else:
				# Missing field - add from template with deep copy
				if isinstance(template_value, dict):
					clean_data[template_key] = self._deep_copy_dict(template_value)
					changes.append(f"Added missing: {template_key}")
				elif isinstance(template_value, list):
					clean_data[template_key] = template_value.copy() if template_value else []
					changes.append(f"Added missing: {template_key}")
				else:
					clean_data[template_key] = template_value
					changes.append(f"Added missing: {template_key}")

		# Note: We don't add extra fields from data that aren't in template
		# They are reported as issues during validation

		return clean_data

	def _deep_copy_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
		"""Deep copy a dict, preserving structure.

		Args:
			d: Dict to copy

		Returns:
			Deep copy of dict
		"""
		result = {}
		for key, value in d.items():
			if isinstance(value, dict):
				result[key] = self._deep_copy_dict(value)
			elif isinstance(value, list):
				result[key] = value.copy()
			else:
				result[key] = value
		return result

	def _identify_invalid_keys(
		self,
		data: Dict[str, Any],
		template: Dict[str, Any],
		path: str = ""
	) -> tuple:
		"""Identify keys in data that are not in template (dynamic).

		Args:
			data: Strategy data
			template: Template structure
			path: Current path for tracking nested keys

		Returns:
			Tuple of (invalid_top_level_keys, invalid_nested_keys_dict)
		"""
		invalid_top_keys = []
		invalid_nested = {}

		# Check for invalid keys at this level
		for data_key in data.keys():
			if data_key not in template and not data_key.startswith("_") and not data_key.startswith("#"):
				if path:
					# This is a nested key
					nested_path = f"{path}.{data_key}" if path else data_key
					if nested_path not in invalid_nested:
						invalid_nested[nested_path] = []
					invalid_nested[nested_path].append(data_key)
				else:
					# Top-level invalid key
					invalid_top_keys.append(data_key)

		# Recursively check nested dicts
		for template_key in template.keys():
			if isinstance(template.get(template_key), dict) and isinstance(data.get(template_key), dict):
				current_path = f"{path}.{template_key}" if path else template_key
				nested_invalid_top, nested_invalid_dict = self._identify_invalid_keys(
					data[template_key], template[template_key], current_path
				)
				invalid_nested.update(nested_invalid_dict)

		return invalid_top_keys, invalid_nested

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
		"""Fix strategy by adding missing template keys and commenting out extra keys.

		Errors (missing template keys in strategy): Added with default values
		Warnings (extra keys in strategy): Moved to commented section at end

		Args:
			strategy_name: Strategy name to fix
			dry_run: If True, don't save, just show what would be fixed

		Returns:
			Dict with fix results and changes made
		"""
		try:
			result = self.load_strategy(strategy_name)
			if result["status"] != "success":
				return {
					"status": "error",
					"message": f"Strategy not found: {strategy_name}",
					"changes": [],
				}

			strategy_data = result["data"]
			template = self._load_template()
			changes = []

			# Step 1: Validate and identify errors/warnings
			errors = []
			warnings = []
			self._compare_trees(strategy_data, template, "", errors, warnings)

			# Step 2: Build fixed data by following template structure
			fixed_data = self._build_fixed_data(strategy_data, template, errors, changes)

			# Step 3: Collect extra keys to comment out
			extra_keys_content = ""
			if warnings:
				extra_keys_content = self._extract_extra_keys_content(
					strategy_data, template, strategy_name
				)

			# Step 4: Save if not dry run
			if not dry_run and (changes or warnings):
				file_path = self._get_strategy_file(strategy_name)

				# Write fixed data (in template key order)
				with open(file_path, 'w') as f:
					yaml.dump(fixed_data, f, default_flow_style=False, sort_keys=False)

				# Append commented extra keys section if there are warnings
				if extra_keys_content:
					with open(file_path, 'a') as f:
						f.write("\n# ===== COMMENTED OUT (EXTRA KEYS) =====\n")
						f.write(extra_keys_content)

				changes.append(f"Saved fixed strategy to {file_path}")

			return {
				"status": "success",
				"strategy": strategy_name,
				"errors_fixed": len(errors),
				"warnings_commented": len(warnings),
				"changes": changes,
				"change_count": len(changes),
				"dry_run": dry_run,
			}

		except Exception as e:
			return {
				"status": "error",
				"message": f"Fix failed: {str(e)}",
				"error_type": type(e).__name__,
				"changes": [],
			}

	def _build_fixed_data(
		self,
		strategy_data: Dict[str, Any],
		template: Dict[str, Any],
		errors: List[str],
		changes: List[str]
	) -> Dict[str, Any]:
		"""Build fixed data by adding missing template keys and preserving order.

		Args:
			strategy_data: Strategy data to fix
			template: Template structure to follow
			errors: List of error messages (for tracking what was fixed)
			changes: List to accumulate change descriptions

		Returns:
			Fixed data dict with template key order
		"""
		fixed = {}

		# Process template keys in order
		for template_key in template.keys():
			if template_key in strategy_data:
				# Key exists in strategy, recurse if both are dicts
				strategy_value = strategy_data[template_key]
				template_value = template[template_key]

				if isinstance(template_value, dict) and isinstance(strategy_value, dict):
					# Recursively fix nested dict
					nested_errors = [e for e in errors if e.startswith(f"Missing template key: {template_key}.")]
					nested_changes = []
					fixed[template_key] = self._build_fixed_data(
						strategy_value, template_value, nested_errors, nested_changes
					)
					changes.extend(nested_changes)
				else:
					# Copy value as-is
					fixed[template_key] = strategy_value
			else:
				# Key missing from strategy - add from template (fill with default)
				template_value = template[template_key]

				if isinstance(template_value, dict):
					fixed[template_key] = self._deep_copy_dict(template_value)
				elif isinstance(template_value, list):
					fixed[template_key] = template_value.copy() if template_value else []
				else:
					fixed[template_key] = template_value

				changes.append(f"Added missing template key: {template_key}")

		return fixed

	def _extract_extra_keys_content(
		self,
		strategy_data: Dict[str, Any],
		template: Dict[str, Any],
		strategy_name: str
	) -> str:
		"""Extract and comment out extra keys not in template.

		Args:
			strategy_data: Strategy data
			template: Template structure
			strategy_name: Strategy name (for reference)

		Returns:
			Commented string of extra keys
		"""
		# Load original file to extract actual YAML content
		file_path = self._get_strategy_file(strategy_name)
		if not file_path.exists():
			return ""

		try:
			with open(file_path, 'r') as f:
				original_content = f.read()
		except Exception:
			return ""

		extra_sections = []

		# Find extra top-level keys
		for key in strategy_data.keys():
			if key not in template:
				# Extract this key's section from original file
				section = self._extract_yaml_section(original_content, key)
				if section:
					extra_sections.append(section)

		return "".join(extra_sections)

	def _extract_yaml_section(self, content: str, key: str) -> str:
		"""Extract a YAML key section and comment it out.

		Args:
			content: YAML file content
			key: Key to extract

		Returns:
			Commented section string
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
				if line.strip():
					line_indent = len(line) - len(line.lstrip())
					if line_indent <= section_indent:
						# Unindented line means section ended
						in_section = False
					else:
						# Still in section, comment it out
						result_lines.append(f"# {line}")
				else:
					# Empty line within section
					result_lines.append(f"# {line}")

		return '\n'.join(result_lines) + '\n' if result_lines else ""

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

	def _extract_missing_indicators(self, strategy_data: Dict[str, Any]) -> List[str]:
		"""Extract indicators referenced in formulas that aren't declared.

		Args:
			strategy_data: Strategy configuration data

		Returns:
			List of indicator names that should be added
		"""
		declared_indicators = set(strategy_data.get("indicators", []))
		referenced_indicators = set()
		ohlcv_columns = {"close", "open", "high", "low", "volume", "date", "datetime"}

		def extract_formulas(section, path=""):
			"""Recursively extract all formulas from a section."""
			if isinstance(section, dict):
				for key, value in section.items():
					current_path = f"{path}.{key}" if path else key
					if isinstance(value, str):
						# Check if this looks like a formula
						if any(op in value for op in ["[", "]", "+", "-", "*", "/", ">", "<", "==", "and", "or", "not"]):
							yield current_path, value
					else:
						yield from extract_formulas(value, current_path)
			elif isinstance(section, list):
				for i, item in enumerate(section):
					yield from extract_formulas(item, f"{path}[{i}]")

		import re
		for formula_path, formula in extract_formulas(strategy_data):
			if not formula or formula.lower() in ["true", "false"]:
				continue

			# Extract referenced indicators (indicator_name[index])
			indicator_pattern = r'([a-z_][a-z0-9_]*)\['
			indicator_matches = re.findall(indicator_pattern, formula, re.IGNORECASE)
			for ref in set(indicator_matches):  # Use set to avoid duplicates
				# Skip built-in functions and data column references
				if ref not in ohlcv_columns and ref not in ["data", "len", "max", "min", "round", "abs", "sum"]:
					referenced_indicators.add(ref)

		# Return indicators that are referenced but not declared
		missing = sorted(referenced_indicators - declared_indicators)
		return missing

	def _validate_indicators(self, strategy_data: Dict[str, Any]) -> List[str]:
		"""Validate that declared indicators are real, calculable indicators.

		Args:
			strategy_data: Strategy configuration data

		Returns:
			List of indicator validation issues
		"""
		issues = []

		try:
			from src.tools.indicators.indicators import list_available_indicators
			available = set(list_available_indicators())
		except Exception:
			# If can't load available indicators, skip validation
			return issues

		import re
		declared_indicators = strategy_data.get("indicators", [])

		for indicator in declared_indicators:
			# Extract base indicator name (everything before the first digit)
			base_name = re.sub(r'_\d+.*', '', indicator)

			if base_name not in available:
				issues.append(f"Invalid indicator '{indicator}': base name '{base_name}' is not a supported indicator")

		return issues

	def _validate_formulas(self, strategy_data: Dict[str, Any]) -> List[str]:
		"""Validate formulas using the DSL evaluator with real calculated indicators.

		Args:
			strategy_data: Strategy configuration data

		Returns:
			List of formula validation issues
		"""
		import pandas as pd

		issues = []
		defined_indicators = list(strategy_data.get("indicators", []))

		# Skip these keys - they're not formulas
		SKIP_KEYS = {"name", "description", "engine", "universe", "enabled", "metric", "order_type"}

		def extract_formulas(section, path=""):
			"""Recursively extract all formulas from a section."""
			if isinstance(section, dict):
				for key, value in section.items():
					if key in SKIP_KEYS:
						continue
					current_path = f"{path}.{key}" if path else key
					if isinstance(value, str):
						# Check if this looks like a formula
						if any(op in value for op in ["[", "]", "+", "-", "*", "/", ">", "<", "==", "and", "or", "not", "&&", "||"]):
							yield current_path, value
					else:
						yield from extract_formulas(value, current_path)
			elif isinstance(section, list):
				for i, item in enumerate(section):
					yield from extract_formulas(item, f"{path}[{i}]")

		# Generate sample data and calculate indicators
		try:
			from src.tools.formula.dsl_parser import evaluate_dsl
			from src.tools.indicators import calculate

			# Create 5 days of sample OHLCV data (oldest to newest for indicator calculation)
			sample_data = pd.DataFrame({
				'open': [100.0, 101.0, 102.0, 101.5, 102.5],
				'high': [102.0, 103.0, 104.0, 103.5, 104.5],
				'low': [99.0, 100.0, 101.0, 100.5, 101.5],
				'close': [101.0, 102.0, 103.0, 102.5, 103.5],
				'volume': [1000000, 1100000, 1200000, 1050000, 1150000],
			})

			# Calculate indicators using the actual indicators.calculate() function
			if defined_indicators:
				try:
					indicator_results = calculate(defined_indicators, sample_data)
					# Add calculated indicators to sample data
					for indicator_name, values in indicator_results.items():
						sample_data[indicator_name] = values
				except Exception as e:
					# If calculation fails, log but don't validate
					return []

			# Reverse to newest-first for DSL parser (which expects index 0 = current/most recent)
			sample_data = sample_data.iloc[::-1].reset_index(drop=True)

			# Validate each formula
			for formula_path, formula in extract_formulas(strategy_data):
				if not formula or formula.lower() in ["true", "false"]:
					continue

				try:
					# Use the DSL evaluator to validate the formula
					evaluate_dsl(formula, sample_data)

				except ValueError as e:
					# Formula evaluation error
					issues.append(f"Formula '{formula}' at {formula_path}: {str(e)}")
				except KeyError as e:
					# Missing indicator or column
					error_msg = str(e).strip("'\"")
					issues.append(f"Formula '{formula}' at {formula_path}: missing '{error_msg}'")
				except SyntaxError as e:
					issues.append(f"Formula '{formula}' at {formula_path}: syntax error - {str(e)}")
				except Exception as e:
					issues.append(f"Formula '{formula}' at {formula_path}: {str(e)}")

		except ImportError:
			# DSL evaluator or indicators not available, skip validation
			pass
		except Exception as e:
			# Silently skip validation if we can't set up sample data
			pass

		return issues

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
				"indicators": [],
				"watchlist": {"enabled": True, "parameters": {}},
				"signals": {"enabled": True, "weights": {}, "parameters": {}},
				"entry": {"enabled": True, "parameters": {}},
				"order": {"enabled": True, "parameters": {}},
				"exit": {"enabled": True, "parameters": {}},
				"backtest": {"initial_capital": 10000},
			}

	def validate_against_template(self, strategy_name: str) -> Dict[str, Any]:
		"""Validate strategy against template using tree-based comparison.

		Distinguishes between:
		- Errors: Template keys missing in strategy
		- Warnings: Strategy keys not in template

		Args:
			strategy_name: Strategy name to validate

		Returns:
			Dict with errors, warnings, and status
		"""
		try:
			# Load strategy and template
			result = self.load_strategy(strategy_name)
			if result["status"] != "success":
				return {
					"status": "error",
					"message": f"Strategy not found: {strategy_name}",
					"errors": [],
					"warnings": [],
				}

			strategy_data = result["data"]
			template = self._load_template()

			errors = []
			warnings = []

			# Build comparison: check for missing template keys and extra keys
			self._compare_trees(strategy_data, template, "", errors, warnings)

			return {
				"status": "success",
				"strategy": strategy_name,
				"errors": errors,
				"warnings": warnings,
				"has_errors": len(errors) > 0,
				"has_warnings": len(warnings) > 0,
				"total_issues": len(errors) + len(warnings),
			}

		except Exception as e:
			return {
				"status": "error",
				"message": f"Validation failed: {str(e)}",
				"errors": [],
				"warnings": [],
			}

	def _compare_trees(
		self,
		strategy_item: Any,
		template_item: Any,
		path: str,
		errors: List[str],
		warnings: List[str]
	) -> None:
		"""Recursively compare strategy and template trees.

		Args:
			strategy_item: Current item in strategy
			template_item: Current item in template
			path: Current path in structure (for error messages)
			errors: List accumulating missing template keys
			warnings: List accumulating extra keys in strategy
		"""
		if not isinstance(strategy_item, dict) or not isinstance(template_item, dict):
			return

		# Check for missing template keys in strategy
		for template_key in template_item.keys():
			current_path = f"{path}.{template_key}" if path else template_key

			if template_key not in strategy_item:
				errors.append(f"Missing template key: {current_path}")
			else:
				# Recursively compare nested structures
				strategy_value = strategy_item[template_key]
				template_value = template_item[template_key]

				if isinstance(template_value, dict) and isinstance(strategy_value, dict):
					self._compare_trees(strategy_value, template_value, current_path, errors, warnings)

		# Check for extra keys in strategy not in template
		for strategy_key in strategy_item.keys():
			current_path = f"{path}.{strategy_key}" if path else strategy_key

			if strategy_key not in template_item:
				warnings.append(f"Extra key not in template: {current_path}")
			else:
				# Recursively compare nested structures
				strategy_value = strategy_item[strategy_key]
				template_value = template_item[strategy_key]

				if isinstance(template_value, dict) and isinstance(strategy_value, dict):
					# Already processed in the previous loop, but we still need to recurse for nested extras
					pass


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
