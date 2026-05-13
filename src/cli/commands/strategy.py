"""Strategy validation commands using unified validator."""

import sys
import yaml
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
