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
		info_table.add_row("[bold]init[/bold]", "Initialize ~/.cresus directory structure")
		info_table.add_row("[bold]help[/bold]", "Show all available commands")
		info_table.add_row("[bold]service[/bold]", "Manage services (api, mcp, front)")
		info_table.add_row("[bold]flow[/bold]", "Execute workflows (e.g., flow run watchlist)")
		info_table.add_row("[bold]data[/bold]", "Manage portfolio data and cache")
		info_table.add_row("[bold]universe[/bold]", "Manage universes (e.g., universe list|info cac40)")
		info_table.add_row("[bold]blacklist[/bold]", "Manage blacklist (e.g., blacklist list|add|del MOEX)")
		info_table.add_row("[bold]watchlist[/bold]", "View strategy watchlist (e.g., watchlist show momentum_cac)")
		info_table.add_row("[bold]orders[/bold]", "View pending/executed orders (e.g., orders list momentum_cac)")
		info_table.add_row("[bold]cron[/bold]", "View scheduled cron jobs and next run times")
		info_table.add_row("[bold]status[/bold]", "Show system status")
		info_table.add_row("[bold]update[/bold]", "Update cresus from git")
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

	# ==================== Init Command ====================
	def do_init(self, _):
		"""Initialize ~/.cresus directory structure with config files."""
		self._init_cresus_directory()

	def _init_cresus_directory(self):
		"""Create ~/.cresus directory structure and copy config files from init/ template."""
		cresus_home = Path.home() / ".cresus"
		init_template = self.project_root / "init"

		console.print(f"[bold cyan]Initializing Cresus configuration[/bold cyan]")
		console.print(f"Location: {cresus_home}\n")

		if not init_template.exists():
			console.print(f"[red]✗ Init template not found: {init_template}[/red]")
			return

		# Define directory structure from init template
		dirs_to_create = [cresus_home]

		# Recursively collect all directories from init/db
		for item in (init_template / "db").rglob("*"):
			if item.is_dir():
				rel_path = item.relative_to(init_template / "db")
				dirs_to_create.append(cresus_home / "db" / rel_path)

		# Add config directories
		dirs_to_create.append(cresus_home / "config")
		config_strategies = init_template / "config" / "strategies"
		if config_strategies.exists():
			dirs_to_create.append(cresus_home / "config" / "strategies")

		# Create directories
		created_dirs = []
		for d in dirs_to_create:
			if not d.exists():
				d.mkdir(parents=True, exist_ok=True)
				created_dirs.append(d)

		if created_dirs:
			console.print(f"[green]✓ Created {len(created_dirs)} directories[/green]")
		else:
			console.print("[yellow]⚠ All directories already exist[/yellow]")

		# Copy config files from init/config
		config_files = ["cresus.yml", "cron.yml", "mcp.yml"]
		copied_files = []

		for config_file in config_files:
			src = init_template / "config" / config_file
			dst = cresus_home / "config" / config_file

			if src.exists() and not dst.exists():
				try:
					with open(src, 'r') as f:
						content = f.read()
					with open(dst, 'w') as f:
						f.write(content)
					copied_files.append(config_file)
				except Exception as e:
					console.print(f"[red]✗ Error copying {config_file}: {e}[/red]")
			elif dst.exists():
				pass  # File already exists, don't overwrite
			else:
				console.print(f"[yellow]⚠ Source not found: {config_file}[/yellow]")

		if copied_files:
			console.print(f"[green]✓ Copied {len(copied_files)} config file(s): {', '.join(copied_files)}[/green]")

		# Copy universe files from init/db/universes
		universes_src = init_template / "db" / "universes"
		universes_dst = cresus_home / "db" / "universes"

		if universes_src.exists():
			copied_universes = []
			for universe_file in universes_src.glob("*.csv"):
				dst_file = universes_dst / universe_file.name
				if not dst_file.exists():
					try:
						with open(universe_file, 'r') as f:
							content = f.read()
						with open(dst_file, 'w') as f:
							f.write(content)
						copied_universes.append(universe_file.name)
					except Exception as e:
						console.print(f"[red]✗ Error copying {universe_file.name}: {e}[/red]")

			if copied_universes:
				console.print(f"[green]✓ Copied {len(copied_universes)} universe file(s)[/green]")

		# Copy strategy files from init/db/strategies
		strategies_src = init_template / "db" / "strategies"
		strategies_dst = cresus_home / "db" / "strategies"

		if strategies_src.exists():
			copied_strategies = []
			for strategy_file in strategies_src.glob("*"):
				if strategy_file.is_file():
					dst_file = strategies_dst / strategy_file.name
					if not dst_file.exists():
						try:
							with open(strategy_file, 'r') as f:
								content = f.read()
							with open(dst_file, 'w') as f:
								f.write(content)
							copied_strategies.append(strategy_file.name)
						except Exception as e:
							console.print(f"[red]✗ Error copying {strategy_file.name}: {e}[/red]")

			if copied_strategies:
				console.print(f"[green]✓ Copied {len(copied_strategies)} strategy file(s)[/green]")

		# Create .env file if it doesn't exist
		env_file = cresus_home / ".env"
		if not env_file.exists():
			env_template = init_template / ".env"
			if env_template.exists():
				try:
					with open(env_template, 'r') as f:
						content = f.read()
					with open(env_file, 'w') as f:
						f.write(content)
					console.print("[green]✓ Created .env from template[/green]")
				except Exception as e:
					console.print(f"[red]✗ Error creating .env: {e}[/red]")
			else:
				console.print("[yellow]⚠ .env template not found[/yellow]")
		else:
			console.print("[yellow]⚠ .env already exists (not overwritten)[/yellow]")

		console.print(f"\n[bold green]✓ Cresus initialized successfully![/bold green]")
		console.print(f"[dim]Configuration location: {cresus_home}[/dim]")
		console.print(f"[dim]Edit {cresus_home / '.env'} to customize settings[/dim]")

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
				console.print("[red]✗[/red] Usage: flow run <workflow_name> [strategy] [tickers...] [--context] [--debug] [-v|-vv|-vvv] [--backtest]")
				return

			workflow_name = parts[1]
			include_context = "--context" in parts
			debug = "--debug" in parts
			use_backtest = "--backtest" in parts

			# Count verbosity level (-v, -vv, -vvv)
			verbosity_level = 0
			for part in parts:
				if part == "-v":
					verbosity_level = max(verbosity_level, 1)
				elif part == "-vv":
					verbosity_level = max(verbosity_level, 2)
				elif part == "-vvv":
					verbosity_level = max(verbosity_level, 3)

			# Remove workflow name and flags from parts
			remaining = [p for p in parts[2:] if not p.startswith("-")]

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

			# Set log level based on verbosity
			original_debug = debug
			if verbosity_level > 0:
				from core.logger import set_log_level
				if verbosity_level == 1:
					set_log_level("WARNING")
				elif verbosity_level == 2:
					set_log_level("INFO")
				elif verbosity_level >= 3:
					set_log_level("DEBUG")
					original_debug = True  # Enable debug mode for -vvv

			try:
				result = self.flow_manager.run_workflow(workflow_name, strategy, input_data, include_context, original_debug, use_backtest)
				self.flow_manager._print_flow_result(result, workflow_name)
			finally:
				# Restore default log level
				if verbosity_level > 0:
					from core.logger import set_log_level
					set_log_level("ERROR")

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

	def do_universe(self, args):
		"""Manage universes: list|info <name>"""
		from tools.universe.universe import Universe
		from rich.table import Table

		parts = args.strip().split() if args.strip() else []

		if not parts or parts[0] == "list":
			# List all universes
			universes = Universe.list_universes()

			if not universes:
				console.print("[yellow]No universes found in ~/.cresus/db/universes/[/yellow]")
				return

			table = Table(title="Available Universes", box=box.ROUNDED)
			table.add_column("Universe", style="cyan")
			table.add_column("Tickers", style="green")
			table.add_column("Size (KB)", style="blue")

			for universe_name in universes:
				info = Universe.get_universe_info(universe_name)
				if info:
					table.add_row(
						universe_name,
						str(info["count"]),
						f"{info['file_size_kb']:.1f}"
					)
				else:
					table.add_row(universe_name, "error", "-")

			console.print(table)

		elif parts[0] == "info" and len(parts) > 1:
			# Show detailed info about a universe
			universe_name = parts[1]
			info = Universe.get_universe_info(universe_name)

			if not info:
				console.print(f"[red]✗ Universe '{universe_name}' not found[/red]")
				return

			console.print(f"\n[bold cyan]Universe: {info['name']}[/bold cyan]")
			console.print(f"[cyan]Path:[/cyan] {info['path']}")
			console.print(f"[cyan]Tickers:[/cyan] {info['count']}")
			console.print(f"[cyan]File Size:[/cyan] {info['file_size_kb']:.1f} KB")
			console.print(f"[cyan]Columns:[/cyan] {', '.join(info['columns'])}")

		else:
			console.print("[yellow]Usage: universe list|info <name>[/yellow]")

	# ==================== Blacklist Commands ====================
	def do_blacklist(self, args):
		"""Manage blacklist: list|add|del <ticker>"""
		from tools.universe.blacklist import get_blacklist
		from tools.universe.universe import Universe
		from rich.table import Table
		import pandas as pd

		parts = args.strip().split() if args.strip() else []

		if not parts or parts[0] == "list":
			# List all blacklisted tickers
			blacklist = get_blacklist()
			tickers = blacklist.get_tickers()

			if not tickers:
				console.print("[yellow]No tickers in blacklist[/yellow]")
				return

			table = Table(title="Blacklisted Tickers", box=box.ROUNDED)
			table.add_column("Ticker", style="cyan")
			table.add_column("Reason", style="yellow")
			table.add_column("Date Added", style="dim")

			# Read the CSV to get reason and date info
			try:
				df = pd.read_csv(blacklist.filepath, keep_default_na=False, na_values=[])
				for _, row in df.iterrows():
					table.add_row(
						row.get("ticker", ""),
						row.get("reason", ""),
						row.get("date_added", "")
					)
			except Exception:
				# Fallback: just list the tickers
				for ticker in sorted(tickers):
					table.add_row(ticker, "", "")

			console.print(table)

		elif parts[0] == "add" and len(parts) > 1:
			# Add ticker to blacklist
			ticker = parts[1].upper()
			blacklist = get_blacklist()

			# Try to find the ticker name from universes
			ticker_name = None
			universes = Universe.list_universes()

			for universe_name in universes:
				try:
					u = Universe(universe_name)
					if u.exists():
						df = u.load_df()
						# Search in TickerYahoo column
						if "TickerYahoo" in df.columns:
							match = df[df["TickerYahoo"].str.upper() == ticker]
							if not match.empty:
								# Try to get the name from Name or CompanyName column
								if "Name" in df.columns:
									ticker_name = match.iloc[0]["Name"]
									break
								elif "CompanyName" in df.columns:
									ticker_name = match.iloc[0]["CompanyName"]
									break
						# Search in ISIN column
						if ticker_name is None and "ISIN" in df.columns:
							match = df[df["ISIN"].str.upper() == ticker]
							if not match.empty:
								if "Name" in df.columns:
									ticker_name = match.iloc[0]["Name"]
									break
								elif "CompanyName" in df.columns:
									ticker_name = match.iloc[0]["CompanyName"]
									break
				except Exception:
					pass

			# Add to blacklist
			reason = f"User blacklist - {ticker_name}" if ticker_name else "User blacklist"
			blacklist.add_ticker(ticker, reason=reason)

			console.print(f"[green]✓ Added {ticker} to blacklist[/green]")
			if ticker_name:
				console.print(f"[dim]  Name: {ticker_name}[/dim]")

		elif parts[0] == "del" and len(parts) > 1:
			# Remove ticker from blacklist
			ticker = parts[1].upper()
			blacklist = get_blacklist()

			if not blacklist.is_blacklisted(ticker):
				console.print(f"[yellow]⚠ {ticker} not found in blacklist[/yellow]")
				return

			blacklist.remove_ticker(ticker)
			console.print(f"[green]✓ Removed {ticker} from blacklist[/green]")

		else:
			console.print("[yellow]Usage: blacklist list|add|del <ticker>[/yellow]")

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
		"""Update cresus from git repository."""
		import subprocess
		import sys

		print("Updating cresus from git repository...", flush=True)

		try:
			print("▸ Checking remote for updates...", flush=True)

			# Fetch
			fetch_result = subprocess.run(
				["git", "fetch"],
				cwd=str(self.project_root),
				timeout=30
			)

			if fetch_result.returncode != 0:
				print("✗ Fetch failed", file=sys.stderr, flush=True)
				return

			print("✓ Fetch complete", flush=True)

			# Check how many commits to pull
			log_result = subprocess.run(
				["git", "log", "--oneline", "--decorate", "HEAD..@{u}"],
				cwd=str(self.project_root),
				capture_output=True,
				text=True,
				timeout=10
			)

			commits_to_pull = log_result.stdout.strip().split('\n') if log_result.stdout.strip() else []
			num_commits = len(commits_to_pull)

			if num_commits == 0:
				print("✓ Already up to date with remote", flush=True)
				return

			print(f"▸ Found {num_commits} commit{'s' if num_commits != 1 else ''} to pull", flush=True)
			print("▸ Pulling changes...", flush=True)

			# Execute pull
			pull_result = subprocess.run(
				["git", "pull"],
				cwd=str(self.project_root),
				timeout=60
			)

			if pull_result.returncode == 0:
				print("✓ Update completed successfully", flush=True)
				print(f"Merged {num_commits} commit{'s' if num_commits != 1 else ''}", flush=True)
			else:
				print(f"✗ Pull failed with exit code {pull_result.returncode}", file=sys.stderr, flush=True)

		except subprocess.TimeoutExpired:
			print("✗ Operation timed out", file=sys.stderr, flush=True)
		except Exception as e:
			import traceback
			print(f"✗ Update error: {e}", file=sys.stderr, flush=True)
			traceback.print_exc()

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
