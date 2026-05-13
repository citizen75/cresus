"""Strategy validation commands using unified validator."""

import sys
import yaml
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Tuple, List

# Add src to path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from tools.strategy.strategy import StrategyManager
from tools.strategy.validator import StrategyValidator
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

		# Combine errors and warnings for display
		all_issues = errors + warnings

		# Apply fixes if requested
		if fix and all_issues:
			fix_result = self.strategy_manager.fix_strategy(strategy_name, dry_run=False)
			if fix_result.get("status") == "success":
				console.print(f"[green]✓ Strategy fixed ({fix_result.get('change_count', 0)} changes)[/green]\n")
				return {
					"status": "success",
					"strategy": strategy_name,
					"is_valid": True,
					"fixed": True,
					"changes": fix_result.get("changes", [])
				}
			else:
				console.print(f"[red]✗ Failed to fix strategy: {fix_result.get('message', 'Unknown error')}[/red]")

		# Display results
		self._display_results(strategy_name, errors, warnings)

		is_valid = len(errors) == 0

		return {
			"status": "success" if is_valid else "error",
			"strategy": strategy_name,
			"is_valid": is_valid,
			"errors": errors,
			"warnings": warnings,
			"issues_found": len(all_issues)
		}

	def _display_results(self, strategy_name: str, errors: list, warnings: list):
		"""Display validation results with errors and warnings separated.

		Args:
			strategy_name: Strategy name
			errors: List of error messages (missing template keys)
			warnings: List of warning messages (extra keys)
		"""
		if not errors and not warnings:
			console.print("[bold green]✓ Strategy is valid and ready to use[/bold green]\n")
			return

		# Display errors (missing template keys)
		if errors:
			console.print(f"[bold red]✗ {len(errors)} error(s) found:[/bold red]\n")
			errors_table = Table(title="Errors (Missing Template Keys)", box=box.ROUNDED)
			errors_table.add_column("Error", style="red")
			for error in errors:
				errors_table.add_row(error)
			console.print(errors_table)
			console.print()

		# Display warnings (extra keys)
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
				self.strategy_manager.save_strategy(strategy_name, strategy_data)
				console.print("[green]✓ Wizard changes saved[/green]\n")
				return self._edit_in_editor(strategy_name)
			elif choice == "9":
				# Validate before saving
				self.strategy_manager.save_strategy(strategy_name, strategy_data)
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

		# Update the strategy name in the copied data
		strategy_data["name"] = dest_strategy

		# Save the duplicated strategy
		save_result = self.strategy_manager.save_strategy(dest_strategy, strategy_data)

		if save_result.get("status") == "success":
			console.print(f"[green]✓ Strategy duplicated successfully[/green]")
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
