"""Stop loss execution agent for TransactAgent."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
import pandas as pd
from core.agent import Agent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders


class StopLossAgent(Agent):
	"""Execute stop loss exits using pre-calculated effective stop losses.

	Uses effective_stop_losses from context (calculated by ExitAgent.StopLossAgent).
	Checks if prices hit the calculated levels and records SELL transactions.
	"""

	def __init__(self, name: str = "StopLossAgent"):
		"""Initialize stop loss agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute stop loss exits using effective stop losses from context.

		Args:
			input_data: Input data with:
				- day_data: Pre-sliced market data {ticker: row}

		Returns:
			Response with stop loss execution results
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
		"""Execute stop loss exits using effective stop losses from context.

		Effective stop losses are pre-calculated by ExitAgent.StopLossAgent.
		This method simply checks if prices hit the calculated levels and executes.

		Args:
			journal: Journal for recording transactions
			portfolio_name: Portfolio name
			trading_date: Date of execution
			day_data: Pre-sliced market data {ticker: row}

		Returns:
			List of stop loss execution results
		"""
		execution_results = []
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)

		# Get effective stop losses calculated by ExitAgent
		effective_stop_losses = self.context.get("effective_stop_losses") or {}
		if not effective_stop_losses:
			self.logger.debug("No effective stop losses in context, skipping stop loss exits")
			return execution_results

		try:
			# Get all open positions from journal
			open_positions = journal.get_open_positions()
			if open_positions.empty:
				return execution_results

			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				quantity = int(position.get("quantity", 0))

				if quantity <= 0 or ticker not in effective_stop_losses:
					continue

				# Skip positions entered on the same day (prevent same-day SL exit)
				entry_date = position.get("created_at")
				if entry_date:
					try:
						entry_dt = pd.to_datetime(entry_date).date()
						if entry_dt == trading_date:
							self.logger.debug(f"Skipping {ticker}: entered today, no SL check on same day")
							continue
					except Exception as e:
						self.logger.debug(f"Could not parse entry date for {ticker}: {e}")

				# Get the pre-calculated effective stop loss
				effective_stop_loss = effective_stop_losses[ticker]

				# Get market data for today
				day_low = self._get_day_low(ticker, day_data)
				if day_low is None:
					continue

				# Check if stop loss was hit
				if day_low <= effective_stop_loss:
					self.logger.info(f"STOP LOSS HIT: {ticker} day_low={day_low:.2f} <= SL={effective_stop_loss:.2f}")

					# Execute EXIT at stop loss level
					exit_price = effective_stop_loss

					execution_result = {
						"ticker": ticker,
						"quantity": quantity,
						"stop_loss": effective_stop_loss,
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
						try:
							market_metadata = {}
							if hasattr(market_row, 'items'):
								for key, value in market_row.items():
									try:
										if value is None or (hasattr(value, '__class__') and 'NaT' in str(value)):
											market_metadata[key] = None
										elif hasattr(value, 'isoformat'):
											market_metadata[key] = value.isoformat()
										else:
											try:
												market_metadata[key] = float(value)
											except (ValueError, TypeError):
												market_metadata[key] = str(value)
									except (ValueError, TypeError):
										market_metadata[key] = value
							if not market_metadata:
								market_metadata = None
						except Exception as e:
							self.logger.debug(f"Error extracting market metadata for {ticker}: {e}")
							market_metadata = None

					# Record SELL transaction
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

					# Mark orders as executed
					try:
						pending = orders_mgr.get_pending_orders()
						if not pending.empty:
							for _, order in pending.iterrows():
								if str(order.get("ticker", "")).upper() == ticker.upper():
									order_id = str(order.get("id", ""))
									orders_mgr.update_order_status(order_id, "executed")
					except Exception as e:
						self.logger.debug(f"Could not mark orders as executed: {e}")

					self.logger.info(f"EXIT {quantity} {ticker} @ {exit_price:.2f}")

		except Exception as e:
			self.logger.error(f"Error executing stop loss exits: {e}")

		return execution_results

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
