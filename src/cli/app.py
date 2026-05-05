"""Cresus CLI application."""

import os
import cmd2
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from cli.commands.service import ServiceManager
from cli.commands.flow import FlowManager
from tools.data.manager import DataManager

console = Console()


class CresusCLI(cmd2.Cmd):
	"""Cresus portfolio management CLI."""

	intro = ""

	def __init__(self):
		super().__init__()
		self.project_root = self._find_project_root()
		os.environ["CRESUS_PROJECT_ROOT"] = str(self.project_root)
		self.service_manager = ServiceManager(self.project_root)
		self.flow_manager = FlowManager(self.project_root)
		self.data_manager = DataManager(self.project_root)
		self._setup_history()
		self._setup_prompt()
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

	def do_service(self, args):
		"""Manage services: start|stop|status|logs [service] [-d]"""
		args_str = str(args).strip() if args else ""

		if not args_str:
			table = Table(title="Service Management Commands", box=box.ROUNDED)
			table.add_column("Command", style="cyan")
			table.add_column("Description")
			table.add_row("service start <api|mcp|front|all> [-d]", "Start service(s)")
			table.add_row("service stop <api|mcp|front|all>", "Stop service(s)")
			table.add_row("service status [service]", "Show status")
			table.add_row("service logs <service> [lines]", "Show logs")
			console.print(table)
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None
		service = parts[1] if len(parts) > 1 else None
		daemon = "-d" in parts

		if cmd == "start":
			if not service:
				console.print("[red]✗[/red] Usage: service start <api|mcp|front|all> [-d]")
				return
			if service == "all":
				for svc in ["gateway", "front"]:
					result = self.service_manager.start(svc, daemon)
					svc_status = result.get("status", "error") if isinstance(result, dict) else str(result)
					is_success = svc_status in ["started", "already_running"]
					status = "[green]✓[/green]" if is_success else "[red]✗[/red]"
					msg = f"{svc}: {svc_status}"
					if result.get("pid"):
						msg += f" (PID: {result.get('pid')})"
					console.print(f"{status} {msg}")
			else:
				result = self.service_manager.start(service, daemon)
				svc_status = result.get("status", "error") if isinstance(result, dict) else str(result)
				is_success = svc_status in ["started", "already_running"]
				status = "[green]✓[/green]" if is_success else "[red]✗[/red]"
				msg = f"{service}: {svc_status}"
				if result.get("pid"):
					msg += f" (PID: {result.get('pid')})"
				console.print(f"{status} {msg}")

		elif cmd == "stop":
			if not service:
				console.print("[red]✗[/red] Usage: service stop <api|mcp|front|all>")
				return
			if service == "all":
				for svc in ["api", "mcp", "front"]:
					result = self.service_manager.stop(svc)
					svc_status = result.get("status", "error") if isinstance(result, dict) else str(result)
					is_success = svc_status == "stopped"
					status = "[green]✓[/green]" if is_success else "[red]✗[/red]"
					console.print(f"{status} {svc}: {svc_status}")
			else:
				result = self.service_manager.stop(service)
				svc_status = result.get("status", "error") if isinstance(result, dict) else str(result)
				is_success = svc_status == "stopped"
				status = "[green]✓[/green]" if is_success else "[red]✗[/red]"
				console.print(f"{status} {service}: {svc_status}")

		elif cmd == "status":
			status = self.service_manager.status(service)
			self._print_service_status(status)

		elif cmd == "logs":
			if not service:
				console.print("[red]✗[/red] Usage: service logs <service> [lines]")
				return
			lines = int(parts[2]) if len(parts) > 2 else 20
			logs = self.service_manager.logs(service, lines)
			console.print(Panel(logs, title=f"Logs: {service}", expand=False))

		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			console.print("Try: service start|stop|status|logs")

	def _print_service_status(self, status: dict):
		"""Print service status as a formatted table."""
		table = Table(title="System Status", box=box.ROUNDED)
		table.add_column("Service", style="cyan")
		table.add_column("Status", style="bold")

		for svc, info in status.items():
			status_text = info.get("status", "unknown")
			if status_text == "running":
				status_display = Text("●", style="green") + Text(f" {status_text}")
			else:
				status_display = Text("●", style="red") + Text(f" {status_text}")
			table.add_row(svc, status_display)

		console.print(table)

	def do_status(self, _):
		"""Show overall system status."""
		status = self.service_manager.status()
		self._print_service_status(status)

	def do_info(self, _):
		"""Show project info."""
		panel = Panel(
			f"[cyan]Project Root:[/cyan] {self.project_root}",
			style="cyan",
			box=box.ROUNDED
		)
		console.print(panel)

	def do_data(self, args):
		"""Manage historical and fundamental data: fetch|list|clear|stats [options]"""
		args_str = str(args).strip() if args else ""

		if not args_str:
			table = Table(title="Data Management Commands", box=box.ROUNDED)
			table.add_column("Command", style="cyan")
			table.add_column("Description")
			table.add_row("data fetch history <ticker> [start_date]", "Fetch historical data")
			table.add_row("data fetch fundamental <ticker>", "Fetch fundamental data")
			table.add_row("data fetch universe <name> [start_date]", "Fetch all tickers in universe")
			table.add_row("data fetch all <universe> [start_date]", "Fetch history + fundamental for universe")
			table.add_row("data list [history|fundamentals|all]", "List cached data")
			table.add_row("data clear [type] [ticker]", "Clear cache (types: history, fundamentals, all)")
			table.add_row("data stats", "Show cache statistics")
			table.add_row("data universes", "List available universes")
			console.print(table)
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None

		if cmd == "fetch":
			if len(parts) < 3:
				console.print("[red]✗[/red] Usage: data fetch <history|fundamental|universe|all> <ticker|name|universe> [start_date]")
				return
			data_type = parts[1]
			target = parts[2]
			start_date = parts[3] if len(parts) > 3 else None

			if data_type == "history":
				result = self.data_manager.fetch_history(target, start_date)
				self._print_result(result)
			elif data_type == "fundamental":
				result = self.data_manager.fetch_fundamental(target)
				self._print_result(result)
			elif data_type == "universe":
				result = self.data_manager.fetch_universe(target, start_date)
				self._print_universe_result(result)
			elif data_type == "all":
				result = self.data_manager.fetch_all(target, start_date)
				self._print_universe_result(result)
			else:
				console.print(f"[red]✗[/red] Unknown data type: {data_type}")

		elif cmd == "list":
			data_type = parts[1] if len(parts) > 1 else "all"
			result = self.data_manager.list_cached(data_type)
			self._print_list_result(result)

		elif cmd == "clear":
			data_type = parts[1] if len(parts) > 1 else "all"
			ticker = parts[2] if len(parts) > 2 else None
			result = self.data_manager.clear_cache(data_type, ticker)
			self._print_result(result)

		elif cmd == "stats":
			result = self.data_manager.cache_stats()
			self._print_stats_result(result)

		elif cmd == "universes":
			self._print_universes()

		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			console.print("Try: data fetch|list|clear|stats|universes")

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
			table.add_row("flow run <workflow> [strategy] [tickers...]", "Run a workflow")
			table.add_row("flow run <workflow> [strategy] [--context]", "Run workflow and display context")
			table.add_row("flow run <workflow> [strategy] [--debug]", "Run workflow with debug logging enabled")
			console.print(table)
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None

		if cmd == "list":
			result = self.flow_manager.list_workflows()
			self._print_workflows_result(result)

		elif cmd == "run":
			if len(parts) < 2:
				console.print("[red]✗[/red] Usage: flow run <workflow_name> [strategy] [tickers...] [--context] [--debug]")
				return

			workflow_name = parts[1]
			include_context = "--context" in parts
			debug = "--debug" in parts

			# Remove workflow name and flags from parts
			remaining = [p for p in parts[2:] if not p.startswith("--")]

			# First remaining item is strategy, rest depends on workflow type
			strategy = remaining[0] if remaining else "default_strategy"
			input_data = None

			# Special handling for backtest workflow (dates instead of tickers)
			if workflow_name.lower() == "backtest":
				input_data = {}
				if len(remaining) > 1:
					# Second argument is start_date
					input_data["start_date"] = remaining[1]
				if len(remaining) > 2:
					# Third argument is end_date
					input_data["end_date"] = remaining[2]
			else:
				# For other workflows, treat remaining items as tickers
				tickers = remaining[1:] if len(remaining) > 1 else None
				if tickers:
					input_data = {"tickers": tickers}

			result = self.flow_manager.run_workflow(workflow_name, strategy, input_data, include_context, debug)
			self._print_flow_result(result)

		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			console.print("Try: flow list|run")

	def _print_workflows_result(self, result):
		"""Print available workflows."""
		if result.get("status") == "error":
			panel = Panel(
				f"[red]✗[/red] {result.get('message')}",
				style="red",
				box=box.ROUNDED
			)
			console.print(panel)
			return

		workflows = result.get("workflows", [])
		if not workflows:
			panel = Panel(
				"[yellow]No workflows available[/yellow]",
				style="yellow",
				box=box.ROUNDED
			)
			console.print(panel)
			return

		table = Table(title=f"Available Workflows ({len(workflows)})", box=box.ROUNDED)
		table.add_column("Name", style="cyan")
		table.add_column("Description")
		table.add_column("Parameters", style="dim")

		for wf in workflows:
			params = ", ".join(wf.get("parameters", []))
			table.add_row(wf["name"], wf["description"], params)

		console.print(table)

	def _print_backtest_metrics(self, output):
		"""Print comprehensive backtest portfolio metrics."""
		console.print()
		
		# Backtest metadata
		metadata_table = Table(title="Backtest Period", box=box.ROUNDED)
		metadata_table.add_column("Property", style="cyan")
		metadata_table.add_column("Value", style="yellow")
		
		metadata_table.add_row("Start Date", output.get("start_date", "?"))
		metadata_table.add_row("End Date", output.get("end_date", "?"))
		metadata_table.add_row("Period", f"{output.get('period_days', 0)} days")
		metadata_table.add_row("Backtest ID", output.get("backtest_id", "?"))
		
		console.print(metadata_table)

		# Performance summary
		console.print()
		perf_table = Table(title="Performance Summary", box=box.ROUNDED)
		perf_table.add_column("Metric", style="cyan")
		perf_table.add_column("Value", style="green", justify="right")
		
		start_val = output.get("start_value", 100)
		end_val = output.get("end_value", 100)
		perf_table.add_row("Start Value", f"${start_val:,.2f}")
		perf_table.add_row("End Value", f"${end_val:,.2f}")
		
		total_return = output.get("total_return_pct", 0)
		return_color = "green" if total_return >= 0 else "red"
		perf_table.add_row("Total Return", f"[{return_color}]{total_return:+.2f}%[/{return_color}]")
		
		bench_return = output.get("benchmark_return_pct", 0)
		bench_color = "green" if bench_return >= 0 else "red"
		perf_table.add_row("Benchmark Return", f"[{bench_color}]{bench_return:+.2f}%[/{bench_color}]")
		
		exposure = output.get("max_gross_exposure_pct", 0)
		perf_table.add_row("Max Gross Exposure", f"{exposure:.2f}%")
		
		fees = output.get("total_fees_paid", 0)
		perf_table.add_row("Total Fees Paid", f"${fees:,.2f}")
		
		console.print(perf_table)

		# Risk metrics
		console.print()
		risk_table = Table(title="Risk Metrics", box=box.ROUNDED)
		risk_table.add_column("Metric", style="cyan")
		risk_table.add_column("Value", style="yellow", justify="right")
		
		max_dd = output.get("max_drawdown_pct", 0)
		dd_color = "red" if max_dd < 0 else "yellow"
		risk_table.add_row("Max Drawdown", f"[{dd_color}]{max_dd:.2f}%[/{dd_color}]")
		
		dd_duration = output.get("max_drawdown_duration_days", 0)
		risk_table.add_row("Max Drawdown Duration", f"{dd_duration} days")
		
		console.print(risk_table)

		# Trade statistics
		console.print()
		trades_table = Table(title="Trade Statistics", box=box.ROUNDED)
		trades_table.add_column("Metric", style="cyan")
		trades_table.add_column("Value", style="magenta", justify="right")
		
		total_trades = output.get("total_trades", 0)
		closed_trades = output.get("closed_trades", 0)
		open_trades = output.get("open_trades", 0)
		
		trades_table.add_row("Total Trades", str(total_trades))
		trades_table.add_row("Closed Trades", str(closed_trades))
		trades_table.add_row("Open Trades", str(open_trades))
		
		open_pnl = output.get("open_trade_pnl", 0)
		open_color = "green" if open_pnl >= 0 else "red"
		trades_table.add_row("Open Trade PnL", f"[{open_color}]${open_pnl:+,.2f}[/{open_color}]")
		
		win_rate = output.get("win_rate_pct", 0)
		trades_table.add_row("Win Rate", f"{win_rate:.2f}%")
		
		best_trade = output.get("best_trade_pct", 0)
		best_color = "green" if best_trade >= 0 else "red"
		trades_table.add_row("Best Trade", f"[{best_color}]{best_trade:+.2f}%[/{best_color}]")
		
		worst_trade = output.get("worst_trade_pct", 0)
		worst_color = "green" if worst_trade >= 0 else "red"
		trades_table.add_row("Worst Trade", f"[{worst_color}]{worst_trade:+.2f}%[/{worst_color}]")
		
		avg_winning = output.get("avg_winning_trade_pct", 0)
		trades_table.add_row("Avg Winning Trade", f"{avg_winning:+.2f}%")
		
		avg_losing = output.get("avg_losing_trade_pct", 0)
		trades_table.add_row("Avg Losing Trade", f"{avg_losing:+.2f}%")
		
		console.print(trades_table)

		# Trade duration and metrics
		console.print()
		duration_table = Table(title="Trade Duration & Ratios", box=box.ROUNDED)
		duration_table.add_column("Metric", style="cyan")
		duration_table.add_column("Value", style="bright_white", justify="right")
		
		avg_win_duration = output.get("avg_winning_trade_duration_days", 0)
		duration_table.add_row("Avg Winning Trade Duration", f"{avg_win_duration:.1f} days")
		
		avg_loss_duration = output.get("avg_losing_trade_duration_days", 0)
		duration_table.add_row("Avg Losing Trade Duration", f"{avg_loss_duration:.1f} days")
		
		profit_factor = output.get("profit_factor", 0)
		duration_table.add_row("Profit Factor", f"{profit_factor:.2f}")
		
		expectancy = output.get("expectancy_pct", 0)
		expectancy_color = "green" if expectancy >= 0 else "red"
		duration_table.add_row("Expectancy", f"[{expectancy_color}]{expectancy:+.2f}%[/{expectancy_color}]")
		
		console.print(duration_table)

		# Risk-adjusted returns
		console.print()
		ratios_table = Table(title="Risk-Adjusted Returns", box=box.ROUNDED)
		ratios_table.add_column("Ratio", style="cyan")
		ratios_table.add_column("Value", style="bright_cyan", justify="right")
		
		sharpe = output.get("sharpe_ratio", 0)
		sharpe_color = "green" if sharpe >= 1 else "yellow" if sharpe >= 0 else "red"
		ratios_table.add_row("Sharpe Ratio", f"[{sharpe_color}]{sharpe:.4f}[/{sharpe_color}]")
		
		sortino = output.get("sortino_ratio", 0)
		sortino_color = "green" if sortino >= 1 else "yellow" if sortino >= 0 else "red"
		ratios_table.add_row("Sortino Ratio", f"[{sortino_color}]{sortino:.4f}[/{sortino_color}]")
		
		calmar = output.get("calmar_ratio", 0)
		calmar_color = "green" if calmar >= 0.5 else "yellow" if calmar >= 0 else "red"
		ratios_table.add_row("Calmar Ratio", f"[{calmar_color}]{calmar:.4f}[/{calmar_color}]")
		
		omega = output.get("omega_ratio", 0)
		omega_color = "green" if omega >= 1.5 else "yellow" if omega >= 1 else "red"
		ratios_table.add_row("Omega Ratio", f"[{omega_color}]{omega:.4f}[/{omega_color}]")
		
		console.print(ratios_table)

		# Positions breakdown (if available)
		final_portfolio = output.get("final_portfolio", {})
		positions = final_portfolio.get("positions", [])
		if positions:
			console.print()
			positions_table = Table(title=f"Final Positions ({len(positions)})", box=box.ROUNDED)
			positions_table.add_column("Ticker", style="cyan")
			positions_table.add_column("Shares", style="yellow", justify="right")
			positions_table.add_column("Entry Price", style="blue", justify="right")
			positions_table.add_column("Current Price", style="blue", justify="right")
			positions_table.add_column("Position Value", style="magenta", justify="right")
			positions_table.add_column("Gain/Loss", style="bright_white", justify="right")
			positions_table.add_column("Gain %", style="bright_white", justify="right")
			
			for pos in positions:
				ticker = pos.get("ticker", "?")
				# Fix: PortfolioManager returns 'quantity', not 'shares'
				shares = pos.get("quantity", pos.get("shares", 0))
				shares_str = f"{shares:,.0f}"
				
				# Fix: PortfolioManager returns 'avg_entry_price', not 'entry_price'
				entry_price_val = pos.get("avg_entry_price", pos.get("entry_price", 0))
				entry_price = f"${entry_price_val:.2f}"
				
				# Fix: Use 'current_price' from position data
				current_price_val = pos.get("current_price", 0)
				current_price = f"${current_price_val:.2f}"
				
				position_value = f"${pos.get('position_value', 0):,.2f}"
				
				gain = pos.get("position_gain", 0)
				gain_str = f"${gain:+,.2f}"
				gain_pct = pos.get("position_gain_pct", 0)
				
				gain_color = "green" if gain >= 0 else "red"
				gain_pct_str = f"[{gain_color}]{gain_pct:+.2f}%[/{gain_color}]"
				
				positions_table.add_row(ticker, shares_str, entry_price, current_price, position_value, gain_str, gain_pct_str)
			
			console.print(positions_table)

	def _print_flow_result(self, result):
		"""Print workflow execution result."""
		status = result.get("status", "unknown")

		if status == "error":
			panel = Panel(
				f"[red]✗[/red] {result.get('message')}",
				style="red",
				box=box.ROUNDED
			)
			console.print(panel)
			if result.get("available"):
				avail = ", ".join(result.get("available", []))
				console.print(f"[cyan]Available workflows:[/cyan] {avail}")
			return

		# Success case
		panel = Panel(
			f"[green]✓[/green] Workflow executed successfully",
			style="green",
			box=box.ROUNDED
		)
		console.print(panel)

		# Display result details
		if "flow" in result:
			console.print(f"[cyan]Flow:[/cyan] {result['flow']}")
		if "strategy" in result:
			console.print(f"[cyan]Strategy:[/cyan] {result['strategy']}")
		if "steps_completed" in result:
			console.print(f"[cyan]Steps Completed:[/cyan] {result['steps_completed']}/{result.get('total_steps', '?')}")
		if "duration_ms" in result:
			console.print(f"[cyan]Duration:[/cyan] {result['duration_ms']:.0f}ms")

		# Display backtest portfolio metrics
		if "output" in result and isinstance(result.get("output"), dict):
			output = result["output"]
			if output.get("backtest_id"):
				self._print_backtest_metrics(output)
		if "sorted_tickers" in result:
			sorted_tickers = result.get("sorted_tickers", [])
			if sorted_tickers:
				table = Table(title="Tickers by Signal Score (Descending)", box=box.ROUNDED)
				table.add_column("Rank", style="dim")
				table.add_column("Ticker", style="cyan")
				table.add_column("Score", style="green")
				table.add_column("Signals", style="yellow")
				for i, ticker_info in enumerate(sorted_tickers, 1):
					ticker = ticker_info.get("ticker", "?")
					score = ticker_info.get("score", 0)
					signal_count = ticker_info.get("signal_count", 0)
					signals = ticker_info.get("triggered_signals", [])
					signal_str = ", ".join(signals) if signals else "none"
					table.add_row(str(i), ticker, f"{score:.3f}", signal_str)
				console.print(table)
			else:
				console.print("[yellow]No ticker scores available[/yellow]")

		# Display watchlist if present
		if "watchlist" in result:
			watchlist = result["watchlist"]
			if watchlist:
				table = Table(title="Generated Watchlist", box=box.ROUNDED)
				table.add_column("Ticker", style="cyan")
				for ticker in watchlist:
					table.add_row(ticker)
				console.print(table)
			else:
				console.print("[yellow]No tickers in watchlist[/yellow]")

		# Display executable orders if present
		if "executable_orders" in result:
			orders = result["executable_orders"]
			if orders:
				table = Table(title=f"Executable Orders ({len(orders)})", box=box.ROUNDED)
				table.add_column("ID", style="dim", width=12)
				table.add_column("Ticker", style="cyan")
				table.add_column("Shares", style="yellow", justify="right")
				table.add_column("Entry Price", style="green", justify="right")
				table.add_column("Execution", style="magenta")
				table.add_column("Stop Loss", style="red", justify="right")
				table.add_column("Take Profit", style="blue", justify="right")
				table.add_column("Risk/Reward", style="bright_white", justify="right")
				for order in orders:
					order_id = order.get("id", "?")[:8]
					ticker = order.get("ticker", "?")
					shares = str(order.get("shares", "?"))
					entry_price = f"${order.get('entry_price', 0):.2f}"
					execution = order.get("execution_method", "market").upper()
					stop_loss = f"${order.get('stop_loss', 0):.2f}" if order.get('stop_loss') else "—"
					take_profit = f"${order.get('take_profit', 0):.2f}" if order.get('take_profit') else "—"
					rr_ratio = f"{order.get('metadata', {}).get('rr_ratio', 0):.2f}x" if order.get('metadata', {}).get('rr_ratio') else "—"
					table.add_row(
						order_id, ticker, shares, entry_price, execution,
						stop_loss, take_profit, rr_ratio
					)
				console.print(table)

				# Show summary stats
				total_risk = sum(o.get("risk_amount", 0) for o in orders)
				total_value = sum(o.get("shares", 0) * o.get("entry_price", 0) for o in orders)
				console.print(f"[cyan]Summary:[/cyan] {len(orders)} orders | ${total_value:,.0f} total value | ${total_risk:,.0f} total risk")

				# Display execution results if present (paper trading)
				if "execution_results" in result:
					exec_results = result["execution_results"]
					if exec_results:
						exec_table = Table(title="Execution Results (Paper Trading)", box=box.ROUNDED)
						exec_table.add_column("Ticker", style="cyan")
						exec_table.add_column("Status", style="yellow")
						exec_table.add_column("Filled Qty", style="green", justify="right")
						exec_table.add_column("Filled Price", style="blue", justify="right")
						exec_table.add_column("Reason", style="red")
						for exec_result in exec_results:
							ticker = exec_result.get("ticker", "?")
							status = exec_result.get("status", "?").upper()
							status_style = "green" if status == "FILLED" else "yellow"
							filled_qty = str(exec_result.get("filled_quantity", "—"))
							filled_price = f"${exec_result.get('filled_price', 0):.2f}" if exec_result.get('filled_price') else "—"
							reason = exec_result.get("reason", "")
							exec_table.add_row(ticker, f"[{status_style}]{status}[/{status_style}]", filled_qty, filled_price, reason or "—")
						console.print(exec_table)
			else:
				console.print("[yellow]No executable orders[/yellow]")

		# Display execution history
		if "execution_history" in result:
			history = result["execution_history"]
			if history:
				hist_table = Table(title="Execution History", box=box.ROUNDED)
				hist_table.add_column("Step", style="cyan")
				hist_table.add_column("Status", style="yellow")
				for step_info in history:
					step_name = step_info.get("step", "unknown")
					step_status = step_info.get("status", "unknown")
					hist_table.add_row(step_name, step_status)

					# Add substeps if present (from nested flows)
					if "substeps" in step_info:
						for substep in step_info["substeps"]:
							substep_name = f"  - {substep.get('step', 'unknown')}"
							substep_status = substep.get("status", "unknown")
							hist_table.add_row(substep_name, substep_status)

				console.print(hist_table)

		# Display context if present
		if "_context" in result:
			context = result["_context"]
			if context:
				context_table = Table(title="Flow Context", box=box.ROUNDED)
				context_table.add_column("Key", style="cyan")
				context_table.add_column("Value", style="yellow")
				for key, value in context.items():
					# Format value for display
					if isinstance(value, (dict, list)):
						value_str = str(value)[:100]
					else:
						value_str = str(value)
					context_table.add_row(key, value_str)
				console.print(context_table)
			else:
				console.print("[yellow]Flow context is empty[/yellow]")

	def _print_result(self, result):
		"""Print command result."""
		status = result.get("status", "unknown")
		message = result.get('message', 'Command executed')

		if status == "success":
			panel = Panel(
				f"[green]✓[/green] {message}",
				style="green",
				box=box.ROUNDED
			)
		else:
			panel = Panel(
				f"[red]✗[/red] {message}",
				style="red",
				box=box.ROUNDED
			)

		console.print(panel)

		if status == "error":
			return

		for key, value in result.items():
			if key not in ("status", "message", "ticker"):
				if isinstance(value, (dict, list)):
					console.print(f"  [cyan]{key}:[/cyan] {value}")
				else:
					console.print(f"  [cyan]{key}:[/cyan] {value}")

	def _print_list_result(self, result):
		"""Print list result as formatted tables."""
		if result.get("status") == "error":
			panel = Panel(
				f"[red]✗[/red] {result.get('message')}",
				style="red",
				box=box.ROUNDED
			)
			console.print(panel)
			return

		if result.get("history"):
			hist_table = Table(title="History Cache", box=box.ROUNDED)
			hist_table.add_column("Ticker", style="cyan")
			hist_table.add_column("Size (KB)", style="yellow")
			for item in result["history"]:
				hist_table.add_row(item['ticker'], f"{item['size_kb']:.1f}")
			console.print(hist_table)

		if result.get("fundamentals"):
			fund_table = Table(title="Fundamentals Cache", box=box.ROUNDED)
			fund_table.add_column("Ticker", style="cyan")
			fund_table.add_column("Size (KB)", style="yellow")
			for item in result["fundamentals"]:
				fund_table.add_row(item['ticker'], f"{item['size_kb']:.1f}")
			console.print(fund_table)

	def _print_stats_result(self, result):
		"""Print cache statistics."""
		if result.get("status") == "error":
			panel = Panel(
				f"[red]✗[/red] {result.get('message')}",
				style="red",
				box=box.ROUNDED
			)
			console.print(panel)
			return

		hist = result.get("history", {})
		fund = result.get("fundamentals", {})

		stats_table = Table(title="Cache Statistics", box=box.ROUNDED)
		stats_table.add_column("Type", style="cyan")
		stats_table.add_column("Files", style="yellow")
		stats_table.add_column("Size (MB)", style="magenta")
		stats_table.add_column("Path", style="dim")

		stats_table.add_row(
			"History",
			str(hist.get('count', 0)),
			f"{hist.get('size_mb', 0):.2f}",
			str(hist.get('path', 'N/A'))[:40]
		)
		stats_table.add_row(
			"Fundamentals",
			str(fund.get('count', 0)),
			f"{fund.get('size_mb', 0):.2f}",
			str(fund.get('path', 'N/A'))[:40]
		)

		console.print(stats_table)
		console.print(f"\n[bold]Total Size:[/bold] {result.get('total_size_mb', 0):.2f} MB")

	def _print_universe_result(self, result):
		"""Print universe fetch result."""
		status = result.get("status", "unknown")
		message = result.get('message', 'Command executed')

		if status == "success":
			panel = Panel(
				f"[green]✓[/green] {message}",
				style="green",
				box=box.ROUNDED
			)
		else:
			panel = Panel(
				f"[red]✗[/red] {message}",
				style="red",
				box=box.ROUNDED
			)
		console.print(panel)

		if status == "error":
			if result.get("available"):
				avail = ", ".join(result.get('available', []))
				console.print(f"[cyan]Available universes:[/cyan] {avail}")
			return

		table = Table(title="Universe Fetch Summary", box=box.ROUNDED)
		table.add_column("Metric", style="cyan")
		table.add_column("Value", style="yellow")

		table.add_row("Universe", result.get('universe'))
		table.add_row("Total Tickers", str(result.get('total')))
		table.add_row("Fetched", str(result.get('fetched')))
		table.add_row("Failed", str(result.get('failed')))

		details = result.get("details", [])
		successful = [d for d in details if d.get("status") == "success"]
		if successful:
			rows_fetched = sum(d.get("rows", 0) for d in successful)
			table.add_row("Total Rows", str(rows_fetched))

		console.print(table)

	def do_history(self, args):
		"""View command history: history [N] shows last N commands (default: 20)"""
		try:
			count = int(str(args).strip()) if args else 20
		except ValueError:
			console.print("[red]✗[/red] Invalid number of commands")
			return

		if not self.history:
			console.print("[yellow]No command history[/yellow]")
			return

		# Get last N commands
		commands = list(self.history)[-count:]

		table = Table(title=f"Command History (last {len(commands)})", box=box.ROUNDED)
		table.add_column("#", style="dim")
		table.add_column("Command", style="cyan")

		for idx, cmd in enumerate(commands, 1):
			table.add_row(str(idx), str(cmd))

		console.print(table)

	def do_clear(self, _):
		"""Clear the screen."""
		console.clear()

	def do_motd(self, _):
		"""Show welcome banner."""
		self._print_intro()

	def do_pwd(self, _):
		"""Show current project root."""
		panel = Panel(
			f"[cyan]Project Root:[/cyan]\n{self.project_root}",
			style="cyan",
			box=box.ROUNDED,
			title="Working Directory"
		)
		console.print(panel)

	def _print_universes(self):
		"""Print available universes as a table."""
		from tools.universe.universe import Universe

		universes = Universe.list_universes()

		if not universes:
			panel = Panel(
				"No universes found",
				style="yellow",
				box=box.ROUNDED
			)
			console.print(panel)
			return

		table = Table(title=f"Available Universes ({len(universes)})", box=box.ROUNDED)
		table.add_column("Name", style="cyan")
		table.add_column("Tickers", style="yellow")
		table.add_column("Size (KB)", style="magenta")

		for universe_name in universes:
			info = Universe.get_universe_info(universe_name)
			if info:
				table.add_row(
					universe_name,
					str(info.get('count', 0)),
					f"{info.get('file_size_kb', 0):.1f}"
				)

		console.print(table)
