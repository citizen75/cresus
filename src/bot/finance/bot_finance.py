"""Finance bot for algorithmic trading with agent orchestration."""

import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.bot import Bot, STATUS_SUCCESS, STATUS_ERROR
from core.context import AgentContext
from tools.portfolio.manager import PortfolioManager
from tools.portfolio.orders import Orders
from tools.universe import Universe
from agents.market_prep.agent import MarketPrepAgent
from agents.market_process.agent import MarketProcessAgent
from agents.market_close.agent import MarketCloseAgent


class BotFinance(Bot):
	"""Finance bot for algorithmic trading with agent orchestration.

	Workflow steps:
	  pre_market  — delegates to MarketPrepAgent (data → watchlist → ranking → entry/exit orders → save)
	  in_market   — delegates to MarketProcessAgent (executes pending orders, manages exits via TradingBroker)
	  post_market — delegates to MarketCloseAgent (expires stale pending orders)

	All three steps run the exact same pipelines backtests use, so live and
	backtested behavior no longer diverge.
	"""

	STEP_PRE_MARKET = "pre_market"
	STEP_IN_MARKET = "in_market"
	STEP_POST_MARKET = "post_market"
	VALID_STEPS = [STEP_PRE_MARKET, STEP_IN_MARKET, STEP_POST_MARKET]

	def __init__(self, name: str, bot_dir: Path, context: Optional[AgentContext] = None):
		super().__init__(name, bot_dir, context)
		self.strategy_name: str = ""
		self.strategy_config: Dict[str, Any] = {}
		self.tickers: List[str] = []
		self.portfolio_data: Dict[str, Any] = {}

	# ------------------------------------------------------------------
	# Helpers
	# ------------------------------------------------------------------

	@staticmethod
	def _err(params: Dict[str, Any], message: str) -> Dict[str, Any]:
		return {"status": STATUS_ERROR, "params": params, "output": {}, "message": message}

	# ------------------------------------------------------------------
	# Initialisation
	# ------------------------------------------------------------------

	def _load_configs(self) -> None:
		"""Load bot config (config.yml) and strategy config (strategy.yml).

		Raises on any missing or empty file so the caller aborts early.
		"""
		config_path = self.get_config_path()
		if not config_path.exists():
			raise FileNotFoundError(
				f"Bot config not found at {config_path}. "
				"Ensure strategy.yml was copied during bot creation."
			)

		bot_config = yaml.safe_load(config_path.read_text()) or {}
		self.strategy_name = bot_config.get("strategy", "")
		if not self.strategy_name:
			raise ValueError("'strategy' key missing from bot config")

		strategy_path = self.bot_dir / "strategy.yml"
		if not strategy_path.exists():
			raise FileNotFoundError(
				f"Strategy file not found at {strategy_path} "
				f"(expected strategy: {self.strategy_name})"
			)

		self.strategy_config = yaml.safe_load(strategy_path.read_text()) or {}
		if not self.strategy_config:
			raise ValueError(f"Strategy config is empty: {strategy_path}")

		self.logger.debug(f"Configs loaded: bot={self.name}, strategy={self.strategy_name}")

	def _load_portfolio(self) -> None:
		"""Load portfolio from PortfolioManager into self.portfolio_data.

		Non-fatal: logs a warning and sets safe defaults on failure.
		"""
		try:
			pm = PortfolioManager()
			metadata = pm.get_portfolio_metadata(self.strategy_name) or {}
			positions_data = pm.get_portfolio_positions(self.strategy_name) or {}
			cash = pm.get_portfolio_cash(self.strategy_name)

			self.portfolio_data = {
				"cash": cash,
				"positions": positions_data.get("positions", []),
				"total_value": positions_data.get("total_value", 0),
				"initial_capital": metadata.get("initial_capital", 0),
				"type": metadata.get("portfolio_type", "paper"),
				"currency": metadata.get("currency", "EUR"),
			}
			self.logger.debug(
				f"Portfolio loaded: cash={cash:.2f}, "
				f"positions={len(self.portfolio_data['positions'])}"
			)
		except Exception as e:
			self.logger.warning(f"Portfolio load failed (continuing with defaults): {e}")
			self.portfolio_data = {"cash": 0, "positions": [], "total_value": 0}

	def _load_tickers(self) -> List[str]:
		"""Resolve the ticker list from strategy config or its universe."""
		tickers = self.strategy_config.get("tickers", [])
		if tickers:
			return tickers

		universe_name = (
			self.strategy_config.get("source")
			or self.strategy_config.get("universe")
		)
		if not universe_name:
			self.logger.warning("No tickers or universe defined in strategy config")
			return []

		universe = Universe(universe_name)
		if not universe.exists():
			self.logger.warning(f"Universe '{universe_name}' not found")
			return []

		tickers = universe.get_tickers()
		self.logger.debug(f"Loaded {len(tickers)} tickers from universe '{universe_name}'")
		return tickers

	def _init_context(self) -> bool:
		"""Load configs, portfolio, and tickers; populate the shared context.

		Returns False (instead of raising) so process() can return a clean error response.
		"""
		try:
			self._load_configs()
			self._load_portfolio()
			self.tickers = self._load_tickers()

			if not self.tickers:
				self.logger.warning(f"No tickers found for strategy '{self.strategy_name}'")

			self.context.set("bot_name", self.name)
			self.context.set("bot_dir", str(self.bot_dir))
			self.context.set("strategy_name", self.strategy_name)
			self.context.set("portfolio_name", self.strategy_name)
			self.context.set("strategy_config", self.strategy_config)
			self.context.set("portfolio", self.portfolio_data)
			self.context.set("tickers", self.tickers)
			self.context.set("timestamp", datetime.now().isoformat())

			self.logger.debug(
				f"Context ready: strategy={self.strategy_name}, tickers={len(self.tickers)}"
			)
			return True
		except Exception as e:
			self.logger.error(f"Context init failed: {e}")
			return False

	# ------------------------------------------------------------------
	# Step workflows
	# ------------------------------------------------------------------

	def _process_pre_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
		"""Delegate to MarketPrepAgent (the same pipeline backtests use)."""
		self.logger.info("Starting pre-market workflow")
		try:
			agent = MarketPrepAgent(self.strategy_name, context=self.context)
			result = agent.run({"portfolio_name": self.strategy_name})
			self.agents_executed = agent.agents_executed
			if result.get("status") != STATUS_SUCCESS:
				return self._err(params, result.get("message", "Pre-market workflow failed"))

			self.logger.info(f"Pre-market done: {len(self.agents_executed)} agents")
			return {
				"status": STATUS_SUCCESS,
				"params": params,
				"output": {
					"step": self.STEP_PRE_MARKET,
					"agents_executed": self.agents_executed,
					"data_history": result.get("data_history") or {},
					"watchlist": result.get("watchlist") or {},
					"orders": result.get("orders") or [],
					"exit_orders": self.context.get("exit_orders") or [],
					"timestamp": datetime.now().isoformat(),
				},
			}
		except RuntimeError as e:
			return self._err(params, str(e))
		except Exception as e:
			self.logger.exception("Pre-market workflow failed")
			return self._err(params, str(e))

	def _process_in_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
		"""Active trade management: delegate to MarketProcessAgent (same pipeline backtests use)."""
		self.logger.info("Starting in-market workflow")
		positions = self.portfolio_data.get("positions", [])
		self.logger.debug(f"In-market cycle: {len(positions)} open positions (pre-execution)")

		trading_date = datetime.now().date()
		flow_result = MarketProcessAgent(context=self.context).process({
			"date": trading_date.isoformat(),
			"portfolio_name": self.strategy_name,
			"strategy_name": self.strategy_name,
		})
		broker_output = flow_result.get("output", {})

		# MarketProcessAgent/TradingBroker just refreshed the portfolio cache (new fills, closed
		# exits) - reload so "positions" reflects post-execution state, not the pre-run snapshot.
		self._load_portfolio()
		positions = self.portfolio_data.get("positions", [])

		orders_mgr = Orders(self.strategy_name, context=self.context.__dict__)
		pending_orders = len(orders_mgr.get_pending_orders())

		self.logger.info(f"In-market done: {pending_orders} pending order(s)")
		return {
			"status": STATUS_SUCCESS,
			"params": params,
			"output": {
				"step": self.STEP_IN_MARKET,
				"trades_executed": broker_output.get("total_executed", 0),
				"buy_executed": broker_output.get("buy_executed", 0),
				"exit_executed": broker_output.get("exit_executed", 0),
				"pending_orders": pending_orders,
				"pnl": 0.0,
				"positions": len(positions),
				"timestamp": datetime.now().isoformat(),
			},
		}

	def _process_post_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
		"""Delegate to MarketCloseAgent (same pipeline backtests use): expire stale pending orders."""
		self.logger.info("Starting post-market workflow")
		try:
			trading_date = datetime.now().date()
			self.context.set("date", trading_date)
			self.context.set("strategy_name", self.strategy_name)

			agent = MarketCloseAgent(self.strategy_name, context=self.context)
			result = agent.process({"portfolio_name": self.strategy_name})
			if result.get("status") != STATUS_SUCCESS:
				return self._err(params, result.get("message", "Post-market workflow failed"))

			output = result.get("output", {})
			return {
				"status": STATUS_SUCCESS,
				"params": params,
				"output": {
					"step": self.STEP_POST_MARKET,
					"trades_analyzed": 0,
					"pnl_daily": 0.0,
					"positions_closed": 0,
					"expired_count": output.get("expired_count", 0),
					"timestamp": datetime.now().isoformat(),
				},
			}
		except Exception as e:
			self.logger.exception("Post-market workflow failed")
			return self._err(params, str(e))

	# ------------------------------------------------------------------
	# Entry point
	# ------------------------------------------------------------------

	def process(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Run the requested trading step.

		Args:
			params: Must include 'step': one of pre_market / in_market / post_market
		"""
		params = params or {}
		step = params.get("step", self.STEP_PRE_MARKET)

		if step not in self.VALID_STEPS:
			return self._err(params, f"Invalid step '{step}'. Must be one of {self.VALID_STEPS}")

		if not self._init_context():
			return self._err(params, "Failed to initialise context")

		handlers = {
			self.STEP_PRE_MARKET: self._process_pre_market,
			self.STEP_IN_MARKET: self._process_in_market,
			self.STEP_POST_MARKET: self._process_post_market,
		}
		return handlers[step](params)
