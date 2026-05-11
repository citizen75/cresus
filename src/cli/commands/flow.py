"""Flow management and execution for CLI."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add src to path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from flows.watchlist import WatchlistFlow
from flows.signals import SignalsFlow
from flows.premarket import PreMarketFlow
from flows.transact import TransactFlow
from flows.backtest import BacktestFlow
from flows.portfolio_analysis import PortfolioAnalysisFlow
from tools.strategy.strategy import StrategyManager
from tools.universe.universe import Universe


class FlowManager:
	"""Manager for executing workflow flows."""

	def __init__(self, project_root: Path):
		"""Initialize flow manager.

		Args:
			project_root: Root directory of the project
		"""
		self.project_root = project_root
		self.strategy_manager = StrategyManager(project_root)

	def run_workflow(self, workflow_name: str, strategy: str = "default", input_data: Optional[Dict[str, Any]] = None, include_context: bool = False, debug: bool = False, use_backtest: bool = False, show_metrics: bool = False) -> Dict[str, Any]:
		"""Run a workflow.

		Args:
			workflow_name: Name of the workflow to run (e.g., 'watchlist', 'signals')
			strategy: Strategy name for the workflow
			input_data: Optional input data for the workflow
			include_context: Whether to include flow context in result
			debug: Enable debug logging
			use_backtest: Use backtest mode
			show_metrics: Display agent execution metrics table

		Returns:
			Workflow result dictionary
		"""
		# Import here to avoid circular imports
		from core.logger import enable_debug_mode, disable_debug_mode
		
		# Enable debug mode if requested
		if debug:
			enable_debug_mode()
		
		# Auto-enable include_context if metrics are requested
		if show_metrics:
			include_context = True
		
		try:
			if workflow_name.lower() == "signals":
				# Signals flow - generate trading signals
				flow = SignalsFlow(strategy)
				result = flow.process(input_data or {})

				# Include context if requested
				if include_context:
					result["_context"] = {
						key: value for key, value in flow.context.__dict__.items()
						if not key.startswith("_") and key != "logger"
					}

				return result

			elif workflow_name.lower() == "watchlist":
				# Try to get tickers from input_data or strategy config
				tickers = None

				if input_data and input_data.get("tickers"):
					tickers = input_data["tickers"]
				else:
					# Try to load strategy and extract tickers from universe
					strategy_result = self.strategy_manager.load_strategy(strategy)

					if strategy_result.get("status") != "success":
						return {
							"status": "error",
							"message": f"Strategy '{strategy}' not found. Provide tickers: flow run watchlist {strategy} AAPL GOOGL MSFT"
						}

					# Get universe from strategy
					universe_name = strategy_result.get("source")
					if not universe_name:
						return {
							"status": "error",
							"message": f"Strategy '{strategy}' does not specify a universe or source"
						}

					try:
						universe = Universe(universe_name)
						if not universe.exists():
							return {
								"status": "error",
								"message": f"Universe '{universe_name}' not found"
							}
						tickers = universe.get_tickers()
						if not tickers:
							return {
								"status": "error",
								"message": f"Universe '{universe_name}' is empty"
							}
					except Exception as e:
						return {
							"status": "error",
							"message": f"Failed to load universe '{universe_name}': {str(e)}"
						}

				# Validate tickers
				if not tickers:
					return {
						"status": "error",
						"message": "No tickers found. Provide tickers: flow run watchlist my_strategy AAPL GOOGL MSFT"
					}

				# Prepare input data
				if input_data is None:
					input_data = {}
				input_data["tickers"] = tickers

				flow = WatchlistFlow(strategy)
				result = flow.process(input_data)

				# Include context if requested
				if include_context:
					result["_context"] = {
						key: value for key, value in flow.context.__dict__.items()
						if not key.startswith("_") and key != "logger"
					}

				return result

			elif workflow_name.lower() == "premarket":
				# Pre-market flow - watchlist generation + signal analysis
				flow = PreMarketFlow(strategy)
				result = flow.process(input_data or {})

				# Include context if requested
				if include_context:
					result["_context"] = {
						key: value for key, value in flow.context.__dict__.items()
						if not key.startswith("_") and key != "logger"
					}

				return result

			elif workflow_name.lower() == "transact":
				# Transaction flow - execute pending orders on a date
				# Default to today if no date provided
				from datetime import date

				flow_input = input_data or {}
				if "date" not in flow_input or not flow_input["date"]:
					flow_input["date"] = date.today().isoformat()

				# Use strategy as portfolio name if provided
				if strategy and strategy != "default":
					flow_input["portfolio_name"] = strategy

				flow = TransactFlow()
				result = flow.process(flow_input)

				# Include context if requested
				if include_context:
					result["_context"] = {
						key: value for key, value in flow.context.__dict__.items()
						if not key.startswith("_") and key != "logger"
					}

				return result

			elif workflow_name.lower() == "backtest":
				# Backtest flow - simulate strategy over a date range
				flow_input = input_data or {}
				flow_input["strategy"] = strategy if strategy and strategy != "default" else flow_input.get("strategy")

				if not flow_input.get("strategy"):
					return {
						"status": "error",
						"message": "strategy parameter required for backtest"
					}

				flow = BacktestFlow()
				result = flow.process(flow_input)

				# Include context if requested
				if include_context:
					result["_context"] = {
						key: value for key, value in flow.context.__dict__.items()
						if not key.startswith("_") and key != "logger"
					}

				return result

			elif workflow_name.lower() == "portfolio_analysis":
				# Portfolio analysis flow - analyze portfolio journal and identify issues
				# Can analyze live portfolio or most recent backtest
				portfolio_name = strategy if strategy and strategy != "default" else "default"

				flow = PortfolioAnalysisFlow(portfolio_name, use_backtest=use_backtest)
				flow_input = input_data or {}
				flow_input["use_backtest"] = use_backtest
				result = flow.process(flow_input)

				# Include context if requested
				if include_context:
					result["_context"] = {
						key: value for key, value in flow.context.__dict__.items()
						if not key.startswith("_") and key != "logger"
					}

				return result

			elif workflow_name.lower() == "market_regime":
				# Market regime detection flow - train or predict regimes
				from flows.market_regime import MarketRegimeFlow

				flow_input = input_data or {}

				# universe is required
				if not flow_input.get("universe"):
					return {
						"status": "error",
						"message": "universe parameter required for market_regime (e.g. 'etf_pea')"
					}

				flow = MarketRegimeFlow()
				result = flow.process(flow_input)

				# Include context if requested
				if include_context:
					result["_context"] = {
						key: value for key, value in flow.context.__dict__.items()
						if not key.startswith("_") and key != "logger"
					}

				return result

			else:
				return {
					"status": "error",
					"message": f"Unknown workflow: {workflow_name}",
					"available": ["signals", "watchlist", "premarket", "transact", "backtest", "portfolio_analysis", "market_regime"]
				}
		finally:
			# Always disable debug mode after workflow completes
			if debug:
				disable_debug_mode()

	def list_workflows(self) -> Dict[str, Any]:
		"""List available workflows.

		Returns:
			Dictionary with available workflows
		"""
		return {
			"status": "success",
			"workflows": [
				{
					"name": "signals",
					"description": "Trading signal generation from strategy indicators",
					"parameters": ["strategy"]
				},
				{
					"name": "watchlist",
					"description": "Stock watchlist generation using strategy analysis",
					"parameters": ["strategy", "tickers"]
				},
				{
					"name": "premarket",
					"description": "Pre-market analysis: watchlist generation + signal analysis",
					"parameters": ["strategy"]
				},
				{
					"name": "transact",
					"description": "Execute pending orders on a specific trading date",
					"parameters": ["date", "portfolio_name"]
				},
				{
					"name": "backtest",
					"description": "Backtest strategy over a date range (pre-market → transact daily)",
					"parameters": ["strategy", "start_date", "end_date"]
				},
				{
					"name": "portfolio_analysis",
					"description": "Analyze portfolio journal and identify trading issues",
					"parameters": ["portfolio_name"]
				},
				{
					"name": "market_regime",
					"description": "Train or predict market regime using LightGBM (6 regime classes)",
					"parameters": ["universe", "action", "lookback_days", "session_date"]
				}
			]
		}

	def _print_workflows_result(self, result):
		"""Print list of available workflows."""
		from rich.console import Console
		from rich.table import Table
		from rich import box

		console = Console()

		if result.get("status") == "error":
			console.print(f"[red]✗[/red] {result.get('message')}")
			return

		table = Table(title="Available Workflows", box=box.ROUNDED)
		table.add_column("Workflow", style="cyan")
		table.add_column("Description")
		table.add_column("Parameters", style="yellow")

		for workflow in result.get("workflows", []):
			table.add_row(
				workflow["name"],
				workflow["description"],
				", ".join(workflow["parameters"])
			)

		console.print(table)

	def _print_flow_result(self, result, workflow_name=None):
		"""Print flow execution result."""
		from rich.console import Console
		from rich.panel import Panel
		from rich.text import Text

		console = Console()

		if result.get("status") == "error":
			console.print(f"\n[red]✗ Flow failed:[/red] {result.get('message')}")
			return

		console.print(f"\n[green]✓ Flow completed successfully[/green]")

		# Special handling for specific workflows
		if workflow_name:
			if workflow_name.lower() == "portfolio_analysis":
				self._print_portfolio_analysis_result(result, console)
				return
			elif workflow_name.lower() == "market_regime":
				self._print_market_regime_result(result, console)
				return
			elif workflow_name.lower() == "premarket":
				self._print_premarket_result(result, console)
				return
			elif workflow_name.lower() == "backtest":
				# Backtest results are printed separately in app.py, skip summary here
				return

		# Print summary for other workflows
		output = result.get("output", {})
		if output:
			console.print("\n[cyan]Summary:[/cyan]")
			for key, value in output.items():
				if isinstance(value, dict):
					console.print(f"  {key}:")
					for k, v in value.items():
						console.print(f"    {k}: {v}")
				else:
					console.print(f"  {key}: {value}")

	def _print_portfolio_analysis_result(self, result, console):
		"""Print portfolio analysis flow result."""
		from rich.table import Table

		if result.get("status") != "success":
			return

		portfolio = result.get("portfolio_name", "unknown")
		mode = result.get("analysis_mode", "live")
		research = result.get("research_analysis", {})
		issues = result.get("issues", [])
		severity = result.get("severity", "none")
		metrics = result.get("portfolio_metrics", {})

		journal = research.get("journal_analysis", {})
		orders = research.get("order_analysis", {})

		# Header
		console.print(f"\n[bold]Portfolio Analysis[/bold] - [cyan]{mode.upper()} MODE[/cyan]")
		console.print("=" * 100)

		# Portfolio Metrics (if available)
		if metrics:
			console.print("\n[bold cyan]📊 Portfolio Metrics[/bold cyan]")
			console.print("-" * 100)

			# Simple text format for metrics (like backtest output)
			start = metrics.get("start_date", "N/A")
			end = metrics.get("end_date", "N/A")
			period = metrics.get("period_days", 0)

			start_val = metrics.get("start_value", 0)
			end_val = metrics.get("end_value", 0)
			total_return = metrics.get("total_return_pct", 0)
			bench_return = metrics.get("benchmark_return_pct", 0)
			max_exposure = metrics.get("max_gross_exposure_pct", 0)
			fees = metrics.get("total_fees", 0)

			max_dd = metrics.get("max_drawdown_pct", 0)
			max_dd_days = metrics.get("max_drawdown_duration_days", 0)

			total_trades = metrics.get("total_trades", 0)
			closed_trades = metrics.get("closed_trades", 0)
			open_trades = metrics.get("open_trades", 0)
			open_pnl = metrics.get("open_trade_pnl", 0)

			win_rate = metrics.get("win_rate_pct", 0)
			best_trade = metrics.get("best_trade_pct", 0)
			worst_trade = metrics.get("worst_trade_pct", 0)
			avg_win = metrics.get("avg_winning_trade_pct", 0)
			avg_loss = metrics.get("avg_losing_trade_pct", 0)

			avg_win_days = metrics.get("avg_winning_trade_duration_days", 0)
			avg_loss_days = metrics.get("avg_losing_trade_duration_days", 0)

			profit_factor = metrics.get("profit_factor", 0)
			expectancy = metrics.get("expectancy_pct", 0)
			sharpe = metrics.get("sharpe_ratio", 0)
			calmar = metrics.get("calmar_ratio", 0)
			omega = metrics.get("omega_ratio", 0)
			sortino = metrics.get("sortino_ratio", 0)

			# Format like backtest output
			metrics_text = f"""Start                                {start}
