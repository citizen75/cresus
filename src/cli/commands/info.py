"""Information commands (status, info, etc)."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


class InfoCommands:
	"""Information command handlers."""

	def handle_status(self):
		"""Handle status command."""
		console.print(Panel(
			Text("Cresus Gateway Status", justify="center", style="bold cyan"),
			style="cyan",
			title="Status",
		))
		console.print("[green]✓[/green] API Server: Running")
		console.print("[green]✓[/green] MCP Server: Running")
		console.print("[yellow]⧗[/yellow] Cron Scheduler: Enabled")

	def handle_info(self):
		"""Handle info command."""
		console.print(Panel(
			Text("Cresus v1.0.0\nAlgorithmic Trading System", justify="center", style="bold cyan"),
			style="cyan",
			title="About",
		))
		console.print("Multi-agent trading system with ML-powered strategy execution")
		console.print("Type [cyan]help[/cyan] for available commands")
