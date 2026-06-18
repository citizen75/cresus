"""Finance bot for algorithmic trading with agent orchestration."""

import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.bot import Bot, STATUS_SUCCESS, STATUS_ERROR
from core.context import AgentContext
from tools.portfolio.manager import PortfolioManager
from tools.universe import Universe
from tools.watchlist import WatchlistManager
from agents.data.agent import DataAgent
from agents.watchlist_alphas.agent import WatchlistAlphasAgent
from agents.watchlist.agent import WatchListAgent
from agents.watchlist_ranking.agent import WatchlistRankingAgent
from agents.watchlist_scoring.agent import WatchlistScoringAgent
from agents.watchlist_filter.agent import WatchlistFilterAgent


class BotFinance(Bot):
	"""Finance bot for algorithmic trading with agent orchestration.

	Workflow steps:
	  pre_market  — data fetch → alphas → scoring → watchlist filter → ranking → save
	  in_market   — active trade management (placeholder)
	  post_market — daily analysis and cleanup (placeholder)
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

	def _run_agent(self, agent, *, fatal: bool = True) -> Dict[str, Any]:
		"""Run an agent, record it in agents_executed, and handle errors.

		Args:
			fatal: Raise RuntimeError on failure so the pipeline aborts.
			       False means log a warning and continue.
		"""
		name = getattr(agent, "name", type(agent).__name__)
		try:
			self.logger.info(f"[{name}] starting")
			response = agent.run(input_data={})
			self.agents_executed.append(name)
			if response.get("status") != STATUS_SUCCESS and fatal:
				raise RuntimeError(response.get("message", f"{name} returned non-success"))
			return response
		except RuntimeError:
			raise
		except Exception as e:
			self.agents_executed.append(name)
			if fatal:
				raise RuntimeError(f"{name} failed: {e}") from e
			self.logger.warning(f"[{name}] non-fatal error: {e}")
			return {"status": STATUS_ERROR, "message": str(e), "output": {}}

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
			self.context.set("strategy_name", self.strategy_name)
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
		"""data → alphas → ranking → scoring → watchlist → filter → save."""
		self.logger.info("Starting pre-market workflow")
		try:
			self._run_agent(DataAgent(f"DataAgent[{self.strategy_name}]", self.context))
			self._run_agent(WatchListAgent("WatchListAgent", context=self.context))
			alphas_resp = self._run_agent(WatchlistAlphasAgent(context=self.context))
			self._run_agent(WatchlistRankingAgent(context=self.context), fatal=False)
			self._run_agent(WatchlistScoringAgent("WatchlistScoringAgent", context=self.context), fatal=False)
			self._run_agent(WatchlistFilterAgent("WatchlistFilterAgent", context=self.context), fatal=False)
			self._save_watchlist()

			self.logger.info(f"Pre-market done: {len(self.agents_executed)} agents")
			return {
				"status": STATUS_SUCCESS,
				"params": params,
				"output": {
					"step": self.STEP_PRE_MARKET,
					"agents_executed": self.agents_executed,
					"data_history": self.context.get("data_history") or {},
					"alphas": alphas_resp.get("output", {}),
					"watchlist": self.context.get("watchlist") or {},
					"timestamp": datetime.now().isoformat(),
				},
			}
		except RuntimeError as e:
			return self._err(params, str(e))
		except Exception as e:
			self.logger.exception("Pre-market workflow failed")
			return self._err(params, str(e))

	def _process_in_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
		"""Active trade management (placeholder)."""
		self.logger.info("Starting in-market workflow")
		positions = self.portfolio_data.get("positions", [])
		self.logger.debug(f"In-market cycle: {len(positions)} open positions")
		return {
			"status": STATUS_SUCCESS,
			"params": params,
			"output": {
				"step": self.STEP_IN_MARKET,
				"trades_executed": 0,
				"pnl": 0.0,
				"positions": len(positions),
				"timestamp": datetime.now().isoformat(),
			},
		}

	def _process_post_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
		"""Daily analysis and cleanup (placeholder)."""
		self.logger.info("Starting post-market workflow")
		return {
			"status": STATUS_SUCCESS,
			"params": params,
			"output": {
				"step": self.STEP_POST_MARKET,
				"trades_analyzed": 0,
				"pnl_daily": 0.0,
				"positions_closed": 0,
				"timestamp": datetime.now().isoformat(),
			},
		}

	def _save_watchlist(self) -> None:
		"""Persist current watchlist to bot_dir/watchlist.csv."""
		watchlist = self.context.get("watchlist") or {}
		tickers = list(watchlist.keys()) if isinstance(watchlist, dict) else list(watchlist)

		if not tickers:
			self.logger.warning("No watchlist tickers to save")
			return

		ticker_scores = self.context.get("ticker_scores") or {}
		indicators = {
			ticker: {"score": (ticker_scores.get(ticker) or {}).get("score")}
			for ticker in tickers
			if (ticker_scores.get(ticker) or {}).get("score") is not None
		}

		wm = WatchlistManager(self.strategy_name, bot_dir=str(self.bot_dir))
		result = wm.save(tickers, ticker_scores, self.context.get("data_history") or {}, indicators=indicators)

		if result.get("status") == "success":
			self.logger.info(f"Watchlist saved: {result['ticker_count']} tickers → {result['file']}")
		else:
			self.logger.warning(f"Watchlist save issue: {result.get('message')}")

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
