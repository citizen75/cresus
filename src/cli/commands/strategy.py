"""Strategy validation commands using unified validator."""

import sys
from pathlib import Path
from typing import Dict, Any

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

		# Validate using unified validator
		is_valid, validation_errors = self.validator.validate(strategy_data)

		# Display results
		self._display_results(strategy_name, is_valid, validation_errors)

		return {
			"status": "success" if is_valid else "error",
			"strategy": strategy_name,
			"is_valid": is_valid,
			"issues_found": len(validation_errors),
			"validation_errors": validation_errors
		}

	def _display_results(self, strategy_name: str, is_valid: bool, validation_errors: list):
		"""Display validation results.

		Args:
			strategy_name: Strategy name
			is_valid: Whether validation passed
			validation_errors: List of error messages
		"""
		if is_valid:
			console.print("[bold green]✓ Strategy is valid and ready to use[/bold green]\n")
			return

		# Display errors in table
		console.print(f"[bold red]✗ {len(validation_errors)} issue(s) found:[/bold red]\n")

		issues_table = Table(title="Issues Found", box=box.ROUNDED)
		issues_table.add_column("Issue", style="yellow")

		for error in validation_errors:
			issues_table.add_row(error)

		console.print(issues_table)
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
