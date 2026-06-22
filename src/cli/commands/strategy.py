"""Strategy validation commands using unified validator."""

import sys
import yaml
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional

# Add src to path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from tools.strategy.strategy import StrategyManager
from tools.strategy.validator import StrategyValidator
from tools.strategy.versioning import save_strategy_version
from tools.indicators import IndicatorChecker
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box


console = Console()


class StrategyCommands:
	"""CLI commands for strategy management using unified validator."""

	def __init__(self, project_root: Path):
		"""Initialize strategy commands.

		Args:
			project_root: Root directory of the project
		"""
		self.project_root = project_root
		self.strategy_manager = StrategyManager()
		self.validator = StrategyValidator()
		self.checker = IndicatorChecker()
		# Load template for structure comparison
		self.template = self._load_template()

	def check(self, strategy_name: str, fix: bool = False, template: bool = False) -> Dict[str, Any]:
		"""Check strategy configuration for compliance.

		Args:
			strategy_name: Name of the strategy to check
			fix: If True, attempt to fix issues
			template: If True, show template structure

		Returns:
			Check result
		"""
		if template:
			self._show_template()
			return {"status": "success", "message": "Template displayed"}

		console.print(f"\n[bold cyan]Strategy Compliance Check: {strategy_name}[/bold cyan]\n")

		# Load strategy
		result = self.strategy_manager.load_strategy(strategy_name)
		if result.get("status") != "success":
			console.print(f"[red]✗ Failed to load strategy: {result.get('message', 'Unknown error')}[/red]")
			return {
				"status": "error",
				"strategy": strategy_name,
				"message": result.get('message', 'Unknown error')
			}

		strategy_data = result.get("data", {})

		# Show indicators
		indicators = strategy_data.get("indicators", [])
		console.print(f"[cyan]Indicators ({len(indicators)}):[/cyan] {', '.join(indicators)}\n")

		# Validate using tree-based comparison
		validation_result = self.strategy_manager.validate_against_template(strategy_name)
		errors = validation_result.get("errors", [])
		warnings = validation_result.get("warnings", [])

		# Validate all formulas
		formula_errors, invalid_formulas = self.validator.validate_formulas(strategy_data)
		errors.extend(formula_errors)

		# Extract indicators from formulas
		extracted_indicators = self.validator.extract_indicators_from_strategy(strategy_data)

		# Filter out data fields (not indicators)
		data_fields = {'open', 'high', 'low', 'close', 'volume', 'timestamp', 'ticker', 'date'}
		extracted_indicators_filtered = extracted_indicators - data_fields
		missing_indicators = extracted_indicators_filtered - set(indicators)

		if missing_indicators:
			# Display missing indicators clearly
			missing_list = ', '.join(sorted(missing_indicators))
			console.print(f"\n[yellow]⚠ Missing indicators used in formulas:[/yellow]")
			console.print(f"[yellow]{missing_list}[/yellow]\n")

		# Validate all indicators (declared and extracted)
		indicator_validation = self.validator.validate_all_indicators(strategy_data)

		# Filter out data field errors (they're not really indicators)
		data_fields = {'open', 'high', 'low', 'close', 'volume', 'timestamp', 'ticker', 'date'}

		declared_errors_filtered = [
			err for err in indicator_validation.get("declared_errors", [])
			if not any(field in err.lower() for field in data_fields)
		]

		extracted_errors_filtered = [
			err for err in indicator_validation.get("extracted_errors", [])
			if not any(field in err.lower() for field in data_fields)
		]

		indicator_errors = declared_errors_filtered + extracted_errors_filtered

		# Combine errors and warnings for display
		all_issues = errors + warnings + indicator_errors

		# Check validity before fixes
		is_valid = len(errors) == 0 and len(indicator_errors) == 0

		# Apply fixes if requested
		if fix:
			changes = []
			data_fields = {'open', 'high', 'low', 'close', 'volume', 'timestamp', 'ticker', 'date'}

			# Remove data fields from declared indicators (they're not real indicators)
			declared_with_data_fields = [ind for ind in indicators if ind.lower() in data_fields]
			if declared_with_data_fields:
				new_indicators = [ind for ind in indicators if ind.lower() not in data_fields]
				strategy_data["indicators"] = new_indicators
				changes.append(f"Removed {len(declared_with_data_fields)} data field(s) from indicators: {', '.join(sorted(declared_with_data_fields))}")
				indicators = new_indicators  # Update for the rest of the fix

			# Add missing valid indicators from formulas (only those that exist in registry)
			if missing_indicators:
				valid_missing = []
				invalid_missing = []
				for ind in missing_indicators:
					ind_result = self.checker.check(ind, verbose=False)
					if isinstance(ind_result, dict):
						ind_result = list(ind_result.values())[0]
					if ind_result.exists and ind_result.is_valid():
						valid_missing.append(ind)
					else:
						invalid_missing.append(ind)

				if valid_missing:
					new_indicators = indicators + valid_missing
					new_indicators.sort()
					strategy_data["indicators"] = new_indicators
					changes.append(f"Added {len(valid_missing)} missing valid indicator(s): {', '.join(sorted(valid_missing))}")

				# Report data fields that were skipped
				if invalid_missing:
					changes.append(f"Skipped {len(invalid_missing)} data field(s) (not indicators): {', '.join(sorted(invalid_missing))}")

			# Handle extra keys: comment them out and add missing template keys
			if self.template:
				extra_key_changes = self._fix_template_structure(strategy_name, strategy_data)
				if extra_key_changes:
					changes.extend(extra_key_changes)

			# Apply other fixes (formatting, structure, etc)
			if changes:
				# Save the strategy data first (indicators changes)
				save_result = self.strategy_manager.save_strategy(strategy_name, strategy_data)

				if save_result.get("status") == "success":
					console.print(f"[green]✓ Strategy fixed ({len(changes)} changes)[/green]\n")
					console.print("[bold]Changes made:[/bold]")
					for change in changes:
						console.print(f"  • {change}")
					console.print()
					return {
						"status": "success",
						"strategy": strategy_name,
						"is_valid": False,  # Still has errors (invalid declared indicators)
						"fixed": True,
						"changes": changes
					}
				else:
					console.print(f"[red]✗ Failed to save strategy: {save_result.get('message', 'Unknown error')}[/red]")
			else:
				# No changes to make, but show that check was run
				pass

		# Filter data fields from indicator_validation before display
		data_fields = {'open', 'high', 'low', 'close', 'volume', 'timestamp', 'ticker', 'date'}
		indicator_validation_filtered = indicator_validation.copy()
		indicator_validation_filtered["declared_errors"] = declared_errors_filtered
		indicator_validation_filtered["extracted_errors"] = extracted_errors_filtered

		# Display results
		self._display_results(
			strategy_name,
			errors,
			warnings,
			formula_errors,
			missing_indicators,
			indicator_validation_filtered
		)

		return {
			"status": "success",
			"strategy": strategy_name,
			"is_valid": is_valid,
			"errors": errors,
			"warnings": warnings,
			"issues_found": len(all_issues)
		}

	def _load_template(self) -> Dict[str, Any]:
		"""Load the strategy template from the template file.

		Returns:
			Template configuration dict
		"""
		try:
			# Try init/templates/strategy.yml first
			template_path = Path(__file__).parent.parent.parent.parent / "init" / "templates" / "strategy.yml"
			if not template_path.exists():
				# Fallback to src/config/template.yml
				template_path = Path(__file__).parent.parent.parent / "config" / "template.yml"
			if template_path.exists():
				with open(template_path, 'r') as f:
					return yaml.safe_load(f) or {}
			return {}
		except Exception:
			return {}

	def _fix_template_structure(self, strategy_name: str, strategy_data: Dict[str, Any]) -> List[str]:
		"""Synchronize strategy structure with template.

		Adds missing template keys and removes extra keys not in template.

		Args:
			strategy_name: Strategy name
			strategy_data: Strategy configuration (modified in place)

		Returns:
			List of changes made
		"""
		if not self.template:
			return []

		changes = []
		template = self.template.get("strategies", [{}])[0] if "strategies" in self.template else self.template

		# Find missing keys from template and add them
		missing_keys = self._find_missing_keys(template, strategy_data)
		if missing_keys:
			self._add_missing_keys(strategy_data, template, missing_keys)
			changes.append(f"Added {len(missing_keys)} missing template key(s)")

		# Find and remove extra keys not in template
		extra_keys = self._find_extra_keys(strategy_data, template)
		if extra_keys:
			removed = self._remove_extra_keys(strategy_data, template, extra_keys)
			if removed > 0:
				changes.append(f"Commented out {removed} extra key(s) not in template")

		return changes

	def _find_missing_keys(self, template: Dict, strategy: Dict, path: str = "") -> List[str]:
		"""Find keys in template but not in strategy.

		Args:
			template: Template dict
			strategy: Strategy dict
			path: Current path in the structure

		Returns:
			List of missing key paths
		"""
		missing = []
		if not isinstance(template, dict) or not isinstance(strategy, dict):
			return missing

		for key, value in template.items():
			current_path = f"{path}.{key}" if path else key
			if key not in strategy:
				missing.append(current_path)
			elif isinstance(value, dict) and isinstance(strategy.get(key), dict):
				missing.extend(self._find_missing_keys(value, strategy[key], current_path))

		return missing

	def _find_extra_keys(self, strategy: Dict, template: Dict, path: str = "") -> List[str]:
		"""Find keys in strategy but not in template.

		Args:
			strategy: Strategy dict
			template: Template dict
			path: Current path in the structure

		Returns:
			List of extra key paths
		"""
		extra = []
		if not isinstance(strategy, dict) or not isinstance(template, dict):
			return extra

		for key, value in strategy.items():
			current_path = f"{path}.{key}" if path else key
			if key not in template:
				extra.append(current_path)
			elif isinstance(value, dict) and isinstance(template.get(key), dict):
				extra.extend(self._find_extra_keys(value, template[key], current_path))

		return extra

	def _add_missing_keys(self, strategy: Dict, template: Dict, missing_keys: List[str]) -> None:
		"""Add missing keys from template to strategy.

		Args:
			strategy: Strategy dict to update
			template: Template dict with defaults
			missing_keys: List of missing key paths
		"""
		for key_path in missing_keys:
			parts = key_path.split(".")
			template_ref = template
			strategy_ref = strategy

			# Navigate to parent and get value from template
			for i, part in enumerate(parts[:-1]):
				if part not in strategy_ref:
					strategy_ref[part] = {}
				strategy_ref = strategy_ref[part]
				if part in template_ref:
					template_ref = template_ref[part]

			# Add the final key
			final_key = parts[-1]
			if final_key in template_ref and final_key not in strategy_ref:
				strategy_ref[final_key] = template_ref[final_key]

	def _remove_extra_keys(self, strategy: Dict, template: Dict, extra_keys: List[str]) -> int:
		"""Remove extra keys from strategy that aren't in template.

		Note: Values are preserved in comments, keys are removed from structure.

		Args:
			strategy: Strategy dict to update (modified in place)
			template: Template dict
			extra_keys: List of extra key paths

		Returns:
			Number of keys removed
		"""
		removed = 0
		# Sort by depth (deepest first) to avoid issues with parent removal
		sorted_keys = sorted(extra_keys, key=lambda x: x.count("."), reverse=True)

		for key_path in sorted_keys:
			parts = key_path.split(".")
			strategy_ref = strategy

			# Navigate to parent
			for part in parts[:-1]:
				if part not in strategy_ref:
					break
				strategy_ref = strategy_ref[part]
				if not isinstance(strategy_ref, dict):
					break
			else:
				# Remove the final key if it exists
				final_key = parts[-1]
				if final_key in strategy_ref:
					del strategy_ref[final_key]
					removed += 1

		return removed

	def _comment_extra_keys(self, strategy_name: str, warnings: List[str]) -> Dict[str, Any]:
		"""Comment out extra keys not in template.

		Args:
			strategy_name: Strategy name
			warnings: List of warning messages about extra keys

		Returns:
			Result dict with list of commented keys
		"""
		try:
			strategy_file = self.strategy_manager._get_strategy_file(strategy_name)

			# Extract key paths from warnings (e.g., "signals.weights.momentum" from warning)
			extra_keys = []
			for warning in warnings:
				if "Extra key not in template:" in warning:
					# Extract the key path
					key_path = warning.replace("Extra key not in template:", "").strip()
					extra_keys.append(key_path)

			if not extra_keys:
				return {"status": "success", "commented_keys": []}

			# Read the file
			with open(strategy_file, 'r') as f:
				content = f.read()

			# Comment out lines containing these keys
			lines = content.split('\n')
			commented_lines = []
			commented_count = 0

			for i, line in enumerate(lines):
				# Check if this line contains any of the extra keys
				for key in extra_keys:
					# Extract the last part of the key path (e.g., "momentum" from "signals.weights.momentum")
					key_name = key.split('.')[-1]
					if key_name in line and ':' in line and not line.strip().startswith('#'):
						# Comment out this line and preserve indentation
						indent = len(line) - len(line.lstrip())
						commented_lines.append(' ' * indent + '# ' + line.lstrip())
						commented_count += 1
						break
				else:
					commented_lines.append(line)

			# Write back
			with open(strategy_file, 'w') as f:
				f.write('\n'.join(commented_lines))

			return {
				"status": "success",
				"commented_keys": extra_keys[:commented_count],
				"file": str(strategy_file)
			}

		except Exception as e:
			return {
				"status": "error",
				"message": f"Failed to comment extra keys: {str(e)}"
			}

	def _display_results(
		self,
		strategy_name: str,
		errors: list,
		warnings: list,
		formula_errors: list = None,
		missing_indicators: set = None,
		indicator_validation: dict = None
	):
		"""Display validation results with errors and warnings separated.

		Args:
			strategy_name: Strategy name
			errors: List of error messages (missing template keys)
			warnings: List of warning messages (extra keys)
			formula_errors: List of formula validation errors
			missing_indicators: Set of indicators used in formulas but not declared
			indicator_validation: Indicator validation results dict
		"""
		formula_errors = formula_errors or []
		missing_indicators = missing_indicators or set()
		indicator_validation = indicator_validation or {}
		indicator_errors = (
			indicator_validation.get("declared_errors", []) +
			indicator_validation.get("extracted_errors", [])
		)

		if not errors and not warnings and not formula_errors and not missing_indicators and not indicator_errors:
			console.print("[bold green]✓ Strategy is valid and ready to use[/bold green]\n")
			return

		# Display errors (missing template keys, formula errors, and indicator errors)
		all_errors = errors + indicator_errors
		if all_errors:
			console.print(f"[bold red]✗ {len(all_errors)} error(s) found:[/bold red]\n")
			errors_table = Table(title="Errors (Template, Formulas & Indicators)", box=box.ROUNDED)
			errors_table.add_column("Error", style="red")
			for error in all_errors:
				errors_table.add_row(error)
			console.print(errors_table)
			console.print()

		# Display indicator validation summary
		if indicator_validation:
			decl_count = len(indicator_validation.get("declared_indicators", []))
			extr_count = len(indicator_validation.get("extracted_indicators", []))
			missing_from_decl = indicator_validation.get("missing_from_declaration", [])

			if decl_count > 0 or extr_count > 0:
				indicator_summary = f"Declared: {decl_count}, Extracted from formulas: {extr_count}"
				if missing_from_decl:
					indicator_summary += f", Missing from declaration: {len(missing_from_decl)}"
				console.print(f"[cyan]📊 Indicator Summary:[/cyan] {indicator_summary}\n")

		# Display warnings (extra keys only - missing indicators shown at top)
		if warnings:
			console.print(f"[bold yellow]⚠ {len(warnings)} warning(s) found:[/bold yellow]\n")
			warnings_table = Table(title="Warnings (Extra Keys Not in Template)", box=box.ROUNDED)
			warnings_table.add_column("Warning", style="yellow")
			for warning in warnings:
				warnings_table.add_row(warning)
			console.print(warnings_table)
			console.print()


	def edit(self, strategy_name: str, use_editor: bool = False) -> Dict[str, Any]:
		"""Edit a strategy interactively or in $EDITOR.

		Args:
			strategy_name: Name of the strategy to edit
			use_editor: If True, open in $EDITOR; if False, use interactive wizard

		Returns:
			Result dictionary with status
		"""
		# Load strategy
		result = self.strategy_manager.load_strategy(strategy_name)
		if result.get("status") != "success":
			console.print(f"[red]✗ Strategy not found: {strategy_name}[/red]")
			return {
				"status": "error",
				"message": f"Strategy '{strategy_name}' not found",
			}

		if use_editor:
			return self._edit_in_editor(strategy_name)
		else:
			return self._edit_wizard(strategy_name)

	def _edit_in_editor(self, strategy_name: str) -> Dict[str, Any]:
		"""Open strategy in $EDITOR for direct editing.

		Args:
			strategy_name: Strategy name to edit

		Returns:
			Result dictionary with status
		"""
		console.print(f"\n[bold cyan]Opening {strategy_name} in editor...[/bold cyan]\n")

		strategy_file = self.strategy_manager._get_strategy_file(strategy_name)

		# Get editor from environment or default to nano
		editor = os.environ.get("EDITOR", "nano")

		try:
			# Open file in editor
			subprocess.run([editor, str(strategy_file)], check=False)

			# Validate after editing
			validation = self.strategy_manager.validate_against_template(strategy_name)
			errors = validation.get("errors", [])
			warnings = validation.get("warnings", [])

			if errors:
				console.print(f"\n[bold yellow]⚠ Validation errors found:[/bold yellow]\n")
				errors_table = Table(title="Errors", box=box.ROUNDED)
				errors_table.add_column("Error", style="red")
				for error in errors:
					errors_table.add_row(error)
				console.print(errors_table)
				console.print()

				if Confirm.ask("[yellow]Try to auto-fix errors?[/yellow]"):
					fix_result = self.strategy_manager.fix_strategy(strategy_name, dry_run=False)
					if fix_result.get("status") == "success":
						console.print(f"\n[green]✓ Auto-fixed {fix_result.get('change_count', 0)} issues[/green]\n")
						return {"status": "success", "message": "Strategy edited and fixed"}
					else:
						console.print(f"\n[red]✗ Auto-fix failed: {fix_result.get('message')}[/red]\n")
				return {"status": "error", "message": "Strategy has validation errors"}

			if warnings:
				console.print(f"[yellow]⚠ {len(warnings)} warning(s) found (extra keys not in template)[/yellow]\n")
				if Confirm.ask("[yellow]Auto-fix warnings?[/yellow]"):
					fix_result = self.strategy_manager.fix_strategy(strategy_name, dry_run=False)
					if fix_result.get("status") == "success":
						console.print(f"\n[green]✓ Fixed warnings[/green]\n")

			console.print(f"[green]✓ Strategy '{strategy_name}' edited successfully[/green]\n")
			return {"status": "success", "message": "Strategy edited and saved"}

		except Exception as e:
			console.print(f"[red]✗ Error opening editor: {e}[/red]")
			return {
				"status": "error",
				"message": f"Failed to edit strategy: {str(e)}",
			}

	def _edit_wizard(self, strategy_name: str) -> Dict[str, Any]:
		"""Edit strategy using interactive wizard.

		Args:
			strategy_name: Strategy name to edit

		Returns:
			Result dictionary with status
		"""
		console.print(f"\n[bold cyan]Strategy Editor - {strategy_name}[/bold cyan]\n")

		result = self.strategy_manager.load_strategy(strategy_name)
		strategy_data = result.get("data", {})

		# Interactive editing menu
		while True:
			console.print("[cyan]What would you like to edit?[/cyan]")
			options = [
				"1. Strategy metadata (name, description, universe)",
				"2. Indicators",
				"3. Entry configuration",
				"4. Exit configuration",
				"5. Watchlist settings",
				"6. Order settings",
				"7. View current strategy",
				"8. Open in $EDITOR for full control",
				"9. Save and exit",
				"0. Exit without saving",
			]

			for opt in options:
				console.print(f"[cyan]{opt}[/cyan]")

			choice = Prompt.ask("[cyan]Select option[/cyan]", default="9")

			if choice == "1":
				self._edit_metadata(strategy_data)
			elif choice == "2":
				self._edit_indicators(strategy_data)
			elif choice == "3":
				self._edit_entry(strategy_data)
			elif choice == "4":
				self._edit_exit(strategy_data)
			elif choice == "5":
				self._edit_watchlist(strategy_data)
			elif choice == "6":
				self._edit_order(strategy_data)
			elif choice == "7":
				self._display_strategy_summary(strategy_data)
			elif choice == "8":
				# Save wizard edits first, then open in editor
				new_version = save_strategy_version(strategy_name, strategy_data)
				console.print(f"[green]✓ Wizard changes saved as v{new_version}[/green]\n")
				return self._edit_in_editor(strategy_name)
			elif choice == "9":
				# Validate before saving
				new_version = save_strategy_version(strategy_name, strategy_data)
				console.print(f"[dim]Saved as v{new_version}[/dim]")
				validation = self.strategy_manager.validate_against_template(strategy_name)
				errors = validation.get("errors", [])

				if errors:
					console.print(f"\n[yellow]⚠ Validation errors found - auto-fixing...[/yellow]\n")
					fix_result = self.strategy_manager.fix_strategy(strategy_name, dry_run=False)
					if fix_result.get("status") == "success":
						console.print(f"[green]✓ Strategy saved and auto-fixed[/green]\n")
				else:
					console.print(f"[green]✓ Strategy saved successfully[/green]\n")
				return {"status": "success", "message": "Strategy edited and saved"}
			elif choice == "0":
				console.print("[yellow]Exiting without saving[/yellow]\n")
				return {"status": "cancelled", "message": "Edit cancelled"}

	def _edit_metadata(self, strategy_data: Dict[str, Any]) -> None:
		"""Edit strategy metadata interactively."""
		console.print("\n[cyan]Strategy Metadata[/cyan]")
		console.print(f"Current name: {strategy_data.get('name')}")
		console.print(f"Current universe: {strategy_data.get('universe')}")
		console.print(f"Current description: {strategy_data.get('description', 'N/A')}\n")

		if Confirm.ask("[cyan]Edit name?[/cyan]", default=False):
			strategy_data["name"] = Prompt.ask("[cyan]New name[/cyan]")

		if Confirm.ask("[cyan]Edit universe?[/cyan]", default=False):
			strategy_data["universe"] = Prompt.ask("[cyan]New universe[/cyan]")

		if Confirm.ask("[cyan]Edit description?[/cyan]", default=False):
			strategy_data["description"] = Prompt.ask("[cyan]New description[/cyan]")

		console.print("[green]✓ Metadata updated[/green]\n")

	def _edit_indicators(self, strategy_data: Dict[str, Any]) -> None:
		"""Edit indicators list interactively."""
		console.print("\n[cyan]Indicators[/cyan]")
		current = strategy_data.get("indicators", [])
		console.print(f"Current indicators ({len(current)}): {', '.join(current)}\n")

		if Confirm.ask("[cyan]Add indicator?[/cyan]", default=False):
			while True:
				ind = Prompt.ask("[cyan]Indicator name (or 'done' to finish)[/cyan]")
				if ind.lower() == "done":
					break
				if ind not in current:
					current.append(ind)
					console.print(f"[green]✓ Added: {ind}[/green]")
				else:
					console.print(f"[yellow]⚠ Already exists: {ind}[/yellow]")

		if Confirm.ask("[cyan]Remove indicator?[/cyan]", default=False):
			console.print("Available indicators:")
			for i, ind in enumerate(current, 1):
				console.print(f"  {i}. {ind}")
			choice = Prompt.ask("[cyan]Number to remove (or 'skip')[/cyan]", default="skip")
			if choice != "skip" and choice.isdigit():
				idx = int(choice) - 1
				if 0 <= idx < len(current):
					removed = current.pop(idx)
					console.print(f"[green]✓ Removed: {removed}[/green]")

		console.print()

	def _edit_entry(self, strategy_data: Dict[str, Any]) -> None:
		"""Edit entry configuration interactively."""
		console.print("\n[cyan]Entry Configuration[/cyan]")
		entry = strategy_data.get("entry", {})
		params = entry.get("parameters", {})

		console.print(f"Entry enabled: {entry.get('enabled', False)}")
		console.print(f"Parameters: {list(params.keys())}\n")

		if Confirm.ask("[cyan]Edit entry parameters?[/cyan]", default=False):
			param_name = Prompt.ask("[cyan]Parameter name (e.g., position_size, entry_filter)[/cyan]")
			if param_name not in params:
				params[param_name] = {}
			formula = Prompt.ask("[cyan]Formula/value[/cyan]", default=params[param_name].get("formula", ""))
			description = Prompt.ask("[cyan]Description[/cyan]", default=params[param_name].get("description", ""))

			params[param_name] = {
				"formula": formula,
				"description": description,
			}
			console.print(f"[green]✓ Updated: {param_name}[/green]\n")

	def _edit_exit(self, strategy_data: Dict[str, Any]) -> None:
		"""Edit exit configuration interactively."""
		console.print("\n[cyan]Exit Configuration[/cyan]")
		exit_cfg = strategy_data.get("exit", {})
		params = exit_cfg.get("parameters", {})

		console.print(f"Exit enabled: {exit_cfg.get('enabled', False)}")
		console.print(f"Parameters: {list(params.keys())}\n")

		if Confirm.ask("[cyan]Edit exit parameters?[/cyan]", default=False):
			param_name = Prompt.ask("[cyan]Parameter name (e.g., stop, take_profit)[/cyan]")
			if param_name not in params:
				params[param_name] = {}
			formula = Prompt.ask("[cyan]Formula/value[/cyan]", default=params[param_name].get("formula", ""))
			description = Prompt.ask("[cyan]Description[/cyan]", default=params[param_name].get("description", ""))

			params[param_name] = {
				"formula": formula,
				"description": description,
			}
			console.print(f"[green]✓ Updated: {param_name}[/green]\n")

	def _edit_watchlist(self, strategy_data: Dict[str, Any]) -> None:
		"""Edit watchlist configuration interactively."""
		console.print("\n[cyan]Watchlist Configuration[/cyan]")
		watchlist = strategy_data.get("watchlist", {})
		console.print(f"Watchlist enabled: {watchlist.get('enabled', False)}\n")

		if Confirm.ask("[cyan]Edit watchlist settings?[/cyan]", default=False):
			watchlist["enabled"] = Confirm.ask("[cyan]Enable watchlist?[/cyan]", default=watchlist.get("enabled", True))
			console.print(f"[green]✓ Watchlist settings updated[/green]\n")

	def _edit_order(self, strategy_data: Dict[str, Any]) -> None:
		"""Edit order configuration interactively."""
		console.print("\n[cyan]Order Configuration[/cyan]")
		order = strategy_data.get("order", {})
		console.print(f"Order enabled: {order.get('enabled', False)}\n")

		if Confirm.ask("[cyan]Edit order settings?[/cyan]", default=False):
			order["enabled"] = Confirm.ask("[cyan]Enable order?[/cyan]", default=order.get("enabled", True))
			console.print(f"[green]✓ Order settings updated[/green]\n")

	def _display_strategy_summary(self, strategy_data: Dict[str, Any]) -> None:
		"""Display current strategy configuration summary."""
		console.print(f"\n[bold cyan]Strategy Summary[/bold cyan]\n")
		console.print(f"[cyan]Name:[/cyan] {strategy_data.get('name')}")
		console.print(f"[cyan]Universe:[/cyan] {strategy_data.get('universe')}")
		console.print(f"[cyan]Description:[/cyan] {strategy_data.get('description', 'N/A')}")
		console.print(f"[cyan]Indicators:[/cyan] {len(strategy_data.get('indicators', []))} defined")
		console.print(f"[cyan]Entry:[/cyan] {'enabled' if strategy_data.get('entry', {}).get('enabled') else 'disabled'}")
		console.print(f"[cyan]Exit:[/cyan] {'enabled' if strategy_data.get('exit', {}).get('enabled') else 'disabled'}")
		console.print()

	def create(self, strategy_name: str, universe: Optional[str] = None) -> Dict[str, Any]:
		"""Create a new strategy from the `init/templates/strategy.yml` template.

		Args:
			strategy_name: Name for the new strategy
			universe: Optional universe to use instead of the template's default

		Returns:
			Result dictionary with status and message
		"""
		console.print(f"\n[bold cyan]Creating Strategy[/bold cyan]\n")

		existing = self.strategy_manager.load_strategy(strategy_name)
		if existing.get("status") == "success":
			console.print(f"[red]✗ Strategy already exists: {strategy_name}[/red]")
			return {"status": "error", "message": f"Strategy '{strategy_name}' already exists"}

		template_file = self.project_root / "init" / "templates" / "strategy.yml"
		if not template_file.exists():
			console.print(f"[red]✗ Template not found: {template_file}[/red]")
			return {"status": "error", "message": f"Template not found: {template_file}"}

		with open(template_file, "r") as f:
			template_data = yaml.safe_load(f)

		template_data["name"] = strategy_name
		if universe:
			template_data["universe"] = universe

		new_version = save_strategy_version(strategy_name, template_data)
		file_path = str(self.strategy_manager._get_strategy_file(strategy_name))

		console.print(f"[green]✓ Strategy created: {strategy_name} (v{new_version})[/green]")
		if universe:
			console.print(f"[dim]  Universe: {universe}[/dim]")
		console.print(f"[dim]  Location: {file_path}[/dim]\n")

		return {
			"status": "success",
			"message": f"Strategy '{strategy_name}' created",
			"name": strategy_name,
			"file": file_path,
			"version": new_version,
		}

	def duplicate(self, from_strategy: str, dest_strategy: str) -> Dict[str, Any]:
		"""Duplicate a strategy with a new name.

		Args:
			from_strategy: Source strategy name to duplicate
			dest_strategy: Destination strategy name

		Returns:
			Result dictionary with status and message
		"""
		console.print(f"\n[bold cyan]Duplicating Strategy[/bold cyan]\n")

		# Load source strategy
		result = self.strategy_manager.load_strategy(from_strategy)
		if result.get("status") != "success":
			console.print(f"[red]✗ Source strategy not found: {from_strategy}[/red]")
			return {
				"status": "error",
				"message": f"Source strategy '{from_strategy}' not found",
			}

		strategy_data = result.get("data", {})

		# Check if destination already exists
		dest_check = self.strategy_manager.load_strategy(dest_strategy)
		if dest_check.get("status") == "success":
			console.print(f"[yellow]⚠ Destination strategy already exists: {dest_strategy}[/yellow]")
			console.print("[cyan]Use --force to overwrite[/cyan]")
			return {
				"status": "error",
				"message": f"Destination strategy '{dest_strategy}' already exists",
			}

		# Update the strategy name in the copied data; duplicates start their
		# own version lineage at v1 rather than inheriting the source's version
		strategy_data["name"] = dest_strategy
		strategy_data.pop("version", None)

		# Save the duplicated strategy
		new_version = save_strategy_version(dest_strategy, strategy_data)
		save_result = {"status": "success", "file": str(self.strategy_manager._get_strategy_file(dest_strategy))}

		if save_result.get("status") == "success":
			console.print(f"[green]✓ Strategy duplicated successfully (v{new_version})[/green]")
			console.print(f"[cyan]  From:[/cyan] {from_strategy}")
			console.print(f"[cyan]  To:  [/cyan] {dest_strategy}")
			console.print(f"[cyan]  File:[/cyan] {save_result.get('file')}\n")
			return {
				"status": "success",
				"message": f"Strategy '{from_strategy}' duplicated to '{dest_strategy}'",
				"from": from_strategy,
				"to": dest_strategy,
				"file": save_result.get("file"),
			}
		else:
			console.print(f"[red]✗ Failed to save duplicated strategy: {save_result.get('message')}[/red]")
			return {
				"status": "error",
				"message": f"Failed to duplicate strategy: {save_result.get('message')}",
			}

	def _show_template(self):
		"""Display the strategy template."""
		console.print("\n[bold cyan]Strategy Template[/bold cyan]\n")
		try:
			template_file = self.project_root / "init" / "templates" / "strategy.yml"
			if template_file.exists():
				with open(template_file, 'r') as f:
					content = f.read()
				console.print(content)
			else:
				console.print("[yellow]Template file not found[/yellow]")
		except Exception as e:
			console.print(f"[red]Error loading template: {e}[/red]")
