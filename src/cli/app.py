"""Cresus CLI application - main entry point."""

import os
import json
import cmd2
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

# Import command handlers
from cli.commands.service import ServiceManager
from cli.commands.flow import FlowManager
from cli.commands.data import DataCommands
from cli.commands.portfolio import PortfolioCommands
from cli.commands.scheduler import SchedulerCommands
from cli.commands.info import InfoCommands
from tools.data.manager import DataManager

console = Console()


class CresusCLI(cmd2.Cmd):
	"""Cresus portfolio management CLI."""

	intro = ""

	def __init__(self, interactive: bool = True):
		super().__init__()
		self.interactive = interactive
		self.project_root = self._find_project_root()
		os.environ["CRESUS_PROJECT_ROOT"] = str(self.project_root)

		# Initialize command handlers
		self.service_manager = ServiceManager(self.project_root)
		self.flow_manager = FlowManager(self.project_root)
		self.data_manager = DataManager(self.project_root)
		self.data_commands = DataCommands(self.data_manager)
		self.portfolio_commands = PortfolioCommands()
		self.scheduler_commands = SchedulerCommands()
		self.info_commands = InfoCommands()

		self._setup_history()
		self._setup_prompt()

		# Only print intro in interactive mode
		if self.interactive:
			self._print_intro()

	def _setup_prompt(self):
		"""Set up dynamic prompt with context."""
		self.prompt = "cresus> "

	def _print_intro(self):
		"""Print welcome banner."""
		banner = Panel(
			Text("Cresus CLI v1.0.0\nPortfolio Management Service", justify="center", style="bold cyan"),
			style="cyan",
			box=box.DOUBLE
		)
		console.print(banner)

		# Print helpful info
		info_table = Table(box=box.SIMPLE)
		info_table.add_column("Command", style="cyan")
		info_table.add_column("Description")
		info_table.add_row("[bold]help[/bold]", "Show all available commands")
		info_table.add_row("[bold]service[/bold]", "Manage services (api, mcp, front)")
		info_table.add_row("[bold]flow[/bold]", "Execute workflows (e.g., flow run watchlist)")
		info_table.add_row("[bold]data[/bold]", "Manage portfolio data and cache")
		info_table.add_row("[bold]watchlist[/bold]", "View strategy watchlist (e.g., watchlist show momentum_cac)")
		info_table.add_row("[bold]orders[/bold]", "View pending/executed orders (e.g., orders list momentum_cac)")
		info_table.add_row("[bold]cron[/bold]", "View scheduled cron jobs and next run times")
		info_table.add_row("[bold]status[/bold]", "Show system status")
		info_table.add_row("[bold]update[/bold]", "Update cresus from git (background)")
		info_table.add_row("[bold]history[/bold]", "View command history")
		info_table.add_row("[bold]quit[/bold] or [bold]exit[/bold]", "Exit the CLI")

		console.print(info_table)
		console.print(f"\n[dim]Project Root:[/dim] {self.project_root}")
		console.print("[dim]Command history is saved to ~/.cresus/history[/dim]\n")

	def _find_project_root(self) -> Path:
		"""Find project root by looking for config/cresus.yml."""
		cwd = Path.cwd().resolve()
		for p in [cwd, cwd.parent, cwd.parent.parent]:
			if (p / "config" / "cresus.yml").exists():
				return p
		return cwd

	def _setup_history(self):
		"""Set up persistent command history."""
		history_dir = Path.home() / ".cresus"
		history_dir.mkdir(exist_ok=True)

		history_file = history_dir / "history"
		self.persistent_history_file = str(history_file)

		# Configure cmd2 history settings
		self.history_file = str(history_file)
		self.max_history_length = 1000
		self.debug_mode = False

		# Load existing history if available
		if history_file.exists():
			try:
				with open(history_file, 'r') as f:
					lines = f.readlines()
					console.print(f"[dim]Loaded {len(lines)} command(s) from history[/dim]")
			except Exception as e:
				console.print(f"[yellow]Warning:[/yellow] Could not load history: {e}")

	# ==================== Service Commands ====================
	def do_service(self, args):
		"""Manage services: start|stop|status|logs [service] [-d]"""
		args_str = str(args).strip() if args else ""

		if not args_str:
			table = Table(title="Service Management Commands", box=box.ROUNDED)
			table.add_column("Command", style="cyan")
			table.add_column("Description")
			table.add_row("service start <api|mcp|front|all> [-d]", "Start service(s)")
			table.add_row("service stop <api|mcp|front|all>", "Stop service(s)")
			table.add_row("service status [service]", "Check service status")
			table.add_row("service logs <api|mcp|front> [-f] [lines]", "View service logs")
			console.print(table)
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None

		if cmd == "start":
			service_names = parts[1] if len(parts) > 1 else "all"
			background = "-d" in parts
			self.service_manager.start_services(service_names, background=background)
		elif cmd == "stop":
			service_names = parts[1] if len(parts) > 1 else "all"
			self.service_manager.stop_services(service_names)
		elif cmd == "status":
			service_name = parts[1] if len(parts) > 1 else None
			self.service_manager.check_status(service_name)
		elif cmd == "logs":
			if len(parts) < 2:
				console.print("[red]✗[/red] Usage: service logs <service> [-f] [lines]")
				return
			service_name = parts[1]
			follow = "-f" in parts
			lines = None
			for part in parts:
				if part.isdigit():
					lines = int(part)
					break
			self.service_manager.view_logs(service_name, follow=follow, lines=lines)
		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			console.print("Try: service start|stop|status|logs")

	# ==================== Flow/Workflow Commands ====================
	def do_flow(self, args):
		"""Execute workflows: run <workflow_name> [strategy] [tickers...] [--context] [--debug]"""
		args_str = str(args).strip() if args else ""

		if not args_str:
			table = Table(title="Workflow Management Commands", box=box.ROUNDED)
			table.add_column("Command", style="cyan")
			table.add_column("Description")
			table.add_row("flow list", "List available workflows")
			table.add_row("flow run premarket <strategy>", "Generate pending orders")
			table.add_row("flow run transact <portfolio> [date]", "Execute pending orders (default: today)")
			table.add_row("flow run backtest <strategy> [start_date] [end_date]", "Backtest strategy over date range (YYYY-MM-DD format)")
			table.add_row("flow run portfolio_analysis <strategy> [--backtest]", "Analyze portfolio or most recent backtest")
			table.add_row("flow run <workflow> [strategy] [tickers...]", "Run a workflow")
			table.add_row("flow run <workflow> [strategy] [--context]", "Run workflow and display context")
			table.add_row("flow run <workflow> [strategy] [--debug]", "Run workflow with debug logging enabled")
			console.print(table)
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None

		if cmd == "list":
			result = self.flow_manager.list_workflows()
			self.flow_manager._print_workflows_result(result)
		elif cmd == "run":
			if len(parts) < 2:
				console.print("[red]✗[/red] Usage: flow run <workflow_name> [strategy] [tickers...] [--context] [--debug] [--backtest]")
				return

			workflow_name = parts[1]
			include_context = "--context" in parts
			debug = "--debug" in parts
			use_backtest = "--backtest" in parts

			# Remove workflow name and flags from parts
			remaining = [p for p in parts[2:] if not p.startswith("--")]

			# First remaining item is strategy, rest depends on workflow type
			strategy = remaining[0] if remaining else "default_strategy"
			input_data = None

			# Special handling for market_regime workflow (JSON payload)
			if workflow_name.lower() == "market_regime":
				# Try to parse remaining args as JSON if they look like JSON
				if remaining:
					potential_json = " ".join(remaining)
					if potential_json.strip().startswith("{"):
						try:
							input_data = json.loads(potential_json)
							strategy = None  # market_regime doesn't use strategy parameter
						except json.JSONDecodeError as e:
							console.print(f"[red]✗[/red] Invalid JSON payload: {e}")
							return
					else:
						console.print("[red]✗[/red] market_regime requires JSON payload (e.g., '{\"universe\": \"etf_pea\", \"action\": \"train\"}')")
						return
			# Special handling for backtest workflow (dates instead of tickers)
			elif workflow_name.lower() == "backtest":
				input_data = {}
				if len(remaining) > 1:
					input_data["start_date"] = remaining[1]
				if len(remaining) > 2:
					input_data["end_date"] = remaining[2]
			elif workflow_name.lower() in ["premarket", "transact"]:
				input_data = None
			else:
				# For other workflows, treat remaining items as tickers
				tickers = remaining[1:] if len(remaining) > 1 else None
				if tickers:
					input_data = {"tickers": tickers}

			result = self.flow_manager.run_workflow(workflow_name, strategy, input_data, include_context, debug, use_backtest)
			self.flow_manager._print_flow_result(result, workflow_name)

			# Display backtest results if backtest completed successfully
			if workflow_name.lower() == "backtest" and result.get("status") == "success":
				self._print_backtest_results(strategy, result)
		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			console.print("Try: flow list|run")

	# ==================== Data Commands ====================
	def do_data(self, args):
		"""Manage historical and fundamental data: fetch|list|clear|stats|show [options]"""
		self.data_commands.handle(args)

	# ==================== Portfolio Commands ====================
	def do_watchlist(self, args):
		"""Display watchlist: watchlist show|extended <strategy>"""
		self.portfolio_commands.handle_watchlist(args)

	def do_orders(self, args):
		"""Manage orders: list <strategy>"""
		self.portfolio_commands.handle_orders(args)

	# ==================== Scheduler Commands ====================
	def do_cron(self, args):
		"""Manage cron jobs: list"""
		self.scheduler_commands.handle(args)

	# ==================== Info Commands ====================
	def do_status(self, _):
		"""Show system status."""
		self.info_commands.handle_status()

	def do_info(self, _):
		"""Show application info."""
		self.info_commands.handle_info()

	# ==================== Utility Commands ====================
	def do_history(self, args):
		"""View command history."""
		console.print("[dim]Command history saved to ~/.cresus/history[/dim]")

	def do_clear(self, _):
		"""Clear the screen."""
		import os
		os.system("clear" if os.name != "nt" else "cls")

	def do_motd(self, _):
		"""Display message of the day."""
		self._print_intro()

	def do_pwd(self, _):
		"""Print working directory."""
		console.print(str(self.project_root))

	def do_update(self, _):
		"""Update cresus from git repository (runs in background)."""
		import subprocess
		import threading

		def run_git_pull():
			try:
				result = subprocess.run(
					["git", "pull"],
					cwd=str(self.project_root),
					capture_output=True,
					text=True,
					timeout=60
				)

				if result.returncode == 0:
					console.print("[green]✓ Update completed successfully[/green]")
					if result.stdout:
						console.print(f"[dim]{result.stdout}[/dim]")
				else:
					console.print(f"[red]✗ Update failed with exit code {result.returncode}[/red]")
					if result.stderr:
						console.print(f"[red]{result.stderr}[/red]")
			except subprocess.TimeoutExpired:
				console.print("[red]✗ Update timed out after 60 seconds[/red]")
			except Exception as e:
				console.print(f"[red]✗ Update error: {e}[/red]")

		# Run git pull in background thread
		thread = threading.Thread(target=run_git_pull, daemon=True)
		thread.start()
		console.print("[cyan]Updating cresus from git repository...[/cyan]")

	def do_quit(self, _):
		"""Exit the CLI."""
		console.print("[cyan]Goodbye![/cyan]")
		return True

	def _print_backtest_results(self, strategy: str, result: dict):
		"""Display backtest portfolio performance metrics."""
		try:
			output = result.get("output", {})
			metrics = output.get("portfolio_metrics", {})

			if not metrics:
				return

			console.print(f"\n{'='*100}")
			console.print(f"[bold cyan]Portfolio Performance: {strategy}[/bold cyan]")
			console.print(f"{'='*100}\n")

			# Format metrics similar to vectorbt stats() output
			metrics_display = [
				("Start", metrics.get("start_date", "N/A"), ""),
				("End", metrics.get("end_date", "N/A"), ""),
				("Period", f"{metrics.get('period_days', 0)} days", ""),
				("", "", ""),
				("Start Value", f"${metrics.get('start_value', 0):.2f}", ""),
				("End Value", f"${metrics.get('end_value', 0):.2f}", ""),
				("Total Return", f"{metrics.get('total_return_pct', 0):.2f}", "%"),
				("Benchmark Return", f"{metrics.get('benchmark_return_pct', 0):.2f}", "%"),
				("Max Gross Exposure", f"{metrics.get('max_gross_exposure_pct', 0):.2f}", "%"),
				("Total Fees Paid", f"${metrics.get('total_fees_paid', 0):.2f}", ""),
				("", "", ""),
				("Max Drawdown", f"{metrics.get('max_drawdown_pct', 0):.2f}", "%"),
				("Max Drawdown Duration", f"{metrics.get('max_drawdown_duration_days', 0)} days", ""),
				("", "", ""),
				("Total Trades", f"{metrics.get('total_trades', 0):.0f}", ""),
				("Closed Trades", f"{metrics.get('closed_trades', 0):.0f}", ""),
				("Open Trades", f"{metrics.get('open_trades', 0):.0f}", ""),
				("Open Trade PnL", f"${metrics.get('open_trade_pnl', 0):.2f}", ""),
				("", "", ""),
				("Win Rate", f"{metrics.get('win_rate_pct', 0):.2f}", "%"),
				("Best Trade", f"{metrics.get('best_trade_pct', 0):.2f}", "%"),
				("Worst Trade", f"{metrics.get('worst_trade_pct', 0):.2f}", "%"),
				("Avg Winning Trade", f"{metrics.get('avg_winning_trade_pct', 0):.2f}", "%"),
				("Avg Losing Trade", f"{metrics.get('avg_losing_trade_pct', 0):.2f}", "%"),
				("", "", ""),
				("Avg Winning Trade Duration", f"{metrics.get('avg_winning_trade_duration_days', 0):.1f} days", ""),
				("Avg Losing Trade Duration", f"{metrics.get('avg_losing_trade_duration_days', 0):.1f} days", ""),
				("", "", ""),
				("Profit Factor", f"{metrics.get('profit_factor', 0):.6f}", ""),
				("Expectancy", f"{metrics.get('expectancy_pct', 0):.6f}", "%"),
				("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.6f}", ""),
				("Calmar Ratio", f"{metrics.get('calmar_ratio', 0):.6f}", ""),
				("Omega Ratio", f"{metrics.get('omega_ratio', 0):.6f}", ""),
				("Sortino Ratio", f"{metrics.get('sortino_ratio', 0):.6f}", ""),
			]

			# Print in aligned columns
			for metric_name, value, unit in metrics_display:
				if not metric_name:  # Empty line
					console.print()
				else:
					if unit:
						print(f"{metric_name:<35} {value:>20} {unit}")
					else:
						print(f"{metric_name:<35} {value:>20}")

			console.print(f"\n{'='*100}\n")

		except Exception as e:
			console.print(f"[yellow]⚠ Could not display backtest results: {e}[/yellow]")
