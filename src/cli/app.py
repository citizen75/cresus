"""Cresus CLI application."""

import cmd2
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from cli.commands.service import ServiceManager
from tools.data.manager import DataManager

console = Console()


class CresusCLI(cmd2.Cmd):
	"""Cresus portfolio management CLI."""

	intro = ""

	def __init__(self):
		super().__init__()
		self.project_root = self._find_project_root()
		self.service_manager = ServiceManager(self.project_root)
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
				for svc in ["api", "mcp", "front"]:
					result = self.service_manager.start(svc, daemon)
					status = "[green]✓[/green]" if "started" in result.lower() else "[red]✗[/red]"
					console.print(f"{status} {svc}: {result}")
			else:
				result = self.service_manager.start(service, daemon)
				status = "[green]✓[/green]" if "started" in result.lower() else "[red]✗[/red]"
				console.print(f"{status} {result}")

		elif cmd == "stop":
			if not service:
				console.print("[red]✗[/red] Usage: service stop <api|mcp|front|all>")
				return
			if service == "all":
				for svc in ["api", "mcp", "front"]:
					result = self.service_manager.stop(svc)
					status = "[green]✓[/green]" if "stopped" in result.lower() else "[red]✗[/red]"
					console.print(f"{status} {svc}: {result}")
			else:
				result = self.service_manager.stop(service)
				status = "[green]✓[/green]" if "stopped" in result.lower() else "[red]✗[/red]"
				console.print(f"{status} {result}")

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
				console.print("[red]✗[/red] Usage: data fetch <history|fundamental|universe> <ticker|name> [start_date]")
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
