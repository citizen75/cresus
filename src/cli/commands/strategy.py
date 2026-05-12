"""Strategy validation and analysis commands."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
import re

# Add src to path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from tools.strategy.strategy import StrategyManager
from rich.console import Console
from rich.table import Table
from rich import box
from loguru import logger


console = Console()


class StrategyValidator:
	"""Validate and analyze strategy configurations."""

	def __init__(self, project_root: Path):
		"""Initialize strategy validator.

		Args:
			project_root: Root directory of the project
		"""
		self.project_root = project_root
		# Don't pass project_root to StrategyManager so it uses ~/.cresus/db/strategies
		self.strategy_manager = StrategyManager()

	def check_strategy(self, strategy_name: str, fix: bool = False) -> Dict[str, Any]:
		"""Check strategy configuration for issues.

		Args:
			strategy_name: Name of the strategy to check
			fix: If True, attempt to fix identified issues

		Returns:
			Dictionary with analysis results
		"""
		console.print(f"\n[bold cyan]Analyzing strategy: {strategy_name}[/bold cyan]\n")

		# Load strategy
		result = self.strategy_manager.load_strategy(strategy_name)
		if result.get("status") != "success":
			return {
				"status": "error",
				"strategy": strategy_name,
				"message": f"Failed to load strategy: {result.get('message', 'Unknown error')}"
			}

		strategy_data = result.get("data", {})

		# Collect all issues
		issues = {
			"missing_keys": [],
			"invalid_indicators": [],
			"invalid_formulas": [],
			"formula_references": [],
			"warnings": []
		}

		# Check required keys
		issues["missing_keys"] = self._check_required_keys(strategy_data)

		# Get all indicators used in formulas
		defined_indicators = set(strategy_data.get("indicators", []))
		referenced_indicators = self._extract_indicators_from_formulas(strategy_data)
		
		# Find indicators used but not defined
		undefined = referenced_indicators - defined_indicators
		if undefined:
			for ind in sorted(undefined):
				issues["invalid_indicators"].append({
					"indicator": ind,
					"message": f"Used in formulas but not in indicators list"
				})

		# Check formula validity
		issues["invalid_formulas"] = self._validate_formulas(strategy_data)

		# Display results
		self._display_results(strategy_name, strategy_data, issues, fix)

		# Fix issues if requested
		if fix and (issues["missing_keys"] or issues["invalid_indicators"]):
			self._fix_strategy(strategy_name, strategy_data, issues)

		return {
			"status": "success",
			"strategy": strategy_name,
			"issues_found": len(issues["missing_keys"]) + len(issues["invalid_indicators"]) + len(issues["invalid_formulas"]),
			"issues": issues
		}

	def _check_required_keys(self, strategy_data: Dict[str, Any]) -> List[str]:
		"""Check for required keys in strategy config.

		Args:
			strategy_data: Strategy configuration data

		Returns:
			List of missing keys
		"""
		required_sections = ["name", "universe", "indicators", "entry", "exit"]
		missing = []

		for section in required_sections:
			if section not in strategy_data:
				missing.append(f"Missing top-level key: '{section}'")

		# Check entry parameters
		if "entry" in strategy_data:
			entry = strategy_data.get("entry", {})
			entry_params = entry.get("parameters", {})
			required_entry = ["max_positions", "position_size"]
			for param in required_entry:
				if param not in entry_params:
					missing.append(f"Missing entry parameter: '{param}'")

		# Check exit parameters
		if "exit" in strategy_data:
			exit_section = strategy_data.get("exit", {})
			exit_params = exit_section.get("parameters", {})
			# At least one exit condition should be defined
			if not exit_params:
				missing.append("No exit parameters defined")

		return missing

	def _extract_indicators_from_formulas(self, strategy_data: Dict[str, Any]) -> Set[str]:
		"""Extract all indicators referenced in formulas.

		Args:
			strategy_data: Strategy configuration data

		Returns:
			Set of indicator names referenced
		"""
		# OHLCV base data columns that don't need to be declared as indicators
		OHLCV_DATA = {'close', 'open', 'high', 'low', 'volume', 'date', 'datetime'}
		
		indicators = set()
		pattern = r"data\[[\'\"]([^\)\'\"]+)[\'\"]|([a-z_][a-z0-9_]*)\["

		def extract_from_section(section):
			if isinstance(section, dict):
				for key, value in section.items():
					if isinstance(value, str):
						# Find all indicator-like references
						matches = re.findall(r"data\[[\'\"]([^\)\'\"]+)[\'\"]", value)
						indicators.update(matches)
					else:
						extract_from_section(value)
			elif isinstance(section, list):
				for item in section:
					extract_from_section(item)

		# Extract from all sections
		for section in ["watchlist", "signals", "entry", "exit"]:
			if section in strategy_data:
				extract_from_section(strategy_data[section])

		# Filter out OHLCV base data - these don't need to be declared as indicators
		return indicators - OHLCV_DATA

	def _validate_formulas(self, strategy_data: Dict[str, Any]) -> List[Dict[str, str]]:
		"""Validate formula syntax.

		Args:
			strategy_data: Strategy configuration data

		Returns:
			List of formula errors
		"""
		errors = []

		def check_formulas(section, path=""):
			if isinstance(section, dict):
				for key, value in section.items():
					current_path = f"{path}.{key}" if path else key
					if isinstance(value, str) and len(value) > 3:
						# Check for common formula issues
						if value in ["True", "False"]:
							continue
						
						# Check for unmatched brackets
						if value.count("[") != value.count("]"):
							errors.append({
								"location": current_path,
								"formula": value,
								"error": "Unmatched brackets"
							})
						
						# Check for mismatched quotes
						single_quotes = value.count("'")
						double_quotes = value.count('"')
						if single_quotes % 2 != 0 or double_quotes % 2 != 0:
							errors.append({
								"location": current_path,
								"formula": value,
								"error": "Mismatched quotes"
							})
					else:
						check_formulas(value, current_path)
			elif isinstance(section, list):
				for i, item in enumerate(section):
					check_formulas(item, f"{path}[{i}]")

		# Check all sections
		for section in ["watchlist", "signals", "entry", "exit"]:
			if section in strategy_data:
				check_formulas(strategy_data[section], section)

		return errors

	def _display_results(self, strategy_name: str, strategy_data: Dict[str, Any], issues: Dict[str, Any], fix: bool):
		"""Display analysis results.

		Args:
			strategy_name: Strategy name
			strategy_data: Strategy configuration
			issues: Issues found
			fix: Whether fix mode is enabled
		"""
		# Define indicators
		defined_indicators = strategy_data.get("indicators", [])

		# Create summary table
		summary_table = Table(title="Strategy Check Summary", box=box.ROUNDED)
		summary_table.add_column("Category", style="cyan")
		summary_table.add_column("Count", justify="right")
		summary_table.add_column("Status", justify="right")

		total_issues = len(issues["missing_keys"]) + len(issues["invalid_indicators"]) + len(issues["invalid_formulas"])
		
		summary_table.add_row(
			"Missing Keys",
			str(len(issues["missing_keys"])),
			"[red]✗[/red]" if issues["missing_keys"] else "[green]✓[/green]"
		)
		summary_table.add_row(
			"Undefined Indicators",
			str(len(issues["invalid_indicators"])),
			"[red]✗[/red]" if issues["invalid_indicators"] else "[green]✓[/green]"
		)
		summary_table.add_row(
			"Formula Errors",
			str(len(issues["invalid_formulas"])),
			"[red]✗[/red]" if issues["invalid_formulas"] else "[green]✓[/green]"
		)
		summary_table.add_row(
			"Defined Indicators",
			str(len(defined_indicators)),
			"[blue]ℹ[/blue]"
		)
		
		console.print(summary_table)
		console.print()

		# Display missing keys
		if issues["missing_keys"]:
			console.print("[bold red]Missing Keys:[/bold red]")
			for key in issues["missing_keys"]:
				console.print(f"  • {key}")
			console.print()

		# Display undefined indicators
		if issues["invalid_indicators"]:
			console.print("[bold red]Undefined Indicators (used but not in indicators list):[/bold red]")
			for item in issues["invalid_indicators"]:
				console.print(f"  • [yellow]{item['indicator']}[/yellow] - {item['message']}")
			if fix:
				console.print("  [green]✓ Will be added to indicators list[/green]")
			console.print()

		# Display formula errors
		if issues["invalid_formulas"]:
			console.print("[bold red]Formula Errors:[/bold red]")
			for item in issues["invalid_formulas"]:
				console.print(f"  • {item['location']}: {item['error']}")
				console.print(f"    Formula: {item['formula']}")
			console.print()

		# Display defined indicators
		if defined_indicators:
			console.print("[bold cyan]Defined Indicators ({}):[/bold cyan]".format(len(defined_indicators)))
			# Create grid of indicators
			for i in range(0, len(defined_indicators), 3):
				chunk = defined_indicators[i:i+3]
				console.print("  " + "  |  ".join(f"[blue]{ind}[/blue]" for ind in chunk))
			console.print()

		# Summary
		if total_issues == 0:
			console.print("[bold green]✓ Strategy is valid and ready to use[/bold green]\n")
		else:
			console.print(f"[bold yellow]⚠ Found {total_issues} issue(s)[/bold yellow]")
			if not fix:
				console.print("  Use [bold]--fix[/bold] flag to automatically add undefined indicators\n")

	def _fix_strategy(self, strategy_name: str, strategy_data: Dict[str, Any], issues: Dict[str, Any]):
		"""Attempt to fix identified issues.

		Args:
			strategy_name: Strategy name
			strategy_data: Strategy configuration
			issues: Issues found
		"""
		console.print("\n[bold cyan]Attempting fixes...[/bold cyan]\n")

		fixed_count = 0

		# Fix undefined indicators
		if issues["invalid_indicators"]:
			console.print("[bold]Adding undefined indicators to indicators list:[/bold]")
			current_indicators = set(strategy_data.get("indicators", []))
			added_indicators = []

			for item in issues["invalid_indicators"]:
				indicator = item["indicator"]
				if indicator not in current_indicators:
					strategy_data.setdefault("indicators", []).append(indicator)
					added_indicators.append(indicator)
					fixed_count += 1

			for ind in sorted(added_indicators):
				console.print(f"  • Added: [green]{ind}[/green]")
			console.print()

		# Save fixed strategy
		if fixed_count > 0:
			try:
				self.strategy_manager.save_strategy(strategy_name, strategy_data)
				console.print(f"[bold green]✓ Strategy saved with {fixed_count} fix(es)[/bold green]\n")
			except Exception as e:
				console.print(f"[bold red]✗ Failed to save strategy: {e}[/bold red]\n")
		else:
			console.print("[yellow]No automatic fixes available[/yellow]\n")


class StrategyCommands:
	"""CLI commands for strategy management."""

	def __init__(self, project_root: Path):
		"""Initialize strategy commands.

		Args:
			project_root: Root directory of the project
		"""
		self.project_root = project_root
		self.validator = StrategyValidator(project_root)

	def check(self, strategy_name: str, fix: bool = False, template: bool = False) -> Dict[str, Any]:
		"""Check strategy configuration for compliance with template.

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

		# Use StrategyManager's new check_strategy function
		result = self.validator.strategy_manager.check_strategy(strategy_name)

		# Display results
		self._display_check_results(strategy_name, result)

		# Fix if requested
		if fix and result.get("issues"):
			self._handle_fix(strategy_name)

		return result

	def _show_template(self):
		"""Display the strategy template."""
		console.print("\n[bold cyan]Strategy Template[/bold cyan]\n")
		try:
			template_file = self.validator.strategy_manager.project_root / "init" / "templates" / "strategy.yml"
			if template_file.exists():
				with open(template_file, 'r') as f:
					content = f.read()
				console.print(content)
			else:
				console.print("[yellow]Template file not found[/yellow]")
		except Exception as e:
			console.print(f"[red]Error loading template: {e}[/red]")

	def _display_check_results(self, strategy_name: str, result: Dict[str, Any]):
		"""Display strategy check results.

		Args:
			strategy_name: Strategy name
			result: Check result from StrategyManager
		"""
		console.print(f"\n[bold cyan]Strategy Compliance Check: {strategy_name}[/bold cyan]\n")

		if result.get("valid"):
			console.print("[bold green]✓ Strategy is compliant with template[/bold green]\n")
		else:
			console.print(f"[bold red]✗ {result.get('issue_count', 0)} issue(s) found:[/bold red]\n")

			# Display issues in a table
			issues_table = Table(title="Issues Found", box=box.ROUNDED)
			issues_table.add_column("Issue", style="yellow")

			for issue in result.get("issues", []):
				issues_table.add_row(issue)

			console.print(issues_table)
			console.print()
			console.print("[cyan]Use[/cyan] [bold]--fix[/bold] [cyan]to automatically fix issues[/cyan]\n")

	def _handle_fix(self, strategy_name: str):
		"""Handle strategy fix operation.

		Args:
			strategy_name: Strategy name to fix
		"""
		console.print(f"\n[bold cyan]Fixing strategy: {strategy_name}[/bold cyan]\n")

		result = self.validator.strategy_manager.fix_strategy(strategy_name, dry_run=False)

		if result.get("status") == "success":
			console.print("[bold green]✓ Strategy fixed[/bold green]\n")
			for change in result.get("changes", []):
				console.print(f"  • {change}")
			console.print()
		else:
			console.print(f"[bold red]✗ Fix failed: {result.get('message')}[/bold red]\n")
