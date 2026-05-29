"""Portfolio management command - refactored."""

from typing import Optional

from src.cli.base import BaseCommand, CommandResult, ValidationError
from src.cli.utils import ArgParser, Formatter, Validator


class PortfolioCommand(BaseCommand):
	"""Manage portfolio - view orders, watchlist, train ranking models.

	Subcommands:
		orders list <strategy>                  List orders for a strategy
		watchlist show <strategy>               Show watchlist for strategy
		watchlist extended <strategy>           Show detailed watchlist analysis
		watchlist train <strategy>              Train LGBM ranking model
		watchlist rank <strategy>               Rank tickers using trained model
	"""

	def __init__(self):
		"""Initialize portfolio command."""
		super().__init__()

	def handle(self, args: str) -> CommandResult:
		"""Handle portfolio command."""
		try:
			subcommand, subargs = ArgParser.extract_subcommand(args)

			if not subcommand:
				return self._cmd_help("")

			# Route to subcommand handlers
			if subcommand == "orders":
				return self._handle_orders(subargs)
			elif subcommand == "watchlist":
				return self._handle_watchlist(subargs)
			else:
				return self._error(f"Unknown portfolio subcommand: {subcommand}")

		except ValidationError as e:
			result = self._error(str(e), error_type="validation")
			self._print_result(result)
			return result
		except Exception as e:
			result = self._error(f"Unexpected error: {e}", error_type="error")
			self._print_result(result)
			return result

	def _handle_orders(self, args: str) -> CommandResult:
		"""Handle orders subcommand."""
		try:
			subcommand, subargs = ArgParser.extract_subcommand(args)

			if not subcommand:
				return self._error("Usage: portfolio orders list <strategy>", error_type="usage")

			if subcommand == "list":
				return self._cmd_orders_list(subargs)
			else:
				return self._error(f"Unknown orders subcommand: {subcommand}", error_type="usage")

		except ValidationError as e:
			return self._error(str(e), error_type="validation")

	def _handle_watchlist(self, args: str) -> CommandResult:
		"""Handle watchlist subcommand."""
		try:
			subcommand, subargs = ArgParser.extract_subcommand(args)

			if not subcommand:
				return self._error("Usage: portfolio watchlist <show|extended|train|rank> <strategy>", error_type="usage")

			cmd_map = {
				"show": self._cmd_watchlist_show,
				"extended": self._cmd_watchlist_extended,
				"train": self._cmd_watchlist_train,
				"rank": self._cmd_watchlist_rank,
			}

			if subcommand not in cmd_map:
				return self._error(f"Unknown watchlist subcommand: {subcommand}", error_type="usage")

			result = cmd_map[subcommand](subargs)
			self._print_result(result)
			return result

		except ValidationError as e:
			return self._error(str(e), error_type="validation")

	def _cmd_orders_list(self, args: str) -> CommandResult:
		"""List orders for a strategy."""
		try:
			parsed = ArgParser.parse_positional(args, ["strategy"])
			strategy = parsed["strategy"]
		except ValidationError as e:
			return self._error(f"Usage: portfolio orders list <strategy>\n{str(e)}", error_type="usage")

		try:
			from tools.portfolio.orders import Orders
			import pandas as pd

			portfolio_name = strategy.lower().replace(" ", "_")
			orders = Orders(portfolio_name)
			df = orders.get_all_orders()

			if df.empty:
				return self._success(f"No orders found for strategy '{strategy}'")

			# Build display data
			data = []
			df_sorted = df.sort_values("created_at", ascending=False, na_position="last")

			for _, row in df_sorted.iterrows():
				order_id = str(row.get("id", ""))[:8]
				created_at = str(row.get("created_at", ""))
				if "T" in created_at:
					created_at = created_at.split("T")[1][:8]

				data.append({
					"id": order_id,
					"created": created_at,
					"ticker": str(row.get("ticker", "")),
					"qty": str(int(float(row.get("quantity", 0)))) if pd.notna(row.get("quantity")) else "-",
					"entry": f"{float(row.get('entry_price', 0)):.2f}" if pd.notna(row.get("entry_price")) else "-",
					"stop": f"{float(row.get('stop_loss', 0)):.2f}" if pd.notna(row.get("stop_loss")) else "-",
					"target": f"{float(row.get('take_profit', 0)):.2f}" if pd.notna(row.get("take_profit")) else "-",
					"method": str(row.get("execution_method", "market")),
					"status": str(row.get("status", "pending")),
				})

			table = Formatter.table(
				data,
				title=f"Orders for {strategy}",
				columns={
					"id": "ID",
					"created": "Created",
					"ticker": "Ticker",
					"qty": "Qty",
					"entry": "Entry",
					"stop": "Stop",
					"target": "Target",
					"method": "Method",
					"status": "Status",
				}
			)
			self.console.print(table)

			# Summary
			pending = len(df[df["status"].str.lower() == "pending"])
			executed = len(df[df["status"].str.lower() == "executed"])
			cancelled = len(df[df["status"].str.lower() == "cancelled"])
			summary = f"Total: {len(df)} | Pending: {pending} | Executed: {executed} | Cancelled: {cancelled}"

			return self._success(summary)

		except FileNotFoundError:
			return self._error(f"No orders file found for strategy '{strategy}'", error_type="not_found")
		except Exception as e:
			return self._error(f"Error loading orders: {e}", error_type="error")

	def _cmd_watchlist_show(self, args: str) -> CommandResult:
		"""Show watchlist for strategy."""
		try:
			parsed = ArgParser.parse_positional(args, ["strategy"])
			strategy = parsed["strategy"]
		except ValidationError as e:
			return self._error(f"Usage: portfolio watchlist show <strategy>\n{str(e)}", error_type="usage")

		try:
			from tools.watchlist.watchlist_manager import WatchlistManager
			import pandas as pd

			wm = WatchlistManager(strategy)
			df = wm.load()

			if df is None or df.empty:
				return self._success(f"No watchlist found for strategy '{strategy}'")

			# Build display data
			data = []
			df_sorted = df.sort_values("signal_score", ascending=False, na_position="last")

			for _, row in df_sorted.iterrows():
				date = str(row.get("date", ""))
				if date and "T" in date:
					date = date.split("T")[0]
				elif pd.isna(row.get("date")):
					date = "-"

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
				score_str = f"{float(score):.3f}" if pd.notna(score) else "-"

				signals = str(row.get("signals", ""))
				if signals and signals.lower() != "nan":
					if len(signals) > 50:
						signals = signals[:47] + "..."
				else:
					signals = "-"

				data.append({
					"ticker": str(row.get("ticker", "")),
					"date": date,
					"close": f"{float(row.get('close', 0)):.2f}" if pd.notna(row.get("close")) else "-",
					"high": f"{float(row.get('high', 0)):.2f}" if pd.notna(row.get("high")) else "-",
					"low": f"{float(row.get('low', 0)):.2f}" if pd.notna(row.get("low")) else "-",
					"volume": volume_str,
					"score": score_str,
					"signals": signals,
				})

			table = Formatter.table(
				data,
				title=f"Watchlist: {strategy}",
				columns={
					"ticker": "Ticker",
					"date": "Date",
					"close": "Close",
					"high": "High",
					"low": "Low",
					"volume": "Volume",
					"score": "Score",
					"signals": "Signals",
				}
			)
			self.console.print(table)

			avg_score = df["signal_score"].mean() if "signal_score" in df.columns else 0
			summary = f"Total tickers: {len(df)}"
			if not pd.isna(avg_score):
				summary += f" | Avg score: {float(avg_score):.3f}"

			return self._success(summary)

		except FileNotFoundError:
			return self._error(f"No watchlist file found for strategy '{strategy}'", error_type="not_found")
		except Exception as e:
			return self._error(f"Error loading watchlist: {e}", error_type="error")

	def _cmd_watchlist_extended(self, args: str) -> CommandResult:
		"""Show detailed watchlist analysis."""
		try:
			parsed = ArgParser.parse_positional(args, ["strategy"])
			strategy = parsed["strategy"]
		except ValidationError as e:
			return self._error(f"Usage: portfolio watchlist extended <strategy>\n{str(e)}", error_type="usage")

		try:
			from tools.watchlist.watchlist_manager import WatchlistManager
			from tools.data.core import DataHistory
			import numpy as np

			wm = WatchlistManager(strategy)
			df = wm.load()

			if df is None or df.empty:
				return self._success(f"No watchlist found for strategy '{strategy}'")

			df_sorted = df.sort_values("signal_score", ascending=False, na_position="last")

			for idx, (_, row) in enumerate(df_sorted.iterrows(), 1):
				ticker = str(row.get("ticker", ""))
				score = float(row.get("signal_score", 0))
				Formatter.section(f"{idx}. {ticker} (Score: {score:.3f})")

				try:
					dh = DataHistory(ticker)
					price_data = dh.get_all()

					if price_data.empty:
						Formatter.info("No price data available")
						continue

					indicators = self._calculate_extended_indicators(price_data, ticker)

					# Display sections
					self._print_indicator_section("VOLATILITY & STOPS", [
						("14-day ATR", indicators.get("atr_14"), "€"),
						("20-day Volatility", indicators.get("volatility_20"), "%"),
						("Suggested stop loss", indicators.get("suggested_stop"), "%"),
					])

					self._print_indicator_section("MOMENTUM STRENGTH", [
						("RSI(14)", indicators.get("rsi_14"), "0-100"),
						("MACD histogram", indicators.get("macd_signal"), "positive/negative"),
						("Rate of Change (10-day)", indicators.get("roc_10"), "%"),
					])

				except Exception as e:
					Formatter.warning(f"Error loading indicators: {e}")

			return self._success(f"Extended analysis for {len(df_sorted)} tickers displayed")

		except FileNotFoundError:
			return self._error(f"No watchlist file found for strategy '{strategy}'", error_type="not_found")
		except Exception as e:
			return self._error(f"Error loading watchlist: {e}", error_type="error")

	def _cmd_watchlist_train(self, args: str) -> CommandResult:
		"""Train LGBM ranking model for strategy."""
		try:
			parsed = ArgParser.parse_positional(args, ["strategy"])
			strategy = parsed["strategy"]
		except ValidationError as e:
			return self._error(f"Usage: portfolio watchlist train <strategy>\n{str(e)}", error_type="usage")

		try:
			from core.context import AgentContext
			from agents.strategy.agent import StrategyAgent
			from agents.data.agent import DataAgent
			from agents.watchlist_ranking.agent import WatchlistRankingAgent
			from pathlib import Path

			Formatter.info(f"Training LGBM ranking model for {strategy}...")

			ctx = AgentContext()

			# Load strategy
			strategy_agent = StrategyAgent(f"strategy[{strategy}]", ctx)
			result = strategy_agent.process({})
			if result.get("status") != "success":
				return self._error(f"Failed to load strategy: {result.get('message')}", error_type="error")

			# Load data
			data_agent = DataAgent(f"data[{strategy}]", ctx)
			result = data_agent.process({})
			if result.get("status") != "success":
				return self._error(f"Failed to load data: {result.get('message')}", error_type="error")

			tickers_loaded = result.get("output", {}).get("data_after_quantity_filter", 0)
			indicators_count = result.get("output", {}).get("indicators_count", 0)
			Formatter.info(f"Data loaded: {tickers_loaded} tickers, {indicators_count} indicators")

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

				if samples and samples > 0 and folds > 0:
					# Display training summary
					summary_data = {
						"Model Path": model_path,
						"Total Samples": str(samples),
						"Features": str(features),
						"Folds": str(folds),
						"Avg IC": f"{metrics.get('avg_ic', 0):.4f}",
						"Avg RMSE": f"{metrics.get('avg_rmse', 0):.6f}",
						"Positive IC": f"{metrics.get('positive_ic_pct', 0):.1f}%",
					}

					table = Formatter.key_value_table(summary_data, title="Walk-Forward Training Summary")
					self.console.print(table)

					# Display recent fold details
					if fold_results:
						fold_data = []
						for fold in fold_results[-10:]:
							fold_data.append({
								"period": fold.get("period", "-"),
								"train": str(fold.get("train_n", 0)),
								"test": str(fold.get("test_n", 0)),
								"rmse": f"{fold.get('rmse', 0):.6f}",
								"ic": f"{fold.get('ic', 0):.4f}",
							})

						fold_table = Formatter.table(
							fold_data,
							title="Fold Results (Last 10)",
							columns={
								"period": "Period",
								"train": "Train",
								"test": "Test",
								"rmse": "RMSE",
								"ic": "IC",
							}
						)
						self.console.print(fold_table)

					return self._success("Training completed successfully")
				else:
					reason = metrics.get("reason", "Insufficient data")
					return self._success(f"Training completed but no model saved: {reason}")
			else:
				return self._error(f"Training failed: {result.get('message')}", error_type="error")

		except Exception as e:
			return self._error(f"Training error: {str(e)}", error_type="error")

	def _cmd_watchlist_rank(self, args: str) -> CommandResult:
		"""Rank tickers using trained model."""
		try:
			parsed = ArgParser.parse_positional(args, ["strategy"])
			strategy = parsed["strategy"]
		except ValidationError as e:
			return self._error(f"Usage: portfolio watchlist rank <strategy>\n{str(e)}", error_type="usage")

		try:
			from core.context import AgentContext
			from agents.strategy.agent import StrategyAgent
			from agents.data.agent import DataAgent
			from agents.watchlist_ranking.agent import WatchlistRankingAgent

			ctx = AgentContext()

			# Load strategy
			strategy_agent = StrategyAgent(f"strategy[{strategy}]", ctx)
			result = strategy_agent.process({})
			if result.get("status") != "success":
				return self._error(f"Failed to load strategy: {result.get('message')}", error_type="error")

			# Load data
			data_agent = DataAgent(f"data[{strategy}]", ctx)
			result = data_agent.process({})
			if result.get("status") != "success":
				return self._error(f"Failed to load data: {result.get('message')}", error_type="error")

			# Rank tickers
			ranking_agent = WatchlistRankingAgent("RankingAgent", ctx)
			result = ranking_agent.rank(strategy)

			if result.get("status") == "success":
				output = result.get("output", {})
				ranked = output.get("ranked", [])

				if ranked:
					# Build display data
					data = []
					for i, (ticker, score) in enumerate(ranked[:20], 1):
						data.append({
							"rank": str(i),
							"ticker": ticker,
							"score": f"{float(score):.4f}",
						})

					table = Formatter.table(
						data,
						title=f"Top Ranked Tickers - {strategy}",
						columns={"rank": "Rank", "ticker": "Ticker", "score": "Score"}
					)
					self.console.print(table)

					return self._success(f"Ranked {len(output.get('scores', {}))} tickers")
				else:
					return self._success("No tickers to rank")
			else:
				return self._error(f"Ranking failed: {result.get('message')}", error_type="error")

		except Exception as e:
			return self._error(f"Ranking error: {str(e)}", error_type="error")

	def _cmd_help(self, args: str) -> CommandResult:
		"""Show help for portfolio command."""
		help_text = """Portfolio Management Commands:

orders list <strategy>                  List orders for a strategy
watchlist show <strategy>               Show watchlist for strategy
watchlist extended <strategy>           Show detailed watchlist analysis
watchlist train <strategy>              Train LGBM ranking model
watchlist rank <strategy>               Rank tickers using trained model"""

		Formatter.panel(help_text, title="Portfolio Commands")
		return self._success("Help displayed")

	def _calculate_extended_indicators(self, price_data, ticker):
		"""Calculate extended technical indicators."""
		try:
			import numpy as np
			import pandas as pd

			if hasattr(price_data, 'index'):
				price_data = price_data.sort_index()
			else:
				price_data = price_data.sort_values('timestamp')

			close = price_data['close'].values if 'close' in price_data.columns else price_data.iloc[:, 4].values
			high = price_data['high'].values if 'high' in price_data.columns else price_data.iloc[:, 2].values
			low = price_data['low'].values if 'low' in price_data.columns else price_data.iloc[:, 3].values
			volume = price_data['volume'].values if 'volume' in price_data.columns else price_data.iloc[:, 5].values

			indicators = {}

			# ATR(14)
			if len(price_data) >= 14:
				tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1]))
				atr_14 = np.mean(tr[-14:])
				indicators['atr_14'] = round(atr_14, 2)
			else:
				indicators['atr_14'] = None

			# Volatility(20)
			if len(close) >= 20:
				returns = np.diff(close[-20:]) / close[-21:-1]
				volatility = np.std(returns) * 100
				indicators['volatility_20'] = round(volatility, 2)
				indicators['suggested_stop'] = round(volatility * 1.5, 2)
			else:
				indicators['volatility_20'] = None
				indicators['suggested_stop'] = None

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

			# MACD
			if len(close) >= 26:
				ema_12 = self._calculate_ema(close, 12)
				ema_26 = self._calculate_ema(close, 26)
				macd = ema_12[-1] - ema_26[-1]
				indicators['macd_signal'] = "positive" if macd > 0 else "negative"
			else:
				indicators['macd_signal'] = None

			# ROC(10)
			if len(close) >= 10:
				roc = ((close[-1] - close[-10]) / close[-10]) * 100
				indicators['roc_10'] = round(roc, 2)
			else:
				indicators['roc_10'] = None

			return indicators

		except Exception as e:
			return {}

	def _calculate_ema(self, data, period):
		"""Calculate Exponential Moving Average."""
		import numpy as np

		ema = np.zeros(len(data))
		sma = np.mean(data[:period])
		ema[period - 1] = sma

		multiplier = 2 / (period + 1)

		for i in range(period, len(data)):
			ema[i] = (data[i] * multiplier) + (ema[i - 1] * (1 - multiplier))

		return ema

	def _print_indicator_section(self, title: str, indicators: list):
		"""Print a section of indicators."""
		Formatter.section(title)
		for i, (label, value, unit) in enumerate(indicators):
			if value is None or (isinstance(value, str) and value.lower() == "n/a"):
				Formatter.info(f"{label}: N/A ({unit})")
			else:
				Formatter.info(f"{label}: {value} ({unit})")

	def _print_result(self, result: CommandResult):
		"""Print command result."""
		if result.success:
			Formatter.success(result.message)
		else:
			Formatter.error(result.message)
