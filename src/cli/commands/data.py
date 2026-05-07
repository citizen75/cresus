"""Data management commands."""

from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


class DataCommands:
	"""Data management command handlers."""

	def __init__(self, data_manager):
		"""Initialize with DataManager instance."""
		self.data_manager = data_manager

	def handle(self, args: str):
		"""Handle data commands."""
		args_str = str(args).strip() if args else ""

		if not args_str:
			self._show_help()
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None

		if cmd == "fetch":
			self._handle_fetch(parts)
		elif cmd == "show":
			self._handle_show(parts)
		elif cmd == "list":
			self._handle_list(parts)
		elif cmd == "clear":
			self._handle_clear(parts)
		elif cmd == "stats":
			self._handle_stats()
		elif cmd == "universes":
			self._handle_universes()
		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			console.print("Try: data fetch|show|list|clear|stats|universes")

	def _show_help(self):
		"""Show help for data commands."""
		table = Table(title="Data Management Commands", box=box.ROUNDED)
		table.add_column("Command", style="cyan")
		table.add_column("Description")
		table.add_row("data fetch history <ticker> [start_date]", "Fetch historical data")
		table.add_row("data fetch fundamental <ticker>", "Fetch fundamental data")
		table.add_row("data fetch universe <name> [start_date]", "Fetch all tickers in universe")
		table.add_row("data fetch all <universe> [start_date]", "Fetch history + fundamental for universe")
		table.add_row("data show <ticker>", "Show ticker info (history dates, last OHLCV, fundamentals)")
		table.add_row("data list [history|fundamentals|all]", "List cached data")
		table.add_row("data clear [type] [ticker]", "Clear cache (types: history, fundamentals, all)")
		table.add_row("data stats", "Show cache statistics")
		table.add_row("data universes", "List available universes")
		console.print(table)

	def _handle_fetch(self, parts):
		"""Handle data fetch command."""
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

	def _handle_show(self, parts):
		"""Handle data show command."""
		if len(parts) < 2:
			console.print("[red]✗[/red] Usage: data show <ticker>")
			return
		ticker = parts[1]
		result = self.data_manager.show_ticker_info(ticker)
		self._print_ticker_info(result)

	def _handle_list(self, parts):
		"""Handle data list command."""
		data_type = parts[1] if len(parts) > 1 else "all"
		result = self.data_manager.list_cached(data_type)
		self._print_list_result(result)

	def _handle_clear(self, parts):
		"""Handle data clear command."""
		data_type = parts[1] if len(parts) > 1 else "all"
		ticker = parts[2] if len(parts) > 2 else None
		result = self.data_manager.clear_cache(data_type, ticker)
		self._print_result(result)

	def _handle_stats(self):
		"""Handle data stats command."""
		result = self.data_manager.cache_stats()
		self._print_stats_result(result)

	def _handle_universes(self):
		"""Handle data universes command."""
		from tools.universe.universe import Universe
		universes = Universe.list_universes()
		table = Table(title="Available Universes", box=box.ROUNDED)
		table.add_column("Universe", style="cyan")
		for u in universes:
			table.add_row(u)
		console.print(table)

	def _print_result(self, result):
		"""Print simple result."""
		if result.get("status") == "success":
			console.print(f"[green]✓[/green] {result.get('message', 'Success')}")
		else:
			console.print(f"[red]✗[/red] {result.get('message', 'Error')}")

	def _print_universe_result(self, result):
		"""Print universe fetch result."""
		if result.get("status") == "error":
			console.print(f"[red]✗[/red] {result.get('message')}")
			return

		table = Table(title=f"Data Fetch Results: {result.get('universe')}", box=box.ROUNDED)
		table.add_column("Ticker", style="cyan")
		table.add_column("History", style="green")
		table.add_column("Fundamental", style="green")

		for detail in result.get("details", []):
			ticker = detail.get("ticker", "")
			history_status = detail.get("history", "")
			fundamental_status = detail.get("fundamental", "")

			# Check if both are success
			history_colored = "[green]✓[/green]" if history_status == "success" else "[red]✗[/red]"
			fundamental_colored = "[green]✓[/green]" if fundamental_status == "success" else "[red]✗[/red]"

			table.add_row(ticker, history_colored, fundamental_colored)

		console.print(table)
		console.print(f"\n{result.get('message')}")

	def _print_ticker_info(self, result):
		"""Print ticker information."""
		if result.get("status") == "error":
			console.print(f"[red]✗[/red] {result.get('message')}")
			return

		ticker = result.get("ticker")
		console.print(f"\n[cyan]Ticker: {ticker}[/cyan]")

		# History info
		history = result.get("history", {})
		if "message" in history:
			console.print(f"[yellow]History:[/yellow] {history['message']}")
		else:
			console.print(f"[yellow]History:[/yellow] {history.get('start_date')} to {history.get('end_date')} ({history.get('total_rows')} rows)")

		# Last OHLCV
		last_ohlcv = result.get("last_ohlcv", {})
		if "message" in last_ohlcv:
			console.print(f"[yellow]Last OHLCV:[/yellow] {last_ohlcv['message']}")
		else:
			console.print(f"[yellow]Last OHLCV ({last_ohlcv.get('date')}):[/yellow] O={last_ohlcv.get('open')} H={last_ohlcv.get('high')} L={last_ohlcv.get('low')} C={last_ohlcv.get('close')} V={last_ohlcv.get('volume')}")

		# Fundamental
		fundamental = result.get("fundamental", {})
		if "message" in fundamental:
			console.print(f"[yellow]Fundamental:[/yellow] {fundamental['message']}")
		else:
			company = fundamental.get("company", {})
			quotation = fundamental.get("quotation", {})
			console.print(f"[yellow]Fundamental:[/yellow] {company.get('name', 'N/A')} - Price: {quotation.get('current_price', 'N/A')}")

	def _print_list_result(self, result):
		"""Print list of cached data."""
		if result.get("status") == "error":
			console.print(f"[red]✗[/red] {result.get('message')}")
			return

		console.print(f"[cyan]History:[/cyan] {result.get('total_history')} files")
		console.print(f"[cyan]Fundamentals:[/cyan] {result.get('total_fundamentals')} files")

	def _print_stats_result(self, result):
		"""Print cache statistics."""
		if result.get("status") == "error":
			console.print(f"[red]✗[/red] {result.get('message')}")
			return

		table = Table(title="Cache Statistics", box=box.ROUNDED)
		table.add_column("Type", style="cyan")
		table.add_column("Count", justify="right")
		table.add_column("Size (MB)", justify="right", style="yellow")

		history = result.get("history", {})
		fundamentals = result.get("fundamentals", {})

		table.add_row("History", str(history.get("count", 0)), f"{history.get('size_mb', 0):.2f}")
		table.add_row("Fundamentals", str(fundamentals.get("count", 0)), f"{fundamentals.get('size_mb', 0):.2f}")
		table.add_row("[bold]Total[/bold]", f"{history.get('count', 0) + fundamentals.get('count', 0)}", f"[bold]{result.get('total_size_mb', 0):.2f}[/bold]")

		console.print(table)
