"""Pre-market trading bot job."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.job import Job, JobStatus, STATUS_SUCCESS, STATUS_ERROR
from core.context import AgentContext


class BotPremarket(Job):
	"""Pre-market trading bot for early market analysis and trade setup.

	Responsibilities:
	- Fetch overnight data and news
	- Calculate pre-market indicators
	- Identify trading opportunities
	- Setup initial positions before market open

	Usage:
		job = BotPremarket("premarket_monday", Path("./jobs/premarket_monday"))
		result = job.run(params={"markets": ["cac40"], "capital": 100000})
	"""

	def __init__(self, name: str, job_dir: Path, context: Optional[AgentContext] = None):
		"""Initialize pre-market bot.

		Args:
			name: Job identifier
			job_dir: Directory to store job data
			context: Optional AgentContext
		"""
		super().__init__(name, job_dir, context)
		self.markets: List[str] = []
		self.tickers_to_analyze: List[str] = []
		self.signals: Dict[str, Any] = {}
		self.setups: List[Dict[str, Any]] = []

	def fetch_overnight_data(self, markets: List[str]) -> Dict[str, Any]:
		"""Fetch overnight market data and news.

		Args:
			markets: List of market codes (e.g., ['cac40', 'nasdaq'])

		Returns:
			Dictionary with overnight data
		"""
		self.logger.info(f"Fetching overnight data for markets: {markets}")
		self.markets = markets

		self.context.set("markets", markets)
		self.context.set("fetch_time", datetime.now())

		return {
			"markets": markets,
			"data_points": 0,
			"news_items": 0
		}

	def calculate_indicators(self, tickers: List[str], indicators: List[str]) -> Dict[str, Dict[str, float]]:
		"""Calculate pre-market indicators for tickers.

		Args:
			tickers: List of ticker symbols
			indicators: List of indicator names to calculate

		Returns:
			Dictionary mapping tickers to their indicator values
		"""
		self.logger.info(f"Calculating {len(indicators)} indicators for {len(tickers)} tickers")
		self.tickers_to_analyze = tickers

		self.context.set("tickers", tickers)
		self.context.set("indicators", indicators)

		results = {}
		for ticker in tickers:
			results[ticker] = {
				f"{ind}": 0.0 for ind in indicators
			}

		return results

	def identify_opportunities(self, signal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
		"""Identify trading opportunities based on signals.

		Args:
			signal_config: Configuration for signal generation

		Returns:
			List of identified trading opportunities
		"""
		self.logger.info(f"Identifying opportunities with config: {signal_config}")

		self.context.set("signal_config", signal_config)

		opportunities = []
		for ticker in self.tickers_to_analyze:
			opportunities.append({
				"ticker": ticker,
				"signal": "neutral",
				"strength": 0.0,
				"entry_price": None,
				"stop_loss": None,
				"target": None
			})

		self.signals = {opp["ticker"]: opp for opp in opportunities}
		return opportunities

	def setup_positions(self, opportunities: List[Dict[str, Any]], portfolio_config: Dict[str, Any]) -> List[Dict[str, Any]]:
		"""Setup initial positions based on identified opportunities.

		Args:
			opportunities: List of trading opportunities
			portfolio_config: Portfolio configuration (capital, position sizing, etc.)

		Returns:
			List of position setup records
		"""
		self.logger.info(f"Setting up positions for {len(opportunities)} opportunities")

		self.context.set("portfolio_config", portfolio_config)

		setups = []
		capital = portfolio_config.get("capital", 100000)
		max_position_size = portfolio_config.get("max_position_size", 5000)

		for opp in opportunities:
			if opp["signal"] != "neutral":
				setup = {
					"ticker": opp["ticker"],
					"signal": opp["signal"],
					"position_size": min(max_position_size, capital / len(opportunities)),
					"entry_price": opp["entry_price"],
					"stop_loss": opp["stop_loss"],
					"target": opp["target"],
					"status": "ready"
				}
				setups.append(setup)

		self.setups = setups
		return setups

	def process(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process pre-market trading logic.

		Args:
			params: Dictionary with keys:
				- markets: List of market codes (e.g., ['cac40', 'nasdaq'])
				- tickers: Optional list of tickers to analyze
				- capital: Initial capital
				- signal_config: Signal configuration parameters

		Returns:
			Response dictionary with status and output
		"""
		if params is None:
			params = {}

		try:
			# Extract parameters
			markets = params.get("markets", ["cac40"])
			tickers = params.get("tickers", ["AC.PA", "OR.PA", "CS.PA"])
			capital = params.get("capital", 100000)
			signal_config = params.get("signal_config", {
				"rsi_oversold": 30,
				"rsi_overbought": 70,
				"macd_crossover": True
			})

			# Stage 1: Fetch data
			overnight_data = self.fetch_overnight_data(markets)

			# Stage 2: Calculate indicators
			indicators_result = self.calculate_indicators(
				tickers,
				["RSI", "MACD", "BB"]
			)

			# Stage 3: Identify opportunities
			opportunities = self.identify_opportunities(signal_config)

			# Stage 4: Setup positions
			setups = self.setup_positions(
				opportunities,
				{"capital": capital, "max_position_size": capital * 0.05}
			)

			# Build output
			output = {
				"overnight_data": overnight_data,
				"indicators": indicators_result,
				"opportunities": opportunities,
				"position_setups": setups,
				"summary": {
					"markets_analyzed": len(self.markets),
					"tickers_analyzed": len(self.tickers_to_analyze),
					"opportunities_found": len([o for o in opportunities if o["signal"] != "neutral"]),
					"positions_ready": len(self.setups),
					"timestamp": datetime.now().isoformat()
				}
			}

			return {
				"status": STATUS_SUCCESS,
				"params": params,
				"output": output,
			}

		except Exception as e:
			error_msg = f"Pre-market processing failed: {str(e)}"
			self.logger.exception(error_msg)
			return {
				"status": STATUS_ERROR,
				"params": params,
				"output": {},
				"message": error_msg,
			}

	def execute_premarket(self) -> Dict[str, Any]:
		"""Execute full pre-market workflow (legacy method).

		Deprecated: Use run() instead for consistent Agent/Flow/Job/Bot pattern.

		Returns:
			Summary of pre-market execution
		"""
		result = self.run(params={
			"markets": ["cac40", "nasdaq"],
			"tickers": ["AC.PA", "GOOGL", "MSFT"],
			"capital": 100000
		})

		if result.get("status") == STATUS_SUCCESS:
			summary = result.get("output", {}).get("summary", {})
			summary["status"] = "completed"
			return summary
		else:
			raise Exception(result.get("message", "Pre-market execution failed"))

	def get_ready_positions(self) -> List[Dict[str, Any]]:
		"""Get positions ready for market open.

		Returns:
			List of position setups
		"""
		return self.setups

	def get_signals_summary(self) -> Dict[str, str]:
		"""Get summary of all signals.

		Returns:
			Dictionary mapping tickers to signal values
		"""
		return {ticker: signal["signal"] for ticker, signal in self.signals.items()}
