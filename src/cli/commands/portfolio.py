"""Portfolio management commands (orders, watchlist)."""

import json
import os
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich import box
from cli.query import PortfolioQuery

console = Console()


class PortfolioCommands:
	"""Portfolio management command handlers."""

	def handle(self, args: str):
		"""Handle portfolio commands."""
		args_str = str(args).strip() if args else ""

		if not args_str:
			self._show_help()
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None
		has_mcp = "--mcp" in args_str
		has_query = "--query" in args_str

		if cmd == "list":
			portfolio_type = None
			# Extract portfolio type if present (and it's not a flag)
			for part in parts[1:]:
				if not part.startswith("--"):
					portfolio_type = part
					break
			portfolio_type = portfolio_type or "all"

			if has_mcp or has_query:
				# Use query layer for JSON output
				query = PortfolioQuery()
				result = query.list_portfolios()
				output_mode = "json"
				self._display_result("portfolios", result, output_mode)
			else:
				# Use old method for table output
				self._list_portfolios(portfolio_type)
		elif cmd in ["positions", "metrics", "performance", "allocation", "value"]:
			self.handle_query(args_str)
		elif cmd == "orders":
			self.handle_orders(args_str[len(cmd):].strip())
		elif cmd == "watchlist":
			self.handle_watchlist(args_str[len(cmd):].strip())
		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			self._show_help()

	def _show_help(self):
		"""Show help for portfolio commands."""
		table = Table(title="Portfolio Commands", box=box.ROUNDED)
		table.add_column("Command", style="cyan")
		table.add_column("Description")
		table.add_row("portfolio list [real|paper|all]", "List portfolios (default: all)")
		table.add_row("portfolio positions <name> [--mcp|--query]", "Show portfolio positions")
		table.add_row("portfolio metrics <name> [--mcp|--query]", "Show portfolio metrics")
		table.add_row("portfolio performance <name> [--mcp|--query]", "Show performance data")
		table.add_row("portfolio allocation <name> [--mcp|--query]", "Show asset allocation")
		table.add_row("portfolio value <name> [--mcp|--query]", "Show portfolio value")
		table.add_row("orders list <strategy>", "List orders for a strategy")
		table.add_row("watchlist show <strategy>", "Show watchlist")
		table.add_row("watchlist extended <strategy>", "Show watchlist with indicators")
		table.add_row("watchlist train <strategy>", "Train ranking model")
		table.add_row("watchlist rank <strategy>", "Rank tickers using model")
		console.print(table)

	def _list_portfolios(self, portfolio_type: str = "all"):
		"""List portfolios filtered by type."""
		try:
			from tools.portfolio.manager import PortfolioManager

			pm = PortfolioManager()
			all_portfolios = pm.list_portfolios()

			# Filter by type
			if portfolio_type.lower() == "real":
				portfolios = [pf for pf in all_portfolios if pf.get("type") == "real"]
				title = "Real Portfolios"
			elif portfolio_type.lower() == "paper":
				portfolios = [pf for pf in all_portfolios if pf.get("type") == "paper"]
				title = "Paper Portfolios"
			else:  # all
				portfolios = all_portfolios
				title = "All Portfolios"

			if not portfolios:
				console.print(f"[yellow]⚠[/yellow] No {portfolio_type} portfolios found")
				return

			# Create table
			table = Table(title=title, box=box.ROUNDED)
			table.add_column("Name", style="cyan")
			table.add_column("Type", style="magenta")
			table.add_column("Currency", style="yellow")
			table.add_column("Initial Capital", justify="right", style="green")
			table.add_column("Description")

			for pf in portfolios:
				name = pf.get("name", "-")
				pf_type = pf.get("type", "paper")
				currency = pf.get("currency", "EUR")
				initial_capital = pf.get("initial_capital", 0)
				description = pf.get("description", "")

				table.add_row(
					name,
					pf_type,
					currency,
					f"${initial_capital:,.0f}" if initial_capital else "-",
					description[:40] if description else "-"
				)

			console.print(table)
			console.print(f"\n[dim]Total: {len(portfolios)} portfolio(ies)[/dim]")

		except Exception as e:
			console.print(f"[red]✗[/red] Error listing portfolios: {e}")

	def handle_orders(self, args: str):
		"""Handle orders commands."""
		args_str = str(args).strip() if args else ""

		if not args_str:
			table = Table(title="Orders Management Commands", box=box.ROUNDED)
			table.add_column("Command", style="cyan")
			table.add_column("Description")
			table.add_row("orders list <strategy>", "List all orders for a strategy (e.g., momentum_cac)")
			console.print(table)
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None

		if cmd == "list":
			if len(parts) < 2:
				console.print("[red]✗[/red] Usage: orders list <strategy>")
				return
			strategy = parts[1]
			self._print_orders(strategy)
		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			console.print("Try: orders list <strategy>")

	def handle_query(self, args: str):
		"""Handle portfolio data queries (positions, metrics, performance, etc)."""
		args_str = str(args).strip() if args else ""

		if not args_str:
			console.print("[red]✗[/red] Usage: portfolio <command> <portfolio_name> [--mcp|--query]")
			return

		# Parse arguments
		parts = args_str.split()
		cmd = parts[0] if parts else None
		has_mcp = "--mcp" in args_str
		has_query = "--query" in args_str
		output_mode = "json" if (has_mcp or has_query) else "table"

		# Get portfolio name
		portfolio_name = parts[1] if len(parts) > 1 else None
		if not portfolio_name:
			console.print(f"[red]✗[/red] Usage: portfolio {cmd} <portfolio_name> [--mcp|--query]")
			return

		try:
			query = PortfolioQuery()

			if cmd == "positions":
				result = query.get_positions(portfolio_name)
				self._display_result("positions", result, output_mode)
			elif cmd == "metrics":
				result = query.get_metrics(portfolio_name)
				self._display_result("metrics", result, output_mode)
			elif cmd == "performance":
				result = query.get_performance(portfolio_name)
				self._display_result("performance", result, output_mode)
			elif cmd == "allocation":
				result = query.get_allocation(portfolio_name)
				self._display_result("allocation", result, output_mode)
			elif cmd == "value":
				result = query.get_value(portfolio_name)
				self._display_result("value", result, output_mode)
			else:
				console.print(f"[red]✗[/red] Unknown command: {cmd}")
		except Exception as e:
			console.print(f"[red]✗[/red] Error: {str(e)}")

	def _display_result(self, result_type: str, result: dict, output_mode: str):
		"""Display result based on output mode."""
		if result.get("status") == "error":
			console.print(f"[red]✗[/red] {result.get('message')}")
			return

		if output_mode == "json":
			# Output as JSON
			console.print(json.dumps(result, indent=2))
		else:
			# Output as formatted table
			if result_type == "portfolios":
				self._display_portfolios(result)
			elif result_type == "positions":
				self._display_positions(result)
			elif result_type == "metrics":
				self._display_metrics(result)
			elif result_type == "performance":
				self._display_performance(result)
			elif result_type == "allocation":
				self._display_allocation(result)
			elif result_type == "value":
				self._display_value(result)

	def _display_portfolios(self, result: dict):
		"""Display portfolios as rich table."""
		portfolios = result.get("portfolios", [])
		if not portfolios:
			console.print("[yellow]⚠[/yellow] No portfolios found")
			return

		table = Table(title="Portfolios", box=box.ROUNDED)
		table.add_column("Name", style="cyan")
		table.add_column("Type", style="magenta")
		table.add_column("Currency", style="yellow")
		table.add_column("Value", justify="right", style="green")
		table.add_column("Positions", justify="right", style="blue")

		for p in portfolios:
			value_str = f"${p['value']:,.2f}" if p['value'] else "-"
			table.add_row(p["name"], p["type"], p["currency"], value_str, str(p["positions"]))

		console.print(table)
		console.print(f"\n[dim]Total: {result['count']} portfolio(ies)[/dim]")

	def _display_positions(self, result: dict):
		"""Display positions as rich table."""
		positions = result.get("positions", [])
		portfolio = result.get("portfolio")

		if not positions:
			console.print(f"[yellow]⚠[/yellow] No positions in {portfolio}")
			return

		table = Table(title=f"Positions - {portfolio}", box=box.ROUNDED)
		table.add_column("Ticker", style="cyan")
		table.add_column("Qty", justify="right", style="blue")
		table.add_column("Entry Price", justify="right", style="yellow")
		table.add_column("Current Price", justify="right", style="yellow")
		table.add_column("Position Value", justify="right", style="green")
		table.add_column("PnL", justify="right", style="white")
		table.add_column("PnL %", justify="right", style="white")

		for p in positions:
			entry_price = p.get('avg_entry_price') or p.get('entry_price')
			entry = f"${entry_price:.2f}" if entry_price else "-"
			current = f"${p['current_price']:.2f}" if p['current_price'] else "-"
			pos_value = f"${p['position_value']:,.2f}" if p['position_value'] else "-"
			qty = str(int(p['quantity'])) if p['quantity'] else "-"

			pnl = p.get("position_gain")
			pnl_pct = p.get("position_gain_pct")
			pnl_str = f"${pnl:,.2f}" if pnl else "-"
			pnl_pct_str = f"{pnl_pct:+.2f}%" if pnl_pct else "-"

			if pnl and pnl > 0:
				pnl_str = f"[green]{pnl_str}[/green]"
				pnl_pct_str = f"[green]{pnl_pct_str}[/green]"
			elif pnl and pnl < 0:
				pnl_str = f"[red]{pnl_str}[/red]"
				pnl_pct_str = f"[red]{pnl_pct_str}[/red]"

			table.add_row(p["ticker"], qty, entry, current, pos_value, pnl_str, pnl_pct_str)

		console.print(table)
		console.print(f"\n[dim]Total positions: {result['count']}[/dim]")

	def _display_metrics(self, result: dict):
		"""Display metrics as formatted output."""
		metrics = result.get("metrics", {})
		portfolio = result.get("portfolio")

		console.print(f"\n[bold cyan]Portfolio Metrics - {portfolio}[/bold cyan]\n")

		metric_list = [
			("Total Return", metrics.get("total_return"), "%"),
			("Sharpe Ratio", metrics.get("sharpe_ratio"), ""),
			("Max Drawdown", metrics.get("max_drawdown"), "%"),
			("Win Rate", metrics.get("win_rate"), "%"),
			("Profit Factor", metrics.get("profit_factor"), ""),
			("Volatility", metrics.get("volatility"), "%"),
		]

		for label, value, unit in metric_list:
			if value is not None:
				value_str = f"{value:.4f}" if isinstance(value, float) and abs(value) < 1 else f"{value:.2f}"
				console.print(f"  {label:.<30} {value_str} {unit}".rstrip())
			else:
				console.print(f"  {label:.<30} N/A")

	def _display_performance(self, result: dict):
		"""Display performance data."""
		data = result.get("data", {})
		portfolio = result.get("portfolio")

		console.print(f"\n[bold cyan]Portfolio Performance - {portfolio}[/bold cyan]\n")
		console.print(json.dumps(data, indent=2))

	def _display_allocation(self, result: dict):
		"""Display asset allocation."""
		allocation = result.get("allocation", [])
		portfolio = result.get("portfolio")

		console.print(f"\n[bold cyan]Asset Allocation - {portfolio}[/bold cyan]\n")

		if allocation:
			table = Table(box=box.ROUNDED)
			table.add_column("Ticker", style="cyan")
			table.add_column("Weight %", justify="right", style="yellow")
			table.add_column("Value", justify="right", style="green")

			for item in allocation:
				table.add_row(
					item.get("ticker", "-"),
					f"{item.get('weight', 0):.2f}%",
					f"${item.get('value', 0):,.2f}"
				)

			console.print(table)
		else:
			console.print("[yellow]⚠[/yellow] No allocation data available")

	def _display_value(self, result: dict):
		"""Display portfolio value."""
		portfolio = result.get("portfolio")

		console.print(f"\n[bold cyan]Portfolio Value - {portfolio}[/bold cyan]\n")

		total_value = result.get("total_value", 0)
		invested = result.get("invested", 0)
		cash = result.get("cash", 0)

		console.print(f"  Total Value:    ${total_value:,.2f}")
		console.print(f"  Invested:       ${invested:,.2f}")
		console.print(f"  Cash:           ${cash:,.2f}")

		if total_value > 0:
			allocated_pct = (invested / total_value) * 100
			console.print(f"  Allocation:     {allocated_pct:.1f}%")

	def handle_watchlist(self, args: str):
		"""Handle watchlist commands."""
		args_str = str(args).strip() if args else ""

		if not args_str:
			table = Table(title="Watchlist Commands", box=box.ROUNDED)
			table.add_column("Command", style="cyan")
			table.add_column("Description")
			table.add_row("watchlist show <strategy>", "Show watchlist with OHLCV and signal scores")
			table.add_row("watchlist extended <strategy>", "Show watchlist with detailed technical indicators")
			table.add_row("watchlist train <strategy>", "Train LGBM ranking model for strategy")
			table.add_row("watchlist rank <strategy>", "Rank tickers using LGBM model")
			console.print(table)
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None

		if cmd == "show":
			if len(parts) < 2:
				console.print("[red]✗[/red] Usage: watchlist show <strategy>")
				return
			strategy = parts[1]
			self._print_watchlist(strategy)
		elif cmd == "extended":
			if len(parts) < 2:
				console.print("[red]✗[/red] Usage: watchlist extended <strategy>")
				return
			strategy = parts[1]
			self._print_watchlist_extended(strategy)
		elif cmd == "train":
			if len(parts) < 2:
				console.print("[red]✗[/red] Usage: watchlist train <strategy>")
				return
			strategy = parts[1]
			self._train_ranking_model(strategy)
		elif cmd == "rank":
			if len(parts) < 2:
				console.print("[red]✗[/red] Usage: watchlist rank <strategy>")
				return
			strategy = parts[1]
			self._rank_watchlist(strategy)
		else:
			# Support legacy format: watchlist <strategy> (assumes show)
			strategy = cmd
			self._print_watchlist(strategy)

	def _print_orders(self, strategy: str):
		"""Display orders for a strategy."""
		try:
			from tools.portfolio.orders import Orders

			# Strategy name maps to portfolio name (normalize to snake_case)
			portfolio_name = strategy.lower().replace(" ", "_")

			orders = Orders(portfolio_name)
			df = orders.get_all_orders()

			if df.empty:
				console.print(f"[yellow]⚠[/yellow] No orders found for strategy '{strategy}'")
				return

			# Create table for orders
			table = Table(title=f"Orders for {strategy}", box=box.ROUNDED)
			table.add_column("ID", style="dim")
			table.add_column("Created", style="cyan")
			table.add_column("Ticker", style="blue", no_wrap=True)
			table.add_column("Qty", justify="right", style="magenta")
			table.add_column("Entry", justify="right", style="yellow")
			table.add_column("Stop Loss", justify="right", style="red")
			table.add_column("Take Profit", justify="right", style="green")
			table.add_column("Method", style="white")
			table.add_column("Status", style="cyan")

			# Sort by created_at descending
			df_sorted = df.sort_values("created_at", ascending=False, na_position="last")

			for _, row in df_sorted.iterrows():
				order_id = str(row.get("id", ""))[:8]
				created_at = str(row.get("created_at", ""))
				if "T" in created_at:
					created_at = created_at.split("T")[1][:8]  # Show time only
				ticker = str(row.get("ticker", ""))
				qty = str(int(float(row.get("quantity", 0)))) if pd.notna(row.get("quantity")) else "-"
				entry = f"{float(row.get('entry_price', 0)):.2f}" if pd.notna(row.get("entry_price")) else "-"
				stop = f"{float(row.get('stop_loss', 0)):.2f}" if pd.notna(row.get("stop_loss")) else "-"
				target = f"{float(row.get('take_profit', 0)):.2f}" if pd.notna(row.get("take_profit")) else "-"
				method = str(row.get("execution_method", "market"))
				status = str(row.get("status", "pending"))

				# Color status
				if status.lower() == "pending":
					status_colored = "[yellow]⧗ Pending[/yellow]"
				elif status.lower() == "executed":
					status_colored = "[green]✓ Executed[/green]"
				elif status.lower() == "cancelled":
					status_colored = "[red]✗ Cancelled[/red]"
				else:
					status_colored = f"[dim]{status}[/dim]"

				table.add_row(order_id, created_at, ticker, qty, entry, stop, target, method, status_colored)

			console.print(table)

			# Show summary
			pending = len(df[df["status"].str.lower() == "pending"])
			executed = len(df[df["status"].str.lower() == "executed"])
			cancelled = len(df[df["status"].str.lower() == "cancelled"])

			summary = f"Total: {len(df)} | [yellow]⧗ Pending: {pending}[/yellow] | [green]✓ Executed: {executed}[/green] | [red]✗ Cancelled: {cancelled}[/red]"
			console.print(f"\n{summary}")

		except FileNotFoundError:
			console.print(f"[yellow]⚠[/yellow] No orders file found for strategy '{strategy}'")
		except Exception as e:
			console.print(f"[red]✗[/red] Error loading orders: {e}")

	def _print_watchlist(self, strategy: str):
		"""Display watchlist for a strategy."""
		try:
			from tools.watchlist.watchlist_manager import WatchlistManager

			wm = WatchlistManager(strategy)
			df = wm.load()

			if df is None or df.empty:
				console.print(f"[yellow]⚠[/yellow] No watchlist found for strategy '{strategy}'")
				return

			# Create table for watchlist
			table = Table(title=f"Watchlist: {strategy}", box=box.ROUNDED)
			table.add_column("Ticker", style="cyan", no_wrap=True)
			table.add_column("Date", style="dim")
			table.add_column("Close", justify="right", style="yellow")
			table.add_column("High", justify="right", style="green")
			table.add_column("Low", justify="right", style="red")
			table.add_column("Volume", justify="right", style="magenta")
			table.add_column("Signal Score", justify="right", style="blue")
			table.add_column("Signals", style="white")

			# Sort by signal_score descending
			df_sorted = df.sort_values("signal_score", ascending=False, na_position="last")

			for _, row in df_sorted.iterrows():
				ticker = str(row.get("ticker", ""))
				date = str(row.get("date", ""))
				if date and "T" in date:
					date = date.split("T")[0]  # Show date only
				elif pd.isna(row.get("date")):
					date = "-"

				close = f"{float(row.get('close', 0)):.2f}" if pd.notna(row.get("close")) else "-"
				high = f"{float(row.get('high', 0)):.2f}" if pd.notna(row.get("high")) else "-"
				low = f"{float(row.get('low', 0)):.2f}" if pd.notna(row.get("low")) else "-"

				volume = row.get("volume")
				if pd.notna(volume):
					try:
						vol_int = int(float(volume))
						if vol_int >= 1_000_000:
							volume_str = f"{vol_int / 1_000_000:.1f}M"
						elif vol_int >= 1_000:
							volume_str = f"{vol_int / 1_000:.1f}K"
						else:
							volume_str = str(vol_int)
					except (ValueError, TypeError):
						volume_str = "-"
				else:
					volume_str = "-"

				score = row.get("signal_score")
				if pd.notna(score):
					score_str = f"{float(score):.3f}"
					# Color score based on value
					if float(score) > 0.7:
						score_str = f"[green]{score_str}[/green]"
					elif float(score) > 0.4:
						score_str = f"[yellow]{score_str}[/yellow]"
					else:
						score_str = f"[red]{score_str}[/red]"
				else:
					score_str = "-"

				signals = str(row.get("signals", ""))
				if signals and signals.lower() != "nan":
					# Limit signals display to 50 chars
					if len(signals) > 50:
						signals = signals[:47] + "..."
				else:
					signals = "-"

				table.add_row(ticker, date, close, high, low, volume_str, score_str, signals)

			console.print(table)

			# Show summary
			console.print(f"\n[dim]Total tickers: {len(df)}[/dim]")
			avg_score = df["signal_score"].mean() if "signal_score" in df.columns else 0
			if not pd.isna(avg_score):
				console.print(f"[dim]Average signal score: {float(avg_score):.3f}[/dim]")

		except FileNotFoundError:
			console.print(f"[yellow]⚠[/yellow] No watchlist file found for strategy '{strategy}'")
		except Exception as e:
			console.print(f"[red]✗[/red] Error loading watchlist: {e}")

	def _print_watchlist_extended(self, strategy: str):
		"""Display watchlist with detailed technical indicators."""
		try:
			from tools.watchlist.watchlist_manager import WatchlistManager
			from tools.data.core import DataHistory
			import numpy as np

			wm = WatchlistManager(strategy)
			df = wm.load()

			if df is None or df.empty:
				console.print(f"[yellow]⚠[/yellow] No watchlist found for strategy '{strategy}'")
				return

			console.print(f"\n[cyan bold]Extended Watchlist Analysis: {strategy}[/cyan bold]\n")

			# Sort by signal_score descending
			df_sorted = df.sort_values("signal_score", ascending=False, na_position="last")

			for idx, (_, row) in enumerate(df_sorted.iterrows(), 1):
				ticker = str(row.get("ticker", ""))
				console.print(f"\n[bold]{idx}. {ticker}[/bold] - Score: {float(row.get('signal_score', 0)):.3f}")
				console.print("─" * 80)

				# Load historical data for this ticker
				try:
					dh = DataHistory(ticker)
					price_data = dh.get_all()

					if price_data.empty:
						console.print(f"[yellow]⚠ No price data available[/yellow]")
						continue

					indicators = self._calculate_extended_indicators(price_data, ticker)

					# VOLATILITY & STOPS section
					self._print_indicator_section(
						"VOLATILITY & STOPS",
						[
							("14-day ATR", indicators.get("atr_14"), "€"),
							("20-day Volatility", indicators.get("volatility_20"), "%"),
							("Suggested stop loss", indicators.get("suggested_stop"), "%"),
						]
					)

					# MOMENTUM STRENGTH section
					self._print_indicator_section(
						"MOMENTUM STRENGTH",
						[
							("RSI(14)", indicators.get("rsi_14"), "0-100"),
							("MACD histogram", indicators.get("macd_signal"), "positive/negative"),
							("Rate of Change (10-day)", indicators.get("roc_10"), "%"),
						]
					)

					# PRICE ACTION section
					self._print_indicator_section(
						"PRICE ACTION",
						[
							("5-day MA / 20-day MA", f"{indicators.get('ma5'):.2f} / {indicators.get('ma20'):.2f}", "aligned?" if indicators.get('ma_aligned') else "misaligned"),
							("Nearest resistance", indicators.get("resistance"), "€"),
							("Nearest support", indicators.get("support"), "€"),
							("Entry trigger", indicators.get("entry_level"), "price level"),
						]
					)

					# LIQUIDITY section
					self._print_indicator_section(
						"LIQUIDITY",
						[
							("Bid-ask spread", indicators.get("bid_ask_spread"), "bps"),
							("Avg daily volume (last 20d)", indicators.get("avg_volume_20d"), "shares"),
							("Slippage risk (1M+ trade)", indicators.get("slippage_1m"), "bps"),
						]
					)

					# EDGE VALIDATION section
					self._print_indicator_section(
						"EDGE VALIDATION",
						[
							("Historical win rate", indicators.get("win_rate"), "%"),
							("Avg 10-day return", indicators.get("avg_return_10d"), "%"),
							("Max drawdown", indicators.get("max_drawdown"), "%"),
						]
					)

				except Exception as e:
					console.print(f"[yellow]⚠ Error loading indicators: {e}[/yellow]")

			console.print("\n")

		except FileNotFoundError:
			console.print(f"[yellow]⚠[/yellow] No watchlist file found for strategy '{strategy}'")
		except Exception as e:
			console.print(f"[red]✗[/red] Error loading watchlist: {e}")

	def _print_indicator_section(self, title: str, indicators: list):
		"""Print a section of indicators with formatting."""
		console.print(f"[magenta]{title}[/magenta]")
		for i, (label, value, unit) in enumerate(indicators):
			is_last = i == len(indicators) - 1
			prefix = "└─" if is_last else "├─"

			if value is None or (isinstance(value, str) and value.lower() == "n/a"):
				value_str = "[dim]N/A[/dim]"
			elif isinstance(value, (int, float)):
				if unit == "0-100":
					color = "green" if value > 50 else "red"
					value_str = f"[{color}]{value:.1f}[/{color}]"
				elif unit in ["%", "bps"]:
					color = "green" if value >= 0 else "red"
					value_str = f"[{color}]{value:+.2f}[/{color}]"
				else:
					value_str = f"{value:.2f}"
			else:
				value_str = str(value)

			console.print(f"{prefix} {label}: {value_str} ({unit})")

	def _calculate_extended_indicators(self, price_data, ticker):
		"""Calculate extended technical indicators from price data."""
		try:
			import numpy as np

			# Ensure data is sorted by timestamp
			if hasattr(price_data, 'index'):
				price_data = price_data.sort_index()
			else:
				price_data = price_data.sort_values('timestamp')

			# Extract OHLCV
			close = price_data['close'].values if 'close' in price_data.columns else price_data.iloc[:, 4].values
			high = price_data['high'].values if 'high' in price_data.columns else price_data.iloc[:, 2].values
			low = price_data['low'].values if 'low' in price_data.columns else price_data.iloc[:, 3].values
			volume = price_data['volume'].values if 'volume' in price_data.columns else price_data.iloc[:, 5].values

			indicators = {}

			# VOLATILITY & STOPS
			# 14-day ATR
			if len(price_data) >= 14:
				tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1]))
				atr_14 = np.mean(tr[-14:])
				indicators['atr_14'] = round(atr_14, 2)
			else:
				indicators['atr_14'] = None

			# 20-day volatility
			if len(close) >= 20:
				returns = np.diff(close[-20:]) / close[-21:-1]
				volatility = np.std(returns) * 100
				indicators['volatility_20'] = round(volatility, 2)
				indicators['suggested_stop'] = round(volatility * 1.5, 2)
			else:
				indicators['volatility_20'] = None
				indicators['suggested_stop'] = None

			# MOMENTUM STRENGTH
			# RSI(14)
			if len(close) >= 14:
				delta = np.diff(close)
				gain = np.where(delta > 0, delta, 0)
				loss = np.where(delta < 0, -delta, 0)
				avg_gain = np.mean(gain[-14:])
				avg_loss = np.mean(loss[-14:])
				rs = avg_gain / avg_loss if avg_loss != 0 else 0
				rsi = 100 - (100 / (1 + rs))
				indicators['rsi_14'] = round(rsi, 1)
			else:
				indicators['rsi_14'] = None

			# MACD (simplified)
			if len(close) >= 26:
				ema_12 = self._calculate_ema(close, 12)
				ema_26 = self._calculate_ema(close, 26)
				macd = ema_12[-1] - ema_26[-1]
				indicators['macd_signal'] = "positive" if macd > 0 else "negative"
			else:
				indicators['macd_signal'] = None

			# Rate of Change (10-day)
			if len(close) >= 10:
				roc = ((close[-1] - close[-10]) / close[-10]) * 100
				indicators['roc_10'] = round(roc, 2)
			else:
				indicators['roc_10'] = None

			# PRICE ACTION
			if len(close) >= 20:
				indicators['ma5'] = np.mean(close[-5:])
				indicators['ma20'] = np.mean(close[-20:])
				indicators['ma_aligned'] = indicators['ma5'] > indicators['ma20']
			else:
				indicators['ma5'] = None
				indicators['ma20'] = None
				indicators['ma_aligned'] = False

			# Resistance and Support (simple pivot calculation)
			if len(price_data) >= 5:
				recent_high = np.max(high[-5:])
				recent_low = np.min(low[-5:])
				indicators['resistance'] = round(recent_high * 1.02, 2)
				indicators['support'] = round(recent_low * 0.98, 2)
				indicators['entry_level'] = round(close[-1], 2)
			else:
				indicators['resistance'] = None
				indicators['support'] = None
				indicators['entry_level'] = None

			# LIQUIDITY
			# Bid-ask spread (estimated - typically not available in OHLCV)
			indicators['bid_ask_spread'] = "N/A"

			# Avg daily volume
			if len(volume) >= 20:
				indicators['avg_volume_20d'] = int(np.mean(volume[-20:]))
				# Slippage estimation
				slippage = (close[-1] * 0.0001) if indicators['avg_volume_20d'] > 1000000 else 5
				indicators['slippage_1m'] = round(slippage, 1)
			else:
				indicators['avg_volume_20d'] = None
				indicators['slippage_1m'] = None

			# EDGE VALIDATION (placeholder - would need trade history)
			indicators['win_rate'] = "N/A"
			indicators['avg_return_10d'] = "N/A"
			indicators['max_drawdown'] = "N/A"

			return indicators

		except Exception as e:
			console.print(f"[yellow]Warning: Could not calculate indicators - {e}[/yellow]")
			return {}

	def _calculate_ema(self, data, period):
		"""Calculate Exponential Moving Average."""
		ema = np.zeros(len(data))
		sma = np.mean(data[:period])
		ema[period - 1] = sma

		multiplier = 2 / (period + 1)

		for i in range(period, len(data)):
			ema[i] = (data[i] * multiplier) + (ema[i - 1] * (1 - multiplier))

		return ema

	def _train_ranking_model(self, strategy: str):
		"""Train LGBM ranking model for a strategy."""
		try:
			from core.context import AgentContext
			from agents.strategy.agent import StrategyAgent
			from agents.data.agent import DataAgent
			from agents.watchlist_ranking.agent import WatchlistRankingAgent
			from pathlib import Path

			console.print(f"\n[cyan]Training LGBM ranking model for {strategy}...[/cyan]\n")

			# Create context and load data
			ctx = AgentContext()

			# Load strategy
			strategy_agent = StrategyAgent(f"strategy[{strategy}]", ctx)
			result = strategy_agent.process({})
			if result.get("status") != "success":
				console.print(f"[red]✗[/red] Failed to load strategy: {result.get('message')}")
				return

			# Load data
			data_agent = DataAgent(f"data[{strategy}]", ctx)
			result = data_agent.process({})
			if result.get("status") != "success":
				console.print(f"[red]✗[/red] Failed to load data: {result.get('message')}")
				return

			tickers_loaded = result.get("output", {}).get("data_after_quantity_filter", 0)
			console.print(f"  Data loaded: {tickers_loaded} tickers")
			console.print(f"  Features extracted: {result.get('output', {}).get('indicators_count', 0)} indicators\n")

			# Train model
			ranking_agent = WatchlistRankingAgent("RankingAgent", ctx)
			result = ranking_agent.train(strategy)

			if result.get("status") == "success":
				output = result.get("output", {})
				model_path = output.get("model_path", "")
				samples = output.get("samples", 0)
				features = output.get("features", 0)
				folds = output.get("folds", 0)
				metrics = output.get("metrics", {})
				fold_results = output.get("fold_results", [])
				fallback = output.get("fallback")

				# Display model info
				if samples and samples > 0 and folds > 0:
					console.print(f"[green]✓[/green] Walk-forward training completed!\n")
					console.print(f"  [bold]Model Path:[/bold] {model_path}")
					console.print(f"  [bold]Storage:[/bold] ~/.cresus/db/models/watchlist_ranking/{Path(model_path).name}")
					console.print(f"  [bold]Total Samples:[/bold] {samples}")
					console.print(f"  [bold]Features:[/bold] {features}")
					console.print(f"  [bold]Folds:[/bold] {folds}\n")

					# Display walk-forward summary
					if metrics and "avg_ic" in metrics:
						console.print("[bold]Walk-Forward Summary[/bold]")
						console.print(f"  Avg IC (Information Coefficient): {metrics.get('avg_ic'):.4f}")
						console.print(f"  Avg RMSE:                        {metrics.get('avg_rmse'):.6f}")
						console.print(f"  Avg MAE:                         {metrics.get('avg_mae'):.6f}")
						console.print(f"  Positive IC Folds:               {metrics.get('positive_ic_pct'):.1f}%\n")

					# Display recent fold details
					if fold_results:
						console.print("[bold]Recent Fold Results (last 10)[/bold]")
						fold_table = Table(box=box.ROUNDED)
						fold_table.add_column("Period", style="cyan")
						fold_table.add_column("Train", justify="right", style="dim")
						fold_table.add_column("Test", justify="right", style="dim")
						fold_table.add_column("RMSE", justify="right")
						fold_table.add_column("IC", justify="right", style="yellow")

						for fold in fold_results[-10:]:
							rmse_color = "green" if fold.get("rmse", 0) < 0.03 else "yellow" if fold.get("rmse", 0) < 0.05 else "red"
							ic_color = "green" if fold.get("ic", 0) > 0.05 else "yellow" if fold.get("ic", 0) > 0 else "red"
							fold_table.add_row(
								fold.get("period", "-"),
								str(fold.get("train_n", 0)),
								str(fold.get("test_n", 0)),
								f"[{rmse_color}]{fold.get('rmse', 0):.6f}[/{rmse_color}]",
								f"[{ic_color}]{fold.get('ic', 0):.4f}[/{ic_color}]"
							)

						console.print(fold_table)
						console.print()

					# Model info
					model_info = output.get("model", {})
					if model_info:
						console.print("[bold]Final Model Configuration[/bold]")
						console.print(f"  Type: {model_info.get('type')}")
						console.print(f"  Boosting Rounds: {model_info.get('rounds')}")
						params = model_info.get("params", {})
						console.print(f"  Learning Rate: {params.get('learning_rate')}")
						console.print(f"  Num Leaves: {params.get('num_leaves')}\n")

				else:
					console.print(f"[yellow]⚠[/yellow] Training completed but no model saved\n")
					console.print(f"  [bold]Reason:[/bold] {metrics.get('reason', 'Insufficient data')}")
					if fallback:
						console.print(f"  [bold]Fallback:[/bold] {fallback}\n")
			else:
				console.print(f"[red]✗[/red] Training failed: {result.get('message')}")

		except Exception as e:
			console.print(f"[red]✗[/red] Error: {str(e)}")

	def _rank_watchlist(self, strategy: str):
		"""Rank tickers using LGBM model."""
		try:
			from core.context import AgentContext
			from agents.strategy.agent import StrategyAgent
			from agents.data.agent import DataAgent
			from agents.watchlist_ranking.agent import WatchlistRankingAgent

			console.print(f"[cyan]Ranking tickers for {strategy}...[/cyan]")

			# Create context and load data
			ctx = AgentContext()

			# Load strategy
			strategy_agent = StrategyAgent(f"strategy[{strategy}]", ctx)
			result = strategy_agent.process({})
			if result.get("status") != "success":
				console.print(f"[red]✗[/red] Failed to load strategy: {result.get('message')}")
				return

			# Load data
			data_agent = DataAgent(f"data[{strategy}]", ctx)
			result = data_agent.process({})
			if result.get("status") != "success":
				console.print(f"[red]✗[/red] Failed to load data: {result.get('message')}")
				return

			# Rank tickers
			ranking_agent = WatchlistRankingAgent("RankingAgent", ctx)
			result = ranking_agent.rank(strategy)

			if result.get("status") == "success":
				output = result.get("output", {})
				ranked = output.get("ranked", [])

				if ranked:
					console.print(f"[green]✓[/green] Ranked {len(output.get('scores', {}))} tickers\n")

					# Display top 20 ranked tickers
					table = Table(title=f"Top Ranked Tickers - {strategy}", box=box.ROUNDED)
					table.add_column("Rank", style="cyan", justify="right")
					table.add_column("Ticker", style="blue", no_wrap=True)
					table.add_column("Score", justify="right", style="yellow")

					for i, (ticker, score) in enumerate(ranked[:20], 1):
						score_str = f"{float(score):.4f}"
						table.add_row(str(i), ticker, score_str)

					console.print(table)
				else:
					console.print("[yellow]⚠[/yellow] No tickers to rank")
			else:
				console.print(f"[red]✗[/red] Ranking failed: {result.get('message')}")

		except Exception as e:
			console.print(f"[red]✗[/red] Error: {str(e)}")
