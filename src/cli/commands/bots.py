"""CLI commands for bot management."""

from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from tools.bot import BotManager


class BotsCommands:
	"""Commands for managing trading bots."""

	def __init__(self):
		"""Initialize bots commands."""
		self.manager = BotManager()
		self.console = Console()

	def handle(self, args: str) -> None:
		"""Handle bots command with subcommands.

		Args:
			args: Command arguments
		"""
		if not args or args.startswith("help"):
			self._print_help()
			return

		# Parse subcommand
		parts = args.split(None, 1)
		subcommand = parts[0]
		arg_rest = parts[1] if len(parts) > 1 else ""

		# Dispatch to subcommand handler
		handlers = {
			"list": self._handle_list,
			"create": self._handle_create,
			"info": self._handle_info,
			"activate": self._handle_activate,
			"deactivate": self._handle_deactivate,
			"delete": self._handle_delete,
			"config": self._handle_config,
			"watchlist": self._handle_watchlist,
			"portfolio": self._handle_portfolio,
			"summary": self._handle_summary,
			"run": self._handle_run,
		}

		handler = handlers.get(subcommand)
		if handler:
			handler(arg_rest)
		else:
			self.console.print(f"[red]Unknown subcommand: {subcommand}[/red]")
			self._print_help()

	def _print_help(self) -> None:
		"""Print help message."""
		help_text = """[cyan]Bot Management Commands[/cyan]

[bold]Usage:[/bold]
  cresus> bot <subcommand> [arguments]

[bold]Subcommands:[/bold]
  list [state]                        List all bots (optionally filter by active|inactive)
  create <name> <strategy>            Create new bot from strategy name or file path
  info <name>                         Show complete bot details and portfolio
  run <name> [params]                 Execute bot trading cycle with optional JSON params
  activate <name>                     Activate bot for live trading
  deactivate <name>                   Deactivate bot (pause trading)
  delete <name>                       Delete bot and all its data
  config <name> [show|load|save]      Show/load/save bot configuration
  watchlist <name> [show|add|rm]      Manage bot's ticker watchlist
  portfolio <name>                    Display bot portfolio and open positions
  summary                             Show summary of all bots by state

[bold]Strategy argument (for create):[/bold]
  Can be either strategy name or file path:
  - [cyan]Strategy name:[/cyan] cac_top_5, cac_momentum, nasdaq_tech, etc.
    → Searches: config/strategies/<name>.yml
  - [cyan]File path:[/cyan] config/strategies/momentum.yml, ./my_strategy.yml
    → Uses specified file path directly

[bold]Examples:[/bold]
  [cyan]# Listing[/cyan]
  bot list                            # List all bots
  bot list active                     # List only active bots
  bot summary                         # Show bot count by state

  [cyan]# Creating[/cyan]
  bot create cac_bot cac_top_5        # Create bot with strategy name
  bot create mom_bot cac_momentum     # Another strategy name
  bot create test_bot config/strategies/custom.yml  # Using file path

  [cyan]# Information[/cyan]
  bot info cac_bot                    # Show full bot details
  bot config cac_bot show             # Show bot configuration
  bot portfolio cac_bot               # Show portfolio and positions

  [cyan]# Watchlist Management[/cyan]
  bot watchlist cac_bot show          # Display watchlist
  bot watchlist cac_bot add AC.PA     # Add ticker
  bot watchlist cac_bot add OR.PA     # Add another
  bot watchlist cac_bot remove AC.PA  # Remove ticker

  [cyan]# State Management[/cyan]
  bot activate cac_bot                # Activate for trading
  bot deactivate cac_bot              # Pause trading
  bot delete cac_bot                  # Remove bot

  [cyan]# Execution[/cyan]
  bot run cac_bot                     # Run with default params
  bot run cac_bot '{"market":"cac40"}'  # Run with custom params
  bot run momentum_bot '{"capital":100000,"signal_strength":0.8}'

[bold]Parameter Format (for run):[/bold]
  JSON format: bot run <name> '{\"key\":\"value\", ...}'
  Common params:
    - market: "cac40", "nasdaq", "dow", etc.
    - capital: Initial capital amount
    - signal_strength: Min signal strength (0.0-1.0)
    - max_positions: Maximum concurrent positions

[bold]Bot States:[/bold]
  active   - Bot is running and can be executed
  inactive - Bot is paused (must activate to run)
  error    - Bot encountered an error
  stopped  - Bot was stopped

[bold]Tips:[/bold]
  • Must activate bot before running: bot activate <name>
  • Create from available strategies: cresus strategy list
  • Bot data stored in: ~/.cresus/db/bots/<bot_name>/
  • Each bot has isolated portfolio and configuration
"""
		self.console.print(help_text)

	def _handle_list(self, args: str) -> None:
		"""List bots."""
		state_filter = args.strip() if args else None

		if state_filter and state_filter not in ("active", "inactive"):
			self.console.print(f"[red]Invalid state: {state_filter}[/red]")
			return

		bots = self.manager.list_bots(state_filter)

		if not bots:
			self.console.print("[yellow]No bots found[/yellow]")
			return

		table = Table(title="Bots" if not state_filter else f"Bots ({state_filter})")
		table.add_column("Name", style="cyan")
		table.add_column("State", style="magenta")
		table.add_column("Strategy", style="green")
		table.add_column("Created", style="blue")

		for bot in bots:
			state = bot.get("state", "inactive")
			state_color = "green" if state == "active" else "yellow"
			table.add_row(
				bot.get("name", "unknown"),
				f"[{state_color}]{state}[/{state_color}]",
				bot.get("strategy", "-"),
				bot.get("created_at", "-")[:10]
			)

		self.console.print(table)

	def _handle_create(self, args: str) -> None:
		"""Create a new bot."""
		parts = args.split(None, 1)

		if len(parts) < 2:
			self.console.print("[red]Usage: bot create <name> <strategy>[/red]")
			self.console.print("[dim]  <strategy> can be a name (e.g., cac_top_5) or path[/dim]")
			return

		name = parts[0]
		strategy = parts[1]

		try:
			config = self.manager.create_bot(name, strategy)
			self.console.print(f"[green]✓ Bot created: {name}[/green]")
			self.console.print(f"  Directory: {self.manager.get_bot_dir(name)}")
			self.console.print(f"  Strategy: {config.get('strategy', '-')}")
			self.console.print(f"  State: {config.get('state', 'inactive')}")
		except ValueError as e:
			error_msg = str(e)
			self.console.print(f"[red]✗ Error: {error_msg}[/red]")

			# Try to show available strategies
			available = self.manager._get_available_strategies()
			if available:
				self.console.print(f"\n[cyan]Available strategies:[/cyan]")
				for s in available[:10]:
					self.console.print(f"  • {s}")
				if len(available) > 10:
					self.console.print(f"  ... and {len(available) - 10} more")
		except Exception as e:
			self.console.print(f"[red]✗ Unexpected error: {str(e)}[/red]")

	def _handle_info(self, args: str) -> None:
		"""Show bot information."""
		name = args.strip()

		if not name:
			self.console.print("[red]Usage: bot info <name>[/red]")
			return

		info = self.manager.get_bot_info(name)

		if not info:
			self.console.print(f"[red]Bot not found: {name}[/red]")
			return

		config = info["config"]
		portfolio = info["portfolio"]
		watchlist = info["watchlist"]

		# Display bot info panel
		info_text = f"""[cyan]{name}[/cyan]
[bold]State:[/bold] {config.get('state', 'inactive')}
[bold]Created:[/bold] {config.get('created_at', '-')}
[bold]Strategy:[/bold] {config.get('strategy', '-')}
[bold]Description:[/bold] {config.get('description', '-')}

[bold]Portfolio:[/bold]
  Capital: ${portfolio.get('initial_capital', 0):,.0f}
  Cash: ${portfolio.get('cash', 0):,.0f}
  Total Value: ${portfolio.get('total_value', 0):,.0f}
  P&L: ${portfolio.get('pnl', 0):,.2f} ({portfolio.get('pnl_pct', 0):.2%})
  Positions: {len(portfolio.get('positions', []))}

[bold]Watchlist:[/bold]
  {', '.join(watchlist) if watchlist else 'Empty'}
"""

		panel = Panel(info_text, title=f"Bot: {name}")
		self.console.print(panel)

	def _handle_activate(self, args: str) -> None:
		"""Activate a bot."""
		name = args.strip()

		if not name:
			self.console.print("[red]Usage: bot activate <name>[/red]")
			return

		if self.manager.activate_bot(name):
			self.console.print(f"[green]✓ Bot activated: {name}[/green]")
		else:
			self.console.print(f"[red]✗ Bot not found: {name}[/red]")

	def _handle_deactivate(self, args: str) -> None:
		"""Deactivate a bot."""
		name = args.strip()

		if not name:
			self.console.print("[red]Usage: bot deactivate <name>[/red]")
			return

		if self.manager.deactivate_bot(name):
			self.console.print(f"[green]✓ Bot deactivated: {name}[/green]")
		else:
			self.console.print(f"[red]✗ Bot not found: {name}[/red]")

	def _handle_delete(self, args: str) -> None:
		"""Delete a bot."""
		name = args.strip()

		if not name:
			self.console.print("[red]Usage: bot delete <name>[/red]")
			return

		if self.manager.delete_bot(name):
			self.console.print(f"[green]✓ Bot deleted: {name}[/green]")
		else:
			self.console.print(f"[red]✗ Bot not found: {name}[/red]")

	def _handle_config(self, args: str) -> None:
		"""Manage bot configuration."""
		parts = args.split(None, 1)

		if not parts:
			self.console.print("[red]Usage: bot config <name> [show|load <file>|save <file>][/red]")
			return

		name = parts[0]
		action = parts[1] if len(parts) > 1 else "show"

		config = self.manager.get_bot(name)
		if not config:
			self.console.print(f"[red]Bot not found: {name}[/red]")
			return

		if action == "show":
			import yaml
			config_text = yaml.dump(config, default_flow_style=False)
			panel = Panel(config_text, title=f"Bot Configuration: {name}")
			self.console.print(panel)

		elif action.startswith("save"):
			file_path = action.split(None, 1)[1] if len(action.split()) > 1 else "bot_config.yml"
			import yaml
			with open(file_path, "w") as f:
				yaml.dump(config, f)
			self.console.print(f"[green]✓ Configuration saved to: {file_path}[/green]")

		elif action.startswith("load"):
			file_path = action.split(None, 1)[1] if len(action.split()) > 1 else None
			if not file_path:
				self.console.print("[red]Usage: bot config <name> load <file>[/red]")
				return

			try:
				import yaml
				with open(file_path) as f:
					new_config = yaml.safe_load(f)
				self.manager.save_config(name, new_config)
				self.console.print(f"[green]✓ Configuration loaded from: {file_path}[/green]")
			except FileNotFoundError:
				self.console.print(f"[red]File not found: {file_path}[/red]")
			except Exception as e:
				self.console.print(f"[red]Error loading config: {str(e)}[/red]")

	def _handle_watchlist(self, args: str) -> None:
		"""Manage bot watchlist."""
		parts = args.split()

		if not parts:
			self.console.print("[red]Usage: bot watchlist <name> [show|add|remove][/red]")
			return

		_ACTIONS = {"show", "add", "remove"}
		# Support both "watchlist <name> show" and "watchlist show <name>"
		if parts[0] in _ACTIONS and len(parts) >= 2:
			action = parts[0]
			name = parts[1]
			extra = parts[2:]
		else:
			name = parts[0]
			action = parts[1] if len(parts) > 1 else "show"
			extra = parts[2:]

		if action == "show":
			from tools.bot import BotManager
			from tools.watchlist import WatchlistManager

			bot_dir = self.manager.get_bot_dir(name)
			wm = WatchlistManager(name, bot_dir=str(bot_dir))
			df = wm.load()

			if df is None or df.empty:
				self.console.print(f"[yellow]No watchlist.csv found for bot: {name}[/yellow]")
				return

			table = Table(title=f"Watchlist: {name} ({len(df)} tickers)")
			table.add_column("Ticker", style="cyan")
			table.add_column("Close", justify="right")
			table.add_column("Score", justify="right", style="green")
			table.add_column("Signals", style="dim")

			for _, row in df.iterrows():
				close = f"{row['close']:.2f}" if row.get("close") is not None else "-"
				score_val = row.get("score", row.get("signal_score"))
				score = f"{score_val:.4f}" if score_val is not None and str(score_val) != "nan" else "-"
				sig_raw = row.get("signals", "")
				signals = str(sig_raw) if sig_raw and str(sig_raw) != "nan" else "-"
				table.add_row(str(row["ticker"]), close, score, signals)

			self.console.print(table)

		elif action == "add":
			ticker = extra[0] if extra else None

			if not ticker:
				self.console.print("[red]Usage: bot watchlist <name> add <ticker>[/red]")
				return

			if self.manager.add_to_watchlist(name, ticker):
				self.console.print(f"[green]✓ Added to watchlist: {ticker}[/green]")
			else:
				self.console.print(f"[yellow]Already in watchlist: {ticker}[/yellow]")

		elif action == "remove":
			ticker = extra[0] if extra else None

			if not ticker:
				self.console.print("[red]Usage: bot watchlist <name> remove <ticker>[/red]")
				return

			if self.manager.remove_from_watchlist(name, ticker):
				self.console.print(f"[green]✓ Removed from watchlist: {ticker}[/green]")
			else:
				self.console.print(f"[red]Not found in watchlist: {ticker}[/red]")

	def _handle_portfolio(self, args: str) -> None:
		"""Show bot portfolio."""
		name = args.strip()

		if not name:
			self.console.print("[red]Usage: bot portfolio <name>[/red]")
			return

		portfolio = self.manager.load_portfolio(name)

		if not portfolio:
			self.console.print(f"[red]Portfolio not found: {name}[/red]")
			return

		positions = portfolio.get("positions", [])

		# Summary panel
		summary_text = f"""[bold]Capital:[/bold] ${portfolio.get('initial_capital', 0):,.0f}
[bold]Cash:[/bold] ${portfolio.get('cash', 0):,.0f}
[bold]Total Value:[/bold] ${portfolio.get('total_value', 0):,.0f}
[bold]P&L:[/bold] ${portfolio.get('pnl', 0):,.2f} ({portfolio.get('pnl_pct', 0):.2%})
[bold]Positions:[/bold] {len(positions)}
"""

		panel = Panel(summary_text, title=f"Portfolio: {name}")
		self.console.print(panel)

		# Positions table
		if positions:
			table = Table(title="Positions")
			table.add_column("Ticker", style="cyan")
			table.add_column("Quantity", justify="right")
			table.add_column("Entry Price", justify="right")
			table.add_column("Current Price", justify="right")
			table.add_column("P&L", justify="right")

			for pos in positions:
				table.add_row(
					pos.get("ticker", "-"),
					str(pos.get("quantity", 0)),
					f"${pos.get('entry_price', 0):.2f}",
					f"${pos.get('current_price', 0):.2f}",
					f"${pos.get('pnl', 0):.2f}"
				)

			self.console.print(table)

	def _handle_summary(self) -> None:
		"""Show summary of all bots."""
		summary = self.manager.get_bots_summary()

		table = Table(title="Bot Summary")
		table.add_column("State", style="cyan")
		table.add_column("Count", justify="right", style="magenta")

		table.add_row("[green]active[/green]", str(summary["active"]))
		table.add_row("[yellow]inactive[/yellow]", str(summary["inactive"]))
		table.add_row("[bold]Total[/bold]", str(summary["total"]))

		self.console.print(table)

	def _handle_run(self, args: str) -> None:
		"""Run bot execution cycle using BotFinance.

		Usage:
		  bot run <name> [params_json] [--debug]

		Options:
		  --debug    Enable debug logging output
		"""
		import json
		import time
		from pathlib import Path
		from bot.finance import BotFinance

		# Parse arguments
		parts = args.split()

		if not parts:
			self.console.print("[red]Usage: bot run <name> [params_json] [--debug|-v][/red]")
			return

		name = parts[0]
		debug_mode = "--debug" in parts or "-v" in parts

		# Extract params (everything between name and flags)
		params_str = '{"step":"pre_market"}'
		if len(parts) > 1 and parts[1] not in ("--debug", "-v"):
			params_str = parts[1]

		# Load bot
		bot_config = self.manager.get_bot(name)
		if not bot_config:
			self.console.print(f"[red]Bot not found: {name}[/red]")
			return

		# Parse parameters
		try:
			params = json.loads(params_str)
			if not isinstance(params, dict):
				params = {"step": "pre_market"}
		except json.JSONDecodeError:
			self.console.print(f"[red]Invalid JSON params: {params_str}[/red]")
			return
		except Exception as e:
			self.console.print(f"[red]Error parsing params: {str(e)}[/red]")
			return

		# Set default step if not provided
		if "step" not in params:
			params["step"] = "pre_market"

		try:
			self.console.print(f"[cyan]Running bot: {name}[/cyan]")
			if debug_mode:
				self.console.print(f"[yellow][DEBUG MODE][/yellow]")
			self.console.print(f"[dim]Step: {params.get('step')}[/dim]")
			self.console.print(f"[dim]Params: {json.dumps(params)}[/dim]\n")

			# Create and run BotFinance instance
			bot_dir = self.manager.get_bot_dir(name)
			bot = BotFinance(name, bot_dir)

			# Enable debug logging if requested
			if debug_mode:
				bot.logger.enable_debug()

			# Force bot to active state for execution (CLI override)
			bot.activate()

			# Execute bot
			start_time = time.time()
			result = bot.run(params=params)
			execution_time = (time.time() - start_time) * 1000  # Convert to ms

			# Display results
			if result["status"] == "success":
				output = result.get("output", {})
				self.console.print(f"[green]✓ Bot execution completed[/green]\n")

				# Build result table
				result_table = Table(title=f"Bot Execution Results: {name}")
				result_table.add_column("Metric", style="cyan")
				result_table.add_column("Value", style="green")

				result_table.add_row("Status", "✓ Success")
				result_table.add_row("Step", output.get("step", "-"))
				result_table.add_row("Execution Time", f"{execution_time:.2f}ms")

				# Step-specific rows
				step = output.get("step", "")
				if step == "pre_market":
					agents = output.get("agents_executed", [])
					result_table.add_row("Agents Executed", str(len(agents)))
					for agent in agents:
						result_table.add_row(f"  └─ {agent}", "✓")
					result_table.add_row("Market Data Points", str(len(output.get("data_history", {}))))
					result_table.add_row("Alphas Generated", str(len(output.get("alphas", {}))))
					result_table.add_row("Watchlist Items", str(len(output.get("watchlist", []))))

				elif step == "in_market":
					result_table.add_row("Trades Executed", str(output.get("trades_executed", 0)))
					result_table.add_row("P&L", f"${output.get('pnl', 0):,.2f}")
					result_table.add_row("Open Positions", str(output.get("positions", 0)))

				elif step == "post_market":
					result_table.add_row("Trades Analyzed", str(output.get("trades_analyzed", 0)))
					result_table.add_row("Daily P&L", f"${output.get('pnl_daily', 0):,.2f}")
					result_table.add_row("Positions Closed", str(output.get("positions_closed", 0)))

				result_table.add_row("Timestamp", output.get("timestamp", "-"))

				self.console.print(result_table)

				# Show agent details for pre_market
				if step == "pre_market":
					agents_list = output.get("agents_executed", [])
					if agents_list:
						self.console.print(f"\n[cyan]Agents Executed:[/cyan]")
						for i, agent in enumerate(agents_list, 1):
							self.console.print(f"  {i}. {agent}")

					# Show watchlist if available
					watchlist = output.get("watchlist", [])
					if watchlist:
						from tools.watchlist import WatchlistManager
						wm = WatchlistManager(name, bot_dir=str(bot_dir))
						wl_df = wm.load()
						if wl_df is not None and not wl_df.empty:
							table = Table(title=f"Watchlist: {name} ({len(wl_df)} tickers)")
							table.add_column("Ticker", style="cyan")
							table.add_column("Close", justify="right")
							table.add_column("Score", justify="right", style="green")
							table.add_column("Signals", style="dim")
							for _, row in wl_df.iterrows():
								close = f"{row['close']:.2f}" if row.get("close") is not None else "-"
								score_val = row.get("score", row.get("signal_score"))
								score = f"{score_val:.4f}" if score_val is not None and str(score_val) != "nan" else "-"
								sig_raw = row.get("signals", "")
								signals = str(sig_raw) if sig_raw and str(sig_raw) != "nan" else "-"
								table.add_row(str(row["ticker"]), close, score, signals)
							self.console.print(table)

					# Show alphas summary if available
					alphas = output.get("alphas", {})
					if alphas:
						alpha_count = alphas.get("alpha_count", 0)
						calculated = alphas.get("alphas_calculated", 0)
						alpha_names = alphas.get("alpha_names", [])
						self.console.print(f"\n[cyan]Alphas:[/cyan] {alpha_count} defined, {calculated} calculated")
						if alpha_names:
							preview = ", ".join(alpha_names[:5])
							suffix = f" (+{len(alpha_names)-5} more)" if len(alpha_names) > 5 else ""
							self.console.print(f"  {preview}{suffix}")

			else:
				error_msg = result.get("message", "Unknown error")
				self.console.print(f"[red]✗ Bot execution failed[/red]")
				self.console.print(f"[red]Error: {error_msg}[/red]")

		except Exception as e:
			self.console.print(f"[red]✗ Error running bot: {str(e)}[/red]")
			import traceback
			self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
