"""Stop loss exit agent for handling both fix and trailing stop losses."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
from core.agent import Agent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders
from tools.strategy.strategy import StrategyManager


class StopLossAgent(Agent):
	"""Execute stop loss exits when price falls below stop loss level.

	Handles both fix (static) and trailing (dynamic) stop losses.
	Checks all open positions and exits any that hit their stop loss price.
	Uses journal as source of truth for positions (no broker dependency).
	"""

	def __init__(self, name: str = "StopLossAgent"):
		"""Initialize stop loss agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute stop loss exits for positions that hit their stop loss.

		Args:
			input_data: Input data with:
				- portfolio_name: Portfolio to execute exits for
				- trading_date: Date of execution
				- day_data: Pre-sliced market data {ticker: row}

		Returns:
			Response with exit execution results
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"
		trading_date = self.context.get("date")
		day_data = input_data.get("day_data") or self.context.get("day_data") or {}

		if not trading_date:
			return {
				"status": "error",
				"message": "date not set in context",
				"output": {"executed": 0, "exits": []},
			}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		exit_results = self._execute_stop_loss_exits(journal, portfolio_name, trading_date, day_data)

		return {
			"status": "success",
			"output": {
				"executed": len([r for r in exit_results if r.get("status") == "filled"]),
				"exits": exit_results,
			},
			"message": f"Executed {len([r for r in exit_results if r.get('status') == 'filled'])} stop loss exits",
		}

	def _execute_stop_loss_exits(
		self,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		day_data: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Check open positions and execute exits if stop_loss hit.

		Handles both fix (static) and trailing (dynamic) stop losses.
		Records SELL transactions directly in journal (no broker needed).
		Marks corresponding orders as executed.

		Args:
			journal: Journal for reading positions and recording exits
			portfolio_name: Portfolio name
			trading_date: Date of execution
			day_data: Pre-sliced market data {ticker: row} for the specific date

		Returns:
			List of exit execution results
		"""
		execution_results = []
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)

		# Load strategy config to get stop_type
		strategy_name = self.context.get("strategy_name") if self.context else None
		stop_type = "fix"  # Default to fix

		if strategy_name:
			try:
				strategy_manager = StrategyManager()
				strategy_result = strategy_manager.load_strategy(strategy_name)
				if strategy_result.get("status") == "success":
					strategy_data = strategy_result.get("data", {})
					exit_config = strategy_data.get("exit", {}).get("parameters", {})
					if "stop" in exit_config:
						stop_type = exit_config["stop"].get("type", "fix")
			except Exception as e:
				self.logger.debug(f"Could not load strategy config: {e}")

		try:
			# Get all open positions from journal (source of truth)
			open_positions = journal.get_open_positions()
			if open_positions.empty:
				return execution_results

			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				quantity = int(position.get("quantity", 0))
				stop_loss = float(position.get("stop_loss", 0)) if position.get("stop_loss") else None
				highest_price = float(position.get("highest_price", 0)) if position.get("highest_price") else None
				trailing_stop_distance = float(position.get("trailing_stop_distance", 0)) if position.get("trailing_stop_distance") else None

				self.logger.debug(f"  Position {ticker}: qty={quantity}, type={stop_type}, SL={stop_loss}")

				if not stop_loss or quantity <= 0:
					self.logger.debug(f"    Skipping: no SL or zero qty")
					continue

				# Get market data for today (day_data is {ticker: row}, pre-sliced)
				day_low = self._get_day_low(ticker, day_data)
				day_high = self._get_day_high(ticker, day_data)
				self.logger.debug(f"    day_low={day_low}, day_high={day_high}")
				if day_low is None:
					self.logger.debug(f"    No market data")
					continue

				# For trailing stops, update highest_price and calculate dynamic stop loss
				effective_stop_loss = stop_loss
				if stop_type == "trailing" and trailing_stop_distance is not None:
					if day_high is not None and highest_price is not None and day_high > highest_price:
						# Update highest price for trailing stop
						new_highest = day_high
						journal.update_position_highest_price(ticker, new_highest)
						highest_price = new_highest
						self.logger.debug(f"    Updated highest_price to {new_highest:.2f}")

					# Calculate dynamic stop loss for trailing stop
					if highest_price is not None:
						effective_stop_loss = highest_price - trailing_stop_distance
						self.logger.debug(f"    Trailing stop: highest={highest_price:.2f}, distance={trailing_stop_distance:.2f}, dynamic_SL={effective_stop_loss:.2f}")

				# Check if stop_loss was hit
				if day_low <= effective_stop_loss:
					self.logger.info(f"STOP LOSS HIT: {ticker} day_low={day_low:.2f} <= SL={effective_stop_loss:.2f} ({stop_type})")

					# Execute EXIT at stop_loss price
					exit_price = effective_stop_loss

					execution_result = {
						"ticker": ticker,
						"quantity": quantity,
						"stop_loss": effective_stop_loss,
						"stop_type": stop_type,
						"day_low": day_low,
						"status": "filled",
						"exit_price": exit_price,
						"exit_quantity": quantity,
						"reason": "stop_loss_hit",
					}
					execution_results.append(execution_result)

					# Get market data row for metadata
					market_row = day_data.get(ticker)
					market_metadata = None
					if market_row is not None:
						# Extract OHLCV and indicators from row (handles pandas Series or dict)
						try:
							market_metadata = {}
							if hasattr(market_row, 'items'):  # pandas Series or dict
								for key, value in market_row.items():
									try:
										if value is None or (hasattr(value, '__class__') and 'NaT' in str(value)):
											market_metadata[key] = None
										elif hasattr(value, 'isoformat'):  # datetime/Timestamp
											market_metadata[key] = value.isoformat()
										else:
											try:
												market_metadata[key] = float(value)
											except (ValueError, TypeError):
												market_metadata[key] = str(value)
									except (ValueError, TypeError):
										market_metadata[key] = value
							if not market_metadata:  # If empty after iteration, set to None
								market_metadata = None
						except Exception as e:
							self.logger.debug(f"Error extracting market metadata for {ticker}: {e}")
							market_metadata = None

					# Record SELL transaction in journal
					journal.add_transaction(
						operation="SELL",
						ticker=ticker,
						quantity=quantity,
						price=exit_price,
						fees=0,
						notes=f"Stop loss exit @ {exit_price:.2f}",
						created_at=f"{trading_date.isoformat()}T14:00:00.000000",
						exit_type="stop_loss",
						status_at=f"{trading_date.isoformat()}T14:00:00.000000",
						metadata=market_metadata
					)

					# Mark related pending orders as executed
					self._mark_orders_executed(orders_mgr, ticker)

					self.logger.info(
						f"EXIT {quantity} {ticker} @ {exit_price:.2f} "
						f"(stop_loss hit at {stop_loss})"
					)
				else:
					self.logger.debug(f"    SL not hit: {day_low:.2f} > {effective_stop_loss:.2f}")

		except Exception as e:
			self.logger.error(f"Error executing stop loss exits: {e}")

		return execution_results

	def _mark_orders_executed(self, orders_mgr: Orders, ticker: str) -> None:
		"""Mark all pending orders for a ticker as executed.

		Args:
			orders_mgr: Orders manager
			ticker: Ticker symbol to mark
		"""
		try:
			pending = orders_mgr.get_pending_orders()
			if pending.empty:
				return

			for _, order in pending.iterrows():
				if str(order.get("ticker", "")).upper() == ticker.upper():
					order_id = str(order.get("id", ""))
					orders_mgr.update_order_status(order_id, "executed")
					self.logger.debug(f"Marked order {order_id[:8]} as executed")
		except Exception as e:
			self.logger.debug(f"Could not mark orders as executed: {e}")

	def _get_day_low(self, ticker: str, day_data: Dict[str, Any]) -> Optional[float]:
		"""Get daily low price for ticker from day data.

		Args:
			ticker: Ticker symbol
			day_data: Pre-sliced market data {ticker: row}

		Returns:
			Daily low price or None
		"""
		if ticker not in day_data:
			return None

		row = day_data[ticker]
		try:
			return float(row.get("low")) if "low" in row else None
		except (ValueError, AttributeError):
			return None

	def _get_day_high(self, ticker: str, day_data: Dict[str, Any]) -> Optional[float]:
		"""Get daily high price for ticker from day data.

		Args:
			ticker: Ticker symbol
			day_data: Pre-sliced market data {ticker: row}

		Returns:
			Daily high price or None
		"""
		if ticker not in day_data:
			return None

		row = day_data[ticker]
		try:
			return float(row.get("high")) if "high" in row else None
		except (ValueError, AttributeError):
			return None
