"""Stop loss agent for evaluating and calculating effective stop loss levels."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.portfolio.journal import Journal
from tools.strategy.strategy import StrategyManager


class StopLossAgent(Agent):
	"""Calculate effective stop loss levels for open positions.

	Handles both fix (static) and trailing (dynamic) stop losses.
	For trailing stops: updates highest_price and calculates dynamic stop level.
	Updates context with effective stop losses for each position.
	"""

	def __init__(self, name: str = "StopLossAgent"):
		"""Initialize stop loss agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Calculate effective stop losses for all open positions.

		For fix stops: uses stored stop_loss value as-is
		For trailing stops: calculates dynamic level = highest_price - trailing_stop_distance

		Args:
			input_data: Input data with:
				- day_data: Pre-sliced market data {ticker: row}

		Returns:
			Response with updated position stop losses in context
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"
		day_data = input_data.get("day_data") or self.context.get("day_data") or {}

		journal = Journal(portfolio_name, context=self.context.__dict__)

		# Calculate effective stop losses for all positions
		self._calculate_stop_losses(journal, day_data)

		return {
			"status": "success",
			"output": {"stop_losses_calculated": True},
			"message": "Stop losses calculated and updated in context",
		}

	def _calculate_stop_losses(self, journal: Journal, day_data: Dict[str, Any]) -> None:
		"""Calculate effective stop losses for all open positions.

		For fix stops: uses stored value as-is
		For trailing stops: calculates dynamic level and updates highest_price

		Args:
			journal: Journal for reading positions and updating highest_price
			day_data: Pre-sliced market data {ticker: row}
		"""
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
			# Get all open positions from journal
			open_positions = journal.get_open_positions()
			if open_positions.empty:
				return

			# Calculate effective stop loss for each position
			stop_losses = {}
			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				quantity = int(position.get("quantity", 0))
				stop_loss = float(position.get("stop_loss", 0)) if position.get("stop_loss") else None
				highest_price = float(position.get("highest_price", 0)) if position.get("highest_price") else None
				trailing_stop_distance = float(position.get("trailing_stop_distance", 0)) if position.get("trailing_stop_distance") else None

				if not stop_loss or quantity <= 0:
					continue

				effective_stop_loss = stop_loss

				# For trailing stops, update highest_price if new peak reached
				if stop_type == "trailing" and trailing_stop_distance is not None:
					day_high = self._get_day_high(ticker, day_data)
					if day_high is not None and highest_price is not None and day_high > highest_price:
						# Update highest price for trailing stop
						journal.update_position_highest_price(ticker, day_high)
						highest_price = day_high
						self.logger.debug(f"{ticker}: Updated highest_price to {day_high:.2f}")

					# Calculate dynamic stop loss for trailing stop
					if highest_price is not None:
						effective_stop_loss = highest_price - trailing_stop_distance
						self.logger.debug(f"{ticker}: Trailing stop dynamic_SL = {highest_price:.2f} - {trailing_stop_distance:.2f} = {effective_stop_loss:.2f}")

				stop_losses[ticker] = effective_stop_loss

			# Store effective stop losses in context for TransactAgent to use
			self.context.set("effective_stop_losses", stop_losses)
			self.logger.debug(f"Calculated effective stop losses for {len(stop_losses)} positions")

		except Exception as e:
			self.logger.error(f"Error calculating stop losses: {e}")

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
