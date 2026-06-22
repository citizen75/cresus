"""Data management commands."""

from rich.console import Console
from rich.table import Table
from rich import box
import pandas as pd

console = Console()

DEFAULT_INDICATORS = [
	"adx_14", "adx_20", "atr_14", "atr_5", "bb_20_lower", "bb_20_middle",
	"bb_20_upper", "ema_10", "ema_20", "ema_5", "ema_50", "macd_12_26",
	"roc_10", "roc_5", "rsi_14", "rsi_7", "sha_10", "sha_10_green",
	"sha_10_red", "sha_10_up", "sha_10_down", "sha_5", "volume_sma_20"
]


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
		elif cmd == "indicators":
			self._handle_indicators(parts)
		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			console.print("Try: data fetch|show|list|clear|stats|universes|indicators")

	def _show_help(self):
		"""Show help for data commands."""
		table = Table(title="Data Management Commands", box=box.ROUNDED)
		table.add_column("Command", style="cyan")
		table.add_column("Description")
		table.add_row("data fetch history <ticker> [start_date]", "Fetch historical data")
		table.add_row("data fetch fundamental <ticker>", "Fetch fundamental data")
		table.add_row("data fetch universe <name> [start_date]", "Fetch all tickers in universe")
		table.add_row("data fetch all <universe> [start_date]", "Fetch history + fundamental for universe")
		table.add_row("data fetch all --portfolio <name|all> [start_date]", "Fetch history + fundamental for portfolio tickers")
		table.add_row("data fetch ptf <portfolio_name>", "Calculate portfolio history from journal")
		table.add_row("data fetch ptf all", "Fetch fundamental data for all portfolio tickers")
		table.add_row("data show <ticker>", "Show ticker info (history dates, last OHLCV, fundamentals)")
		table.add_row("data list [history|fundamentals|all]", "List cached data")
		table.add_row("data clear [type] [ticker]", "Clear cache (types: history, fundamentals, all)")
		table.add_row("data stats", "Show cache statistics")
		table.add_row("data universes", "List available universes")
		table.add_row("data indicators <ticker> [ind1] [ind2]...", "Show technical indicators for ticker (default: all)")
		console.print(table)

	def _handle_fetch(self, parts):
		"""Handle data fetch command."""
		# Pull out -force/--force as a flag, wherever it appears, before positional parsing
		force = False
		parts = list(parts)
		for flag in ("-force", "--force"):
			if flag in parts:
				parts.remove(flag)
				force = True

		if len(parts) < 2:
			console.print("[red]✗[/red] Usage: data fetch <history|fundamental|universe|all|ptf> [args...] [-force]")
			return

		data_type = parts[1]

		# Check if this is a portfolio fetch (all with --portfolio flag)
		if data_type == "all" and len(parts) >= 4 and parts[2] == "--portfolio":
			portfolio_name = parts[3]
			start_date = parts[4] if len(parts) > 4 else None
			self._handle_fetch_portfolio_data(portfolio_name, start_date)
			return

		# Original behavior for other commands
		if len(parts) < 3:
			console.print("[red]✗[/red] Usage: data fetch <history|fundamental|universe|all|ptf> <ticker|name|universe|portfolio> [start_date]")
			return

		target = parts[2]
		start_date = parts[3] if len(parts) > 3 else None

		if data_type == "history":
			result = self.data_manager.fetch_history(target, start_date, force=force)
			self._print_result(result)
		elif data_type == "fundamental":
			result = self.data_manager.fetch_fundamental(target)
			self._print_result(result)
		elif data_type == "universe":
			result = self.data_manager.fetch_universe(target, start_date, force=force)
			self._print_universe_result(result)
		elif data_type == "all":
			result = self.data_manager.fetch_all(target, start_date, force=force)
			self._print_universe_result(result)
		elif data_type == "ptf":
			self._handle_fetch_portfolio(target)
		else:
			console.print(f"[red]✗[/red] Unknown data type: {data_type}")

	def _handle_fetch_portfolio_data(self, portfolio_name: str, start_date: str = None):
		"""Fetch history and fundamental data for portfolio tickers."""
		from tools.portfolio.manager import PortfolioManager
		from loguru import logger

		try:
			pm = PortfolioManager()

			# Get list of portfolios to process
			portfolios_to_process = []
			if portfolio_name.lower() == "all":
				portfolios_info = pm.list_portfolios()
				# Only include real portfolios (type="real")
				portfolios_to_process = [
					pf_info.get("name") for pf_info in portfolios_info
					if pf_info.get("type") == "real"
				]
			else:
				portfolios_to_process = [portfolio_name]

			if not portfolios_to_process:
				console.print("[yellow]⚠[/yellow] No portfolios found")
				return

			console.print(f"[cyan]Fetching data for {len(portfolios_to_process)} portfolio(s)...[/cyan]")

			total_tickers = set()
			portfolio_tickers = {}

			# Collect tickers from all portfolios
			for pf_name in portfolios_to_process:
				try:
					positions = pm.get_portfolio_positions(pf_name)
					tickers = [pos.get("ticker") for pos in positions.get("positions", [])]
					portfolio_tickers[pf_name] = tickers
					total_tickers.update(tickers)
				except Exception as e:
					console.print(f"[yellow]⚠[/yellow] Could not get positions for {pf_name}: {e}")

			if not total_tickers:
				console.print("[yellow]⚠[/yellow] No open positions found in any portfolio")
				return

			console.print(f"[cyan]Found {len(total_tickers)} unique ticker(s) across {len(portfolios_to_process)} portfolio(s)[/cyan]\n")

			# Fetch data for each ticker
			success_count = 0
			failed_tickers = []

			# Create progress table
			table = Table(title=f"Fetching Data for Portfolio Ticker(s)", box=box.ROUNDED)
			table.add_column("Ticker", style="cyan")
			table.add_column("Portfolios", style="yellow")
			table.add_column("History", style="green")
			table.add_column("Fundamental", style="green")

			for ticker in sorted(total_tickers):
				# Get which portfolios have this ticker
				portfolios_with_ticker = [pf for pf, tickers in portfolio_tickers.items() if ticker in tickers]
				portfolio_str = ", ".join(portfolios_with_ticker)

				try:
					# Fetch history
					history_result = self.data_manager.fetch_history(ticker, start_date)
					history_status = "✓" if history_result.get("status") == "success" else "✗"

					# Fetch fundamental
					fundamental_result = self.data_manager.fetch_fundamental(ticker)
					fundamental_status = "✓" if fundamental_result.get("status") == "success" else "✗"

					if history_result.get("status") == "success" and fundamental_result.get("status") == "success":
						success_count += 1
						history_colored = "[green]✓[/green]"
						fundamental_colored = "[green]✓[/green]"
					else:
						failed_tickers.append(ticker)
						history_colored = "[red]✗[/red]" if history_result.get("status") != "success" else "[green]✓[/green]"
						fundamental_colored = "[red]✗[/red]" if fundamental_result.get("status") != "success" else "[green]✓[/green]"

					table.add_row(ticker, portfolio_str, history_colored, fundamental_colored)

				except Exception as e:
					console.print(f"[yellow]⚠[/yellow] Error fetching data for {ticker}: {e}")
					failed_tickers.append(ticker)
					table.add_row(ticker, portfolio_str, "[red]✗[/red]", "[red]✗[/red]")

			console.print(table)

			# Summary
			console.print(f"\n[green]✓[/green] Successfully fetched {success_count}/{len(total_tickers)} ticker(s)")
			if failed_tickers:
				console.print(f"[yellow]⚠[/yellow] Failed: {', '.join(failed_tickers)}")
			else:
				console.print("[green]✓ All data fetched successfully![/green]")

			console.print(f"[dim]Portfolio data is now cached and available in the API[/dim]")

		except Exception as e:
			console.print(f"[red]✗[/red] Error fetching portfolio data: {e}")
			logger.error(f"Portfolio data fetch error: {e}")

	def _handle_fetch_portfolio(self, portfolio_name):
		"""Handle portfolio history fetch or all portfolio tickers data fetch."""
		from loguru import logger
		from tools.portfolio.manager import PortfolioManager

		# Handle "all" case - fetch data for all portfolio tickers
		if portfolio_name.lower() == "all":
			try:
				console.print(f"[cyan]Fetching fundamental data for all portfolio tickers...[/cyan]")
				pm = PortfolioManager()
				result = pm.fetch_all_ticker_data(days=365)

				if result.get("status") == "error":
					console.print(f"[red]✗[/red] {result.get('message')}")
					return

				# Display results
				tickers_processed = result.get("tickers_processed", 0)
				tickers_total = result.get("tickers_total", 0)
				tickers_failed = result.get("tickers_failed", [])

				console.print(f"[green]✓[/green] Processed {tickers_processed}/{tickers_total} tickers")

				if tickers_failed:
					console.print(f"[yellow]⚠[/yellow] Failed tickers: {', '.join(tickers_failed)}")
				else:
					console.print()

				# Show summary table
				table = Table(title="Portfolio Ticker Data Fetch", box=box.ROUNDED)
				table.add_column("Metric", style="cyan")
				table.add_column("Value", justify="right")
				table.add_row("Total Tickers", str(tickers_total))
				table.add_row("Successfully Fetched", str(tickers_processed))
				table.add_row("Failed", str(len(tickers_failed)))
				table.add_row("Status", "[green]Success[/green]" if result.get("status") == "success" else "[yellow]Partial[/yellow]")

				console.print(table)
				console.print(f"\n[dim]All portfolio ticker data is now cached and available in the API[/dim]")

			except Exception as e:
				console.print(f"[red]✗[/red] Error fetching portfolio ticker data: {e}")
				import traceback
				logger.error(f"Portfolio ticker fetch error: {traceback.format_exc()}")
			return

		# Original behavior - calculate portfolio history
		try:
			from tools.portfolio.portfolio_history import PortfolioHistory

			# Calculate portfolio history
			console.print(f"[cyan]Calculating portfolio history for {portfolio_name}...[/cyan]")

			# Get initial capital from portfolio metadata
			pm = PortfolioManager()
			metadata = pm._get_portfolio_metadata(portfolio_name)
			initial_capital = float(metadata.get("initial_capital", 100000.0))

			# Use PortfolioHistory to calculate
			ph = PortfolioHistory(portfolio_name, initial_capital)
			result = ph.calculate(recalculate=True)

			if result.get("status") == "error":
				console.print(f"[red]✗[/red] {result.get('message')}")
				return

			# Display results
			history = result.get("history", [])
			tickers_loaded = result.get("tickers_loaded", 0)
			tickers_total = result.get("tickers_total", 0)
			failed_tickers = result.get("failed_tickers", [])

			console.print(f"[green]✓[/green] Calculated {len(history)} daily values")
			console.print(f"[cyan]Tickers:[/cyan] {tickers_loaded}/{tickers_total} loaded successfully")

			if failed_tickers:
				console.print(f"[yellow]⚠[/yellow] Failed to fetch data for: {', '.join(failed_tickers)}")
				console.print("[dim]These tickers are invalid or no longer available on Yahoo Finance[/dim]\n")
			else:
				console.print()

			# Show summary
			if history:
				first_entry = history[0]
				last_entry = history[-1]

				table = Table(title=f"Portfolio History: {portfolio_name}", box=box.ROUNDED)
				table.add_column("Metric", style="cyan")
				table.add_column("Value", justify="right")

				table.add_row("Period", f"{first_entry['date']} → {last_entry['date']}")
				table.add_row("Starting Value", f"${first_entry['value']:,.2f}")
				table.add_row("Ending Value", f"${last_entry['value']:,.2f}")

				pnl = last_entry['value'] - first_entry['value']
				pnl_pct = (pnl / first_entry['value'] * 100) if first_entry['value'] > 0 else 0
				pnl_color = "green" if pnl >= 0 else "red"
				table.add_row("P&L", f"[{pnl_color}]${pnl:,.2f} ({pnl_pct:+.2f}%)[/{pnl_color}]")

				table.add_row("Total Days", str(len(history)))

				console.print(table)
				console.print(f"\n[dim]Portfolio history is now cached and available in the API[/dim]")
			else:
				console.print("[yellow]⚠[/yellow] No history data calculated")

		except Exception as e:
			console.print(f"[red]✗[/red] Error calculating portfolio history: {e}")
			import traceback
			logger.error(f"Portfolio history error: {traceback.format_exc()}")

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

	def _calculate_alphas(self, df: pd.DataFrame, indicators: list, indicators_result: dict = None) -> dict:
		"""Calculate all feature alphas from base indicators using formula engine."""
		import yaml
		from pathlib import Path
		from tools.formula.dsl_parser import parse_formula

		alphas_dict = {}
		try:
			# Create enriched DataFrame with calculated indicators
			df_enriched = df.copy()

			# Add calculated indicators to the DataFrame
			if indicators_result:
				for ind_name, ind_series in indicators_result.items():
					if isinstance(ind_series, pd.Series):
						df_enriched[ind_name] = ind_series.values
					else:
						df_enriched[ind_name] = ind_series

			# NOTE: Formula engine now auto-detects and normalizes DataFrame sort order

			# Load alpha definitions from strategy template
			template_path = Path(__file__).parent.parent.parent.parent / "init" / "templates" / "strategy.yml"
			with open(template_path) as f:
				template = yaml.safe_load(f)

			if "features" not in template or "alphas" not in template["features"]:
				return alphas_dict

			alphas_section = template["features"]["alphas"]

			# Iterate through all alpha categories
			for category, alphas_list in alphas_section.items():
				if not isinstance(alphas_list, list):
					continue

				for alpha in alphas_list:
					alpha_name = alpha.get("name")
					formula = alpha.get("formula")

					if not alpha_name or not formula:
						continue

					try:
						# Parse and evaluate formula using DSL parser (returns raw value, not bool)
						ast = parse_formula(formula)
						result = ast.evaluate(df_enriched)

						# Convert result to float (handle Series and scalar results)
						if isinstance(result, pd.Series):
							result = result.iloc[-1]  # Get latest value from Series
						if isinstance(result, (bool, int, float)):
							alphas_dict[alpha_name] = float(result)
						elif result is not None:
							alphas_dict[alpha_name] = float(result)
					except Exception:
						# Skip alphas that can't be calculated
						pass

		except Exception:
			pass

		return alphas_dict

	def _handle_indicators(self, parts):
		"""Handle data indicators command to show technical indicators."""
		if len(parts) < 2:
			console.print("[red]✗[/red] Usage: data indicators <ticker> [options] [ind1] [ind2]...")
			console.print("[yellow]Options:[/yellow]")
			console.print("  -offset N      Show indicators from N days ago")
			console.print("               0 = latest (default), -1 = previous day, -2 = 2 days ago, etc.")
			console.print("  \"YYYY-MM-DD\"   Show indicators for specific date (e.g., \"2026-05-21\")")
			console.print("[yellow]Examples:[/yellow]")
			console.print("  cresus data indicators SU.PA")
			console.print("  cresus data indicators SU.PA -offset -1 sha_10_green sha_10_red")
			console.print("  cresus data indicators SU.PA \"2026-05-21\"")
			console.print("[yellow]Note:[/yellow] If no indicators specified, shows all default indicators")
			return

		ticker = parts[1]

		# Parse options and indicators
		offset = None
		target_date = None
		indicator_args = []

		i = 2
		while i < len(parts):
			arg = parts[i]
			if arg == "-offset" and i + 1 < len(parts):
				try:
					offset = int(parts[i + 1])
					i += 2
					continue
				except ValueError:
					console.print(f"[red]✗[/red] Invalid offset value: {parts[i + 1]}")
					return

			# Check if it's a date string (YYYY-MM-DD format, with or without quotes)
			date_candidate = arg.strip('\'"')
			if len(date_candidate) == 10 and date_candidate.count('-') == 2:
				# Validate it's a proper date
				try:
					from datetime import datetime
					datetime.strptime(date_candidate, '%Y-%m-%d')
					target_date = date_candidate
					i += 1
					continue
				except ValueError:
					pass

			# It's an indicator name
			indicator_args.append(arg)
			i += 1

		requested_indicators = indicator_args if indicator_args else DEFAULT_INDICATORS

		try:
			# Try to load from cache
			from pathlib import Path
			cresus_home = Path.home() / ".cresus"

			# Try parquet first (cached)
			parquet_file = cresus_home / "db" / "cache" / "history" / f"{ticker}.parquet"
			if parquet_file.exists():
				df = pd.read_parquet(parquet_file)
			else:
				# Fall back to fetching if not cached
				result = self.data_manager.fetch_history(ticker)
				if result.get("status") != "success":
					console.print(f"[red]✗[/red] {result.get('message')}")
					return

				# Try again after fetch
				if parquet_file.exists():
					df = pd.read_parquet(parquet_file)
				else:
					console.print(f"[red]✗[/red] Data file not found: {parquet_file}")
					return

			if df.empty:
				console.print(f"[red]✗[/red] No data available for {ticker}")
				return

			# Calculate indicators
			from tools.indicators.indicators import calculate

			# Convert column names to lowercase for indicator engine
			df_lower = df.copy()
			df_lower.columns = [col.lower() for col in df_lower.columns]

			# Calculate all requested indicators
			try:
				indicators_result = calculate(requested_indicators, df_lower)
			except Exception as e:
				console.print(f"[yellow]⚠[/yellow] Error calculating indicators: {e}")
				console.print("[dim]Some indicators may not be available. Use 'data indicators' without args to see defaults.[/dim]")
				return

			# Add calculated indicators to the dataframe
			for ind_name, ind_series in indicators_result.items():
				df[ind_name] = ind_series.values

			# Calculate alphas if no specific indicators requested (show all)
			alphas_to_show = {}
			if not indicator_args:
				try:
					# Get all indicator names needed for alphas from template
					import yaml
					from pathlib import Path
					template_path = Path(__file__).parent.parent.parent.parent / "init" / "templates" / "strategy.yml"
					with open(template_path) as f:
						template = yaml.safe_load(f)

					# Extract all indicator names from template
					all_indicators_in_template = template.get("indicators", [])

					# Calculate any missing indicators
					missing_indicators = [ind for ind in all_indicators_in_template if ind not in indicators_result]
					if missing_indicators:
						try:
							extra_indicators = calculate(missing_indicators, df_lower)
							indicators_result.update(extra_indicators)
							for ind_name, ind_series in extra_indicators.items():
								df[ind_name] = ind_series.values
						except Exception:
							pass  # Some indicators may not be available

					alphas_to_show = self._calculate_alphas(df, requested_indicators, indicators_result)
				except Exception as e:
					console.print(f"[dim]Note: Could not calculate alphas: {e}[/dim]")

			# Display the requested values in a table
			self._display_indicators_table(ticker, df, requested_indicators, alphas=alphas_to_show, offset=offset, target_date=target_date)

		except Exception as e:
			console.print(f"[red]✗[/red] Error: {e}")
			import traceback
			console.print(f"[dim]{traceback.format_exc()}[/dim]")

	def _display_indicators_table(self, ticker: str, df: pd.DataFrame, indicators: list, alphas: dict = None, offset: int = None, target_date: str = None):
		"""Display indicators and alphas in a formatted table."""
		if alphas is None:
			alphas = {}
		if df.empty:
			console.print(f"[yellow]⚠[/yellow] No data available")
			return

		# Determine which row to display
		if target_date:
			# Find row by specific date
			date_col = None
			for col in ['Date', 'date', 'timestamp', 'Timestamp']:
				if col in df.columns:
					date_col = col
					break

			if date_col is None:
				console.print(f"[red]✗[/red] No date column found in data")
				return

			# Convert target_date to pandas Timestamp for comparison
			import pandas as pd_timestamp
			target = pd_timestamp.to_datetime(target_date).date()

			# Find matching row
			matching_rows = []
			for idx, row in df.iterrows():
				row_date = row[date_col]
				if hasattr(row_date, 'date'):
					row_date = row_date.date()
				else:
					row_date = pd_timestamp.to_datetime(row_date).date()

				if row_date == target:
					matching_rows.append(idx)

			if not matching_rows:
				console.print(f"[red]✗[/red] No data available for date: {target_date}")
				return

			# Use the last matching row (in case there are duplicates)
			row_idx = matching_rows[-1]
			latest = df.iloc[row_idx]
			date_str = target_date

		elif offset is not None:
			# Use offset from the end
			# offset 0 or no offset = latest (df.iloc[-1])
			# offset -1 = 1 day ago (df.iloc[-2])
			# offset -2 = 2 days ago (df.iloc[-3]), etc.
			# offset 1 = 1 day ahead (df.iloc[0] - oldest), etc. (rarely used)
			if offset == 0:
				idx = -1  # Latest
			elif offset < 0:
				idx = offset - 1  # Convert -1 to -2, -2 to -3, etc.
			else:
				idx = offset  # Positive offset counts from beginning

			if abs(idx) > len(df):
				console.print(f"[red]✗[/red] Offset {offset} out of range (data has {len(df)} rows)")
				return

			latest = df.iloc[idx]

			# Get the date from the dataframe
			date_val = None
			for col in ['Date', 'date', 'timestamp', 'Timestamp']:
				if col in df.columns:
					date_val = latest[col]
					break

			if date_val is not None:
				if hasattr(date_val, 'strftime'):
					date_str = date_val.strftime('%Y-%m-%d')
				else:
					date_str = str(date_val).split(' ')[0]
			else:
				date_str = f"Row {offset}"

		else:
			# Get the latest row (default behavior)
			latest = df.iloc[-1]

			# Get the date from the dataframe (try different column names)
			date_val = None
			for col in ['Date', 'date', 'timestamp', 'Timestamp']:
				if col in df.columns:
					date_val = latest[col]
					break

			if date_val is not None:
				# Format the date nicely
				if hasattr(date_val, 'strftime'):
					date_str = date_val.strftime('%Y-%m-%d')
				else:
					date_str = str(date_val).split(' ')[0]  # Extract just the date part if it's a timestamp
			else:
				date_str = "N/A"

		# Create two columns: Indicator and Value
		table = Table(title=f"Indicators for {ticker} ({date_str})", box=box.ROUNDED)
		table.add_column("Indicator", style="cyan")
		table.add_column("Value", justify="right")

		# Add OHLCV values first
		ohlcv_fields = ['Open', 'High', 'Low', 'Close', 'Volume']
		ohlcv_cols = {}
		for col in df.columns:
			if col.lower() in [f.lower() for f in ohlcv_fields]:
				ohlcv_cols[col.lower()] = col

		# Display OHLCV in standard order
		for field in ['open', 'high', 'low', 'close', 'volume']:
			if field in ohlcv_cols:
				col_name = ohlcv_cols[field]
				if col_name in df.columns:
					value = latest[col_name]
					if pd.isna(value):
						formatted = "[yellow]N/A[/yellow]"
					elif field == 'volume':
						formatted = f"{int(value):,}"
					else:
						formatted = f"{float(value):.2f}"
					table.add_row(f"[bold]{field.upper()}[/bold]", formatted)

		# Add separator
		if ohlcv_cols:
			table.add_row("[dim]─────────────────────────[/dim]", "[dim]─────────────────────────[/dim]")

		# Add each indicator to the table
		for ind in indicators:
			if ind in df.columns:
				value = latest[ind]
				# Format the value nicely
				if pd.isna(value):
					formatted = "[yellow]N/A[/yellow]"
				elif isinstance(value, (int, float)):
					if abs(value) >= 100 or ind.startswith("vol") or ind.startswith("atr"):
						formatted = f"{value:.2f}"
					elif ind.startswith("rsi") or ind.startswith("adx"):
						formatted = f"{value:.2f}"
					elif ind.endswith("_up") or ind.endswith("_down") or ind.endswith("_red") or ind.endswith("_green"):
						formatted = f"{int(value)}"
					else:
						formatted = f"{value:.4f}"
				else:
					formatted = str(value)

				table.add_row(ind, formatted)
			else:
				table.add_row(ind, "[red]N/A[/red]")

		# Add alphas if available
		if alphas:
			# Keywords that indicate boolean/condition alphas
			boolean_keywords = ('touch', 'breakout', 'confirmation', 'absorption', 'cluster', 'climax',
							   'reversal', 'squeeze', 'expansion', 'signal', 'overbought', 'oversold',
							   'contraction', 'single_print', 'above', 'below', 'uptrend')

			for alpha_name, alpha_value in sorted(alphas.items()):
				# Check if this is a boolean/condition alpha
				is_boolean_alpha = any(keyword in alpha_name for keyword in boolean_keywords)

				if isinstance(alpha_value, (int, float)):
					if is_boolean_alpha:
						# Boolean alphas: show as 1/0 or label them
						if alpha_value in (0.0, 1.0):
							formatted = f"{int(alpha_value)}"
						else:
							formatted = f"{alpha_value:.4f}"
					elif abs(alpha_value) >= 100 or alpha_name.startswith("vol"):
						formatted = f"{alpha_value:.2f}"
					elif alpha_name.startswith("rsi") or alpha_name.startswith("adx") or alpha_name.startswith("bb"):
						formatted = f"{alpha_value:.4f}"
					else:
						formatted = f"{alpha_value:.4f}"
				else:
					formatted = str(alpha_value)

				# Use different styling for boolean alphas
				if is_boolean_alpha:
					table.add_row(f"[yellow]{alpha_name}[/yellow]", f"{formatted}")
				else:
					table.add_row(f"[dim]{alpha_name}[/dim]", f"[dim]{formatted}[/dim]")

		console.print(table)

		# Count boolean vs numeric alphas
		boolean_keywords = ('touch', 'breakout', 'confirmation', 'absorption', 'cluster', 'climax',
						   'reversal', 'squeeze', 'expansion', 'signal', 'overbought', 'oversold',
						   'contraction', 'single_print', 'above', 'below', 'uptrend')
		boolean_count = sum(1 for name in alphas.keys() if any(keyword in name for keyword in boolean_keywords))
		numeric_count = len(alphas) - boolean_count

		console.print(f"\n[dim]Total: {len(df.columns)} columns, {len(df)} rows[/dim]")
		console.print(f"[dim]Alphas: {len(alphas)} total ({numeric_count} numeric + {boolean_count} boolean conditions)[/dim]")
		console.print("[yellow]●[/yellow] [yellow]Boolean alphas[/yellow] show 1=True/0=False (conditions for entry/exit)")

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

		table = Table(title=f"Data Fetch Results: {result.get('universe') or result.get('ticker')}", box=box.ROUNDED)
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