End                                  {end}
Period                                          {period} days

Start Value                                     ${start_val:,.2f}
End Value                                       ${end_val:,.2f}
Total Return                                      {total_return:.2f} %
Benchmark Return                                    {bench_return:.2f} %
Max Gross Exposure                                 {max_exposure:.2f} %
Total Fees Paid                                    ${fees:,.2f}

Max Drawdown                                       {max_dd:.2f} %
Max Drawdown Duration                            {max_dd_days} days

Total Trades                                         {total_trades}
Closed Trades                                        {closed_trades}
Open Trades                                            {open_trades}
Open Trade PnL                                     ${open_pnl:,.2f}

Win Rate                                           {win_rate:.2f} %
Best Trade                                         {best_trade:.2f} %
Worst Trade                                       {worst_trade:.2f} %
Avg Winning Trade                                   {avg_win:.2f} %
Avg Losing Trade                                   {avg_loss:.2f} %

Avg Winning Trade Duration                     {avg_win_days:.1f} days
Avg Losing Trade Duration                       {avg_loss_days:.1f} days

Profit Factor                                   {profit_factor:.6f}
Expectancy                                     {expectancy:.6f} %
Sharpe Ratio                                   {sharpe:.6f}
Calmar Ratio                                   {calmar:.6f}
Omega Ratio                                     {omega:.6f}
Sortino Ratio                                  {sortino:.6f}"""

			console.print(metrics_text)

		# Issues detail
		if issues:
			console.print(f"\n[yellow]⚠️  Identified Issues ({len(issues)})[/yellow]")
			console.print("-" * 100)
			for i, issue in enumerate(issues, 1):
				console.print(f"\n{i}. [bold]{issue['message']}[/bold]")
				console.print(f"   Type: {issue['type']}")
				console.print(f"   Category: {issue['category']}")
				console.print(f"   Severity: [yellow]{issue['severity'].upper()}[/yellow]")
				console.print(f"   Details: {issue['details']}")
		else:
			console.print(f"\n[green]✓ No issues found![/green]")

		# Journal Analytics - Exit Type Analysis
		if journal:
			exit_analysis = journal.get("exit_analysis", {})
			if exit_analysis and exit_analysis.get("total_exits", 0) > 0:
				console.print(f"\n[bold cyan]📊 Trade Exit Analysis[/bold cyan]")
				console.print("-" * 100)
				
				total_exits = exit_analysis.get("total_exits", 0)
				exit_types = exit_analysis.get("exit_types", {})
				
				console.print(f"\n[bold]Total Exits: {total_exits}[/bold]")
				console.print()
				
				# Display each exit type
				exit_type_info = [
					("Target Hit", exit_types.get("target_hit", {}), "green"),
					("Stop Loss", exit_types.get("stop_loss", {}), "red"),
					("Expired", exit_types.get("expired", {}), "yellow"),
					("Other", exit_types.get("other", {}), "white"),
				]
				
				for label, info, color in exit_type_info:
					count = info.get("count", 0)
					pct = info.get("pct", 0.0)
					console.print(f"[{color}]  {label:15} {count:3d} exits ({pct:5.1f}%)[/{color}]")

		# Orders Analytics data
		orders_analysis = research.get("orders_analysis", {})
		if orders_analysis:
			console.print(f"\n[bold cyan]📋 Orders Analytics[/bold cyan]")
			console.print("-" * 100)

			total_orders = orders_analysis.get("total_orders", 0)
			buy_orders = orders_analysis.get("buy_orders", 0)
			sell_orders = orders_analysis.get("sell_orders", 0)
			buy_sell_ratio = orders_analysis.get("buy_sell_ratio", 0)

			sizing = orders_analysis.get("sizing_analysis", {})
			timing = orders_analysis.get("timing_analysis", {})
			balance = orders_analysis.get("order_balance", {})
			tickers = orders_analysis.get("ticker_analysis", {})
			prices = orders_analysis.get("price_analysis", {})
			daily = orders_analysis.get("daily_activity", {})

			console.print(f"\n[bold]Order Summary[/bold]")
			console.print(f"Total Orders:                   {total_orders}")
			console.print(f"Buy Orders:                     {buy_orders}")
			console.print(f"Sell Orders:                    {sell_orders}")
			console.print(f"Buy/Sell Ratio:                 {buy_sell_ratio:.2f}x")

			console.print(f"\n[bold]Position Sizing[/bold]")
			console.print(f"Avg Buy Size:                   {sizing.get('avg_buy_size', 0):.2f} shares")
			console.print(f"Avg Sell Size:                  {sizing.get('avg_sell_size', 0):.2f} shares")
			console.print(f"Min Size:                       {sizing.get('min_size', 0):.2f} shares")
			console.print(f"Max Size:                       {sizing.get('max_size', 0):.2f} shares")
			consistency = sizing.get('size_consistency_pct', 0)
			consistency_color = "red" if consistency < 50 else "yellow" if consistency < 75 else "green"
			console.print(f"[{consistency_color}]Size Consistency:              {consistency:.1f}%[/{consistency_color}]")

			console.print(f"\n[bold]Order Timing[/bold]")
			console.print(f"Avg Orders Per Day:             {timing.get('avg_orders_per_day', 0):.1f}")
			console.print(f"Max Orders Per Day:             {timing.get('max_orders_per_day', 0)}")
			console.print(f"Min Orders Per Day:             {timing.get('min_orders_per_day', 0)}")
			console.print(f"Peak Hour:                      {timing.get('peak_hour', 'N/A')} (24h format)")

			console.print(f"\n[bold]Order Balance[/bold]")
			console.print(f"Total Buy Quantity:             {balance.get('total_buy_quantity', 0):.0f} shares")
			console.print(f"Total Sell Quantity:            {balance.get('total_sell_quantity', 0):.0f} shares")
			imbalance = balance.get('imbalance_ratio', 0)
			imbalance_color = "green" if 0.8 <= imbalance <= 1.5 else "yellow"
			console.print(f"[{imbalance_color}]Imbalance Ratio:               {imbalance:.2f}x[/{imbalance_color}]")

			console.print(f"\n[bold]Ticker Concentration[/bold]")
			console.print(f"Total Tickers:                  {tickers.get('total_tickers', 0)}")
			most_active = tickers.get('most_active', [])[:3]
			if most_active:
				console.print(f"Most Active:")
				for ticker in most_active:
					ticker_stats = tickers.get('stats', {}).get(ticker, {})
					console.print(f"  • {ticker}: {ticker_stats.get('total_orders', 0)} orders")

			console.print(f"\n[bold]Price Quality[/bold]")
			console.print(f"Avg Buy Price:                  €{prices.get('avg_buy_price', 0):.2f}")
			console.print(f"Avg Sell Price:                 €{prices.get('avg_sell_price', 0):.2f}")
			console.print(f"Zero Price Orders:              {prices.get('zero_price_orders', 0)}")

			# Same-day buy/sell analysis
			sameday = orders_analysis.get("sameday_buynsell", {})
			pairs_found = sameday.get("pairs_found", 0)
			if pairs_found > 0:
				console.print(f"\n[bold]Same-Day Buy/Sell Activity[/bold]")
				console.print(f"Days with Buy+Sell:             {pairs_found}")

				pairs = sameday.get("pairs", [])
				if pairs:
					console.print(f"\n[bold cyan]Same-Day Pairs:[/bold cyan]")
					for pair in pairs:
						ticker = pair.get("ticker", "N/A")
						date = pair.get("date", "N/A")
						buy_cnt = pair.get("buy_orders", 0)
						sell_cnt = pair.get("sell_orders", 0)
						buy_qty = pair.get("buy_quantity", 0)
						sell_qty = pair.get("sell_quantity", 0)
						avg_buy = pair.get("avg_buy_price", 0)
						avg_sell = pair.get("avg_sell_price", 0)
						pnl_per = pair.get("pnl_per_share", 0)
						total_pnl = pair.get("total_pnl", 0)

						pnl_color = "green" if total_pnl > 0 else "red"
						console.print(f"\n  {ticker} on {date}")
						console.print(f"    Buys: {buy_cnt} orders ({buy_qty:.0f} shares @ €{avg_buy:.2f})")
						console.print(f"    Sells: {sell_cnt} orders ({sell_qty:.0f} shares @ €{avg_sell:.2f})")
						console.print(f"    [{pnl_color}]P&L per share: €{pnl_per:.4f} | Total P&L: €{total_pnl:.2f}[/{pnl_color}]")

		# Recommendations from stats analysis and orders analysis
		recommendations = result.get("research_analysis", {}).get("recommendations", [])
		if recommendations:
			console.print(f"\n[cyan]💡 Recommendations ({len(recommendations)})[/cyan]")
			console.print("-" * 100)

			# Separate by category
			perf_recs = [r for r in recommendations if r.get("category") in ["returns", "risk_adjusted_returns", "risk_management", "signal_quality", "position_management", "strategy_tuning"]]
			order_recs = [r for r in recommendations if r.get("category") in ["position_sizing", "order_frequency", "signal_consistency", "portfolio_concentration", "order_type", "pricing"]]

			# Display performance recommendations
			if perf_recs:
				console.print(f"\n[bold cyan]📊 Performance Recommendations[/bold cyan]")
				self._display_recommendations_by_priority(perf_recs, console)

			# Display orders recommendations
			if order_recs:
				console.print(f"\n[bold cyan]📋 Order Execution Recommendations[/bold cyan]")
				self._display_recommendations_by_priority(order_recs, console)

	def _display_recommendations_by_priority(self, recommendations, console):
		"""Display recommendations grouped by priority.

		Args:
			recommendations: List of recommendation dicts
			console: Rich console object
		"""
		by_priority = {"critical": [], "high": [], "medium": [], "low": []}
		for rec in recommendations:
			priority = rec.get("priority", "low")
			if priority not in by_priority:
				by_priority[priority] = []
			by_priority[priority].append(rec)

		# Display by priority
		for priority in ["critical", "high", "medium", "low"]:
			recs = by_priority[priority]
			if not recs:
				continue

			color = {"critical": "red", "high": "yellow", "medium": "cyan", "low": "white"}[priority]
			console.print(f"\n[{color}]{priority.upper()} PRIORITY[/{color}]")

			for j, rec in enumerate(recs, 1):
				console.print(f"\n  {j}. [bold]{rec.get('title')}[/bold] ({rec.get('category')})")
				console.print(f"     {rec.get('description')}")
				console.print(f"     → {rec.get('recommendation')}")

	def _print_market_regime_result(self, result, console):
		"""Print market regime flow result."""
		from rich.table import Table

		if result.get("status") != "success":
			return

		output = result.get("output", {})
		action = output.get("action", "unknown")

		console.print(f"\n[bold cyan]🎯 Market Regime Detection[/bold cyan]")
		console.print("=" * 100)

		if action == "train":
			self._print_train_result(output, console)
		elif action == "predict":
			self._print_predict_result(output, console)

	def _print_train_result(self, output, console):
		"""Print training results."""
		from rich.table import Table

		universe = output.get("universe")
		model_path = output.get("model_path")
		training = output.get("training", {})
		metrics = output.get("metrics", {})
		top_features = output.get("top_features", [])
		regime_dist = output.get("regime_distribution", {})

		console.print(f"\n[bold]Training Summary[/bold]")
		console.print(f"Universe:                          {universe}")
		console.print(f"Model Path:                        {model_path}")

		# Training data
		console.print(f"\n[bold]Training Data[/bold]")
		n_train = training.get("n_samples_train", 0)
		n_test = training.get("n_samples_test", 0)
		n_features = training.get("n_features", 0)
		date_range = training.get("date_range", {})

		console.print(f"Training Samples:                  {n_train}")
		console.print(f"Test Samples:                      {n_test}")
		console.print(f"Features:                          {n_features}")
		if date_range:
			console.print(f"Date Range:                        {date_range.get('start')} to {date_range.get('end')}")

		# Metrics
		console.print(f"\n[bold]Performance Metrics[/bold]")
		accuracy = metrics.get("accuracy", 0)
		f1_macro = metrics.get("f1_macro", 0)
		f1_weighted = metrics.get("f1_weighted", 0)

		console.print(f"Accuracy:                          {accuracy:.4f}")
		console.print(f"F1 Score (Macro):                  {f1_macro:.4f}")
		console.print(f"F1 Score (Weighted):               {f1_weighted:.4f}")

		# Per-class metrics
		per_class = metrics.get("per_class_f1", {})
		if per_class:
			console.print(f"\n[bold]Per-Class F1 Scores[/bold]")
			for regime, f1 in per_class.items():
				console.print(f"  {regime:<30} {f1:.4f}")

		# Feature importance
		if top_features:
			console.print(f"\n[bold]Top 5 Features by Importance[/bold]")
			table = Table(box=None)
			table.add_column("Feature", style="cyan")
			table.add_column("Importance", style="green")

			for feature in top_features:
				name = feature.get("name", "unknown")
				importance = feature.get("importance", 0)
				table.add_row(name, f"{importance:.6f}")

			console.print(table)

		# Regime distribution
		if regime_dist:
			console.print(f"\n[bold]Regime Distribution (Training)[/bold]")
			table = Table(box=None)
			table.add_column("Regime", style="cyan")
			table.add_column("Count", style="green")

			for regime, count in sorted(regime_dist.items()):
				table.add_row(regime, str(count))

			console.print(table)

	def _print_predict_result(self, output, console):
		"""Print prediction results."""
		from rich.table import Table

		universe = output.get("universe")
		regime_id = output.get("regime_id")
		regime_name = output.get("regime_name")
		confidence = output.get("confidence", 0)
		probabilities = output.get("probabilities", {})
		model_path = output.get("model_path")
		session_date = output.get("session_date")

		console.print(f"\n[bold]Prediction Summary[/bold]")
		console.print(f"Universe:                          {universe}")
		console.print(f"Session Date:                      {session_date}")
		console.print(f"Model Path:                        {model_path}")

		# Current regime
		console.print(f"\n[bold cyan]Current Regime[/bold cyan]")
		color = "green" if "Bull" in regime_name else "red" if "Bear" in regime_name else "yellow"
		console.print(f"[{color}]{regime_name} (ID: {regime_id})[/{color}]")
		console.print(f"Confidence:                        {confidence:.2%}")

		# Probability distribution
		if probabilities:
			console.print(f"\n[bold]Regime Probabilities[/bold]")
			table = Table(box=None)
			table.add_column("Regime", style="cyan")
			table.add_column("Probability", style="green")

			for regime, prob in sorted(probabilities.items(), key=lambda x: x[1], reverse=True):
				prob_pct = f"{prob:.2%}"
				table.add_row(regime, prob_pct)

			console.print(table)

	def _print_premarket_result(self, result, console):
		"""Print pre-market flow result with watchlist and orders."""
		from rich.table import Table

		if result.get("status") != "success":
			return

		strategy = result.get("strategy", "unknown")
		watchlist = result.get("watchlist", [])
		ticker_scores = result.get("ticker_scores", {})
		executable_orders = result.get("executable_orders", [])
		orders_count = result.get("orders_count", 0)
		watchlist_saved = result.get("watchlist_saved", {})
		target_date = result.get("target_date")
		indicators = result.get("indicators", [])

		console.print(f"\n[bold cyan]📊 Pre-Market Analysis: {strategy}[/bold cyan]")
		console.print("=" * 100)

		# Watchlist section
		if watchlist:
			# Build watchlist header with date and indicators
			watchlist_header = f"Watchlist ({len(watchlist)} tickers)"
			if target_date:
				watchlist_header += f" - {target_date}"
			if indicators:
				indicators_str = ", ".join(indicators[:5])  # Show first 5 indicators
				if len(indicators) > 5:
					indicators_str += f" (+{len(indicators) - 5} more)"
				watchlist_header += f"\nIndicators: {indicators_str}"
			console.print(f"\n[bold]{watchlist_header}[/bold]")
			
			table = Table(box=None)
			table.add_column("Ticker", style="cyan")
			table.add_column("Score", style="green")
			table.add_column("Signals", style="yellow")

			for ticker in watchlist[:20]:  # Show top 20
				score_info = ticker_scores.get(ticker, {})
				score = score_info.get("score", 0)
				triggered_signals = score_info.get("triggered_signals", [])

				# Format signal names
				if triggered_signals:
					signals_str = ", ".join(triggered_signals)
				else:
					signals_str = "-"

				table.add_row(ticker, f"{score:.3f}", signals_str)

			console.print(table)

			if len(watchlist) > 20:
				console.print(f"[dim]... and {len(watchlist) - 20} more tickers[/dim]")

		# Orders section
		if executable_orders:
			console.print(f"\n[bold]Generated Orders ({orders_count} orders)[/bold]")
			table = Table(box=None)
			table.add_column("Ticker", style="cyan")
			table.add_column("Side", style="yellow")
			table.add_column("Shares", style="green")
			table.add_column("Entry", style="blue")
			table.add_column("Stop Loss", style="red")
			table.add_column("Take Profit", style="green")
			table.add_column("R:R", style="magenta")

			for order in executable_orders[:20]:  # Show top 20
				ticker = order.get("ticker", "")
				side = order.get("side", "BUY").upper()
				side_color = "green" if side == "BUY" else "red"
				shares = order.get("shares", 0)
				entry_price = order.get("entry_price", 0)
				stop_loss = order.get("stop_loss", 0)
				take_profit = order.get("take_profit", 0)
				risk_reward = order.get("risk_reward", 0)

				# Format stop loss and take profit
				stop_str = f"${stop_loss:.2f}" if stop_loss > 0 else "-"
				tp_str = f"${take_profit:.2f}" if take_profit > 0 else "-"
				rr_str = f"{risk_reward:.2f}x" if risk_reward > 0 else "-"

				table.add_row(
					ticker,
					f"[{side_color}]{side}[/{side_color}]",
					f"{shares:.0f}",
					f"${entry_price:.2f}",
					stop_str,
					tp_str,
					rr_str
				)

			console.print(table)

			if len(executable_orders) > 20:
				console.print(f"[dim]... and {len(executable_orders) - 20} more orders[/dim]")

		# Save status
		if watchlist_saved:
			saved_path = watchlist_saved.get("saved_path", "")
			if saved_path:
				console.print(f"\n[green]✓ Watchlist saved to:[/green] {saved_path}")

	def print_agent_metrics(self, context: Any) -> None:
		"""Print agent execution metrics as a formatted table, aggregated by agent name.
		
		Args:
			context: AgentContext or dict with metadata containing agent_metrics
		"""
		from rich.console import Console
		from rich.table import Table
		from collections import defaultdict
		
		console = Console()
		
		# Extract metrics from context
		metrics = None
		if hasattr(context, 'get_agent_metrics'):
			# AgentContext object
			metrics = context.get_agent_metrics()
		elif isinstance(context, dict):
			# Dict context
			metadata = context.get("metadata", {})
			metrics = metadata.get("agent_metrics", [])
		
		if not metrics:
			return
		
		# Aggregate metrics by agent name (track ticker counts too)
		agent_stats = defaultdict(lambda: {"count": 0, "total_ms": 0.0, "ticker_counts": []})
		for metric in metrics:
			name = metric["name"]
			duration = metric["duration_ms"]
			ticker_count = metric.get("ticker_count", None)
			agent_stats[name]["count"] += 1
			agent_stats[name]["total_ms"] += duration
			if ticker_count is not None:
				agent_stats[name]["ticker_counts"].append(ticker_count)
		
		# Calculate averages
		aggregated = []
		for name, stats in agent_stats.items():
			avg_ms = stats["total_ms"] / stats["count"]
			avg_tickers = None
			if stats["ticker_counts"]:
				avg_tickers = sum(stats["ticker_counts"]) / len(stats["ticker_counts"])
			aggregated.append({
				"name": name,
				"count": stats["count"],
				"avg_ms": avg_ms,
				"total_ms": stats["total_ms"],
				"avg_tickers": avg_tickers
			})
		
		# Sort by total duration descending
		aggregated.sort(key=lambda x: x["total_ms"], reverse=True)
		total_ms = sum(s["total_ms"] for s in aggregated)
		
		# Filter out metrics with negligible duration (< 1ms total or rounds to 0.0%)
		significant_aggregated = [
			s for s in aggregated
			if s["total_ms"] >= 1.0 or (s["total_ms"] / total_ms * 100 if total_ms > 0 else 0) >= 0.05
		]
		
		# Create table
		table = Table(title="Agent Execution Times (Aggregated)", box=None)
		table.add_column("Agent Name", style="cyan")
		table.add_column("Count", style="magenta", justify="right")
		table.add_column("Avg (ms)", style="green", justify="right")
		table.add_column("Total (ms)", style="blue", justify="right")
		table.add_column("Avg Tickers", style="white", justify="right")
		table.add_column("Percentage", style="yellow", justify="right")
		
		for stat in significant_aggregated:
			name = stat["name"]
			count = stat["count"]
			avg = stat["avg_ms"]
			total = stat["total_ms"]
			avg_tickers = stat["avg_tickers"]
			pct = (total / total_ms * 100) if total_ms > 0 else 0
			
			tickers_str = f"{avg_tickers:.0f}" if avg_tickers is not None else ""
			table.add_row(
				name,
				f"{count}",
				f"{avg:.2f}",
				f"{total:.2f}",
				tickers_str,
				f"{pct:.1f}%"
			)
		
		# Add total row
		table.add_row(
			"[bold]Total[/bold]",
			f"[bold]{len(metrics)}[/bold]",
			"",
			f"[bold]{total_ms:.2f}[/bold]",
			"",
			"[bold]100.0%[/bold]"
		)
		
		console.print("\n")
		console.print(table)
		console.print()
