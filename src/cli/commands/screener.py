"""CLI commands for managing screeners."""

from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from src.tools.screener import ScreenerConfig, ScreenerManager

console = Console()


class ScreenerCommand:
	"""Screener management commands."""

	def __init__(self):
		"""Initialize screener commands."""
		self.manager = ScreenerManager()

	def list(self):
		"""List all screeners."""
		screeners = self.manager.list_screeners()

		if not screeners:
			console.print("[yellow]No screeners found[/yellow]")
			return

		table = Table(title="Screeners")
		table.add_column("Name", style="cyan")
		table.add_column("Source", style="magenta")
		table.add_column("Indicators", style="green")
		table.add_column("Description", style="blue")

		for name in screeners:
			config = self.manager.get_screener(name)
			if config:
				source = config.source or f"Custom ({len(config.tickers)} tickers)"
				indicators = ", ".join(config.indicators[:3])
				if len(config.indicators) > 3:
					indicators += f", +{len(config.indicators) - 3} more"
				table.add_row(
					name,
					source,
					indicators,
					config.description[:50] if config.description else "-"
				)

		console.print(table)

	def info(self, name: str):
		"""Display screener information.

		Args:
			name: Screener name
		"""
		config = self.manager.get_screener(name)
		if not config:
			console.print(f"[red]Screener '{name}' not found[/red]")
			return

		table = Table(title=f"Screener: {name}")
		table.add_column("Property", style="cyan")
		table.add_column("Value", style="green")

		table.add_row("Name", config.name)
		table.add_row("Source", config.source or "Custom")
		table.add_row(
			"Tickers",
			", ".join(config.tickers) if config.tickers else "-"
		)
		table.add_row("Indicators", ", ".join(config.indicators))
		table.add_row("Formula", config.formula)
		table.add_row("Description", config.description or "-")
		table.add_row("Actions", str(config.actions) if config.actions else "None")

		console.print(table)

		# Show recent results
		results = self.manager.list_results(name)
		if results:
			console.print(f"\n[bold]Recent Results:[/bold]")
			results_table = Table()
			results_table.add_column("Result ID", style="cyan")
			results_table.add_column("Timestamp", style="green")
			results_table.add_column("Matches", style="magenta")

			for result_id, timestamp in results[:10]:
				result_data = self.manager.get_result(name, result_id)
				match_count = len(result_data) if result_data else 0
				results_table.add_row(
					result_id,
					timestamp.strftime("%Y-%m-%d %H:%M:%S"),
					str(match_count)
				)

			console.print(results_table)

	def create(
		self,
		name: str,
		formula: str,
		indicators: str,
		source: Optional[str] = None,
		tickers: Optional[str] = None,
		description: Optional[str] = None,
		actions: Optional[str] = None
	):
		"""Create a new screener.

		Args:
			name: Screener name
			formula: Filter formula
			indicators: Comma-separated indicator names
			source: Source universe (e.g., cac40, nasdaq_100)
			tickers: Comma-separated ticker list
			description: Screener description
			actions: JSON string for actions
		"""
		indicator_list = [i.strip() for i in indicators.split(",")]
		ticker_list = [t.strip() for t in tickers.split(",")] if tickers else None

		# Parse actions if provided
		action_dict = {}
		if actions:
			import json
			try:
				action_dict = json.loads(actions)
			except json.JSONDecodeError:
				console.print("[red]Invalid JSON in actions[/red]")
				return

		config = ScreenerConfig(
			name=name,
			source=source,
			tickers=ticker_list,
			indicators=indicator_list,
			formula=formula,
			description=description or "",
			actions=action_dict
		)

		success, message = self.manager.create_screener(config)
		if success:
			console.print(f"[green]✓ {message}[/green]")
		else:
			console.print(f"[red]✗ {message}[/red]")

	def edit(self, name: str):
		"""Edit a screener configuration.

		Args:
			name: Screener name
		"""
		config = self.manager.get_screener(name)
		if not config:
			console.print(f"[red]Screener '{name}' not found[/red]")
			return

		console.print(f"[cyan]Editing screener: {name}[/cyan]")
		console.print("Press Ctrl+C to cancel, Ctrl+D to save")

		# Interactive editing - would need integration with user input
		# For now, show what can be edited
		fields = {
			"description": config.description,
			"formula": config.formula,
			"source": config.source or "custom",
		}

		for key, value in fields.items():
			console.print(f"{key}: {value}")

		console.print("[yellow]Interactive editing not yet implemented[/yellow]")

	def delete(self, name: str, confirm: bool = False):
		"""Delete a screener.

		Args:
			name: Screener name
			confirm: Skip confirmation
		"""
		if not confirm:
			response = console.input(f"Delete screener '{name}'? (yes/no): ").lower()
			if response != "yes":
				console.print("[yellow]Cancelled[/yellow]")
				return

		success, message = self.manager.delete_screener(name)
		if success:
			console.print(f"[green]✓ {message}[/green]")
		else:
			console.print(f"[red]✗ {message}[/red]")

	def run(self, name: str):
		"""Run a screener and display results.

		Args:
			name: Screener name
		"""
		config = self.manager.get_screener(name)
		if not config:
			console.print(f"[red]Screener '{name}' not found[/red]")
			return

		console.print(f"[cyan]Running screener: {name}[/cyan]")

		# Use ScreenerAgent to run the screener
		try:
			from agents.screener import ScreenerAgent
			from core.context import AgentContext

			agent = ScreenerAgent("ScreenerAgent", AgentContext())
			result = agent.process({
				"screener_name": name,
				"screener_config": config
			})

			if result.get("status") == "success":
				message = result.get("message", "Screening complete")
				console.print(f"[green]✓ {message}[/green]")

				# Display results summary
				matches = result.get("matches", [])
				match_count = result.get("match_count", 0)

				if matches:
					console.print(f"\n[bold]Top matches (showing first 10 of {match_count}):[/bold]")

					# Create table with results
					table = Table(title=f"Screener Results: {name}")
					table.add_column("Date", style="cyan")
					table.add_column("Ticker", style="blue", no_wrap=True)
					table.add_column("Name", style="green")
					table.add_column("Close", justify="right", style="yellow")
					table.add_column("Volume", justify="right", style="magenta")

					for i, row in enumerate(matches[:10]):
						table.add_row(
							row.get("date", "-"),
							row.get("ticker", "-"),
							row.get("name", "-")[:30],
							f"{float(row.get('close', 0)):.2f}" if row.get("close") else "-",
							f"{float(row.get('volume', 0)):,.0f}" if row.get("volume") else "-",
						)

					console.print(table)
					console.print(f"\n[dim]Processed {result.get('tickers_processed', 0)} tickers, skipped {result.get('tickers_skipped', 0)}[/dim]")
			else:
				console.print(f"[red]✗ Error: {result.get('message', 'Unknown error')}[/red]")

		except Exception as e:
			console.print(f"[red]✗ Error running screener: {str(e)}[/red]")

	def results(self, name: str, limit: Optional[int] = None):
		"""List results for a screener.

		Args:
			name: Screener name
			limit: Maximum number of results to show
		"""
		config = self.manager.get_screener(name)
		if not config:
			console.print(f"[red]Screener '{name}' not found[/red]")
			return

		results = self.manager.list_results(name)
		if not results:
			console.print(f"[yellow]No results for screener '{name}'[/yellow]")
			return

		if limit:
			results = results[:limit]

		table = Table(title=f"Results for: {name}")
		table.add_column("Result ID", style="cyan")
		table.add_column("Timestamp", style="green")
		table.add_column("Matches", style="magenta")

		for result_id, timestamp in results:
			result_data = self.manager.get_result(name, result_id)
			match_count = len(result_data) if result_data else 0
			table.add_row(
				result_id,
				timestamp.strftime("%Y-%m-%d %H:%M:%S"),
				str(match_count)
			)

		console.print(table)

	def result_show(self, name: str, result_id: str):
		"""Display a specific result.

		Args:
			name: Screener name
			result_id: Result identifier
		"""
		result_data = self.manager.get_result(name, result_id)
		if not result_data:
			console.print(f"[red]Result '{result_id}' not found[/red]")
			return

		if not result_data:
			console.print("[yellow]No matches[/yellow]")
			return

		table = Table(title=f"Result: {result_id}")

		# Add columns dynamically based on first row
		if result_data:
			for key in result_data[0].keys():
				table.add_column(key, style="cyan")

			for row in result_data[:100]:  # Limit to 100 rows for display
				table.add_row(*[str(v) for v in row.values()])

		console.print(table)

	def result_delete(self, name: str, result_id: str, confirm: bool = False):
		"""Delete a result.

		Args:
			name: Screener name
			result_id: Result identifier
			confirm: Skip confirmation
		"""
		if not confirm:
			response = console.input(f"Delete result '{result_id}'? (yes/no): ").lower()
			if response != "yes":
				console.print("[yellow]Cancelled[/yellow]")
				return

		success, message = self.manager.delete_result(name, result_id)
		if success:
			console.print(f"[green]✓ {message}[/green]")
		else:
			console.print(f"[red]✗ {message}[/red]")

	def clear_results(self, name: str, confirm: bool = False):
		"""Clear all results for a screener.

		Args:
			name: Screener name
			confirm: Skip confirmation
		"""
		if not confirm:
			response = console.input(f"Clear all results for '{name}'? (yes/no): ").lower()
			if response != "yes":
				console.print("[yellow]Cancelled[/yellow]")
				return

		success, message = self.manager.clear_results(name)
		if success:
			console.print(f"[green]✓ {message}[/green]")
		else:
			console.print(f"[red]✗ {message}[/red]")

	def export(self, name: str, result_id: str, output_path: str):
		"""Export result to file.

		Args:
			name: Screener name
			result_id: Result identifier
			output_path: Output file path
		"""
		import shutil

		source_file = (
			self.manager._get_results_dir(name) / f"{result_id}.csv"
		)

		if not source_file.exists():
			console.print(f"[red]Result '{result_id}' not found[/red]")
			return

		try:
			shutil.copy(source_file, output_path)
			console.print(f"[green]✓ Exported to {output_path}[/green]")
		except Exception as e:
			console.print(f"[red]✗ Error exporting: {e}[/red]")


def get_screener_command() -> ScreenerCommand:
	"""Get screener command instance."""
	return ScreenerCommand()
