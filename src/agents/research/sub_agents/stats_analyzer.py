"""Portfolio stats analyzer sub-agent for analyzing performance metrics against strategy config."""

from typing import Any, Dict, Optional, List
import yaml
from pathlib import Path
from core.agent import Agent
from utils.env import get_db_root


class PortfolioStatsAnalyzerAgent(Agent):
	"""Analyze portfolio statistics and provide recommendations based on strategy config.

	Examines:
	- Risk-adjusted returns (Sharpe, Sortino, Calmar ratios)
	- Trade efficiency (win rate, profit factor, expectancy)
	- Position management (holding periods, drawdown recovery)
	- Signal quality (entry/exit timing)
	- Position sizing effectiveness
	"""

	def __init__(self, name: str = "PortfolioStatsAnalyzerAgent"):
		"""Initialize portfolio stats analyzer agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Analyze portfolio stats and compare against strategy config.

		Args:
			input_data: Input data with portfolio_metrics and strategy info

		Returns:
			Response with analysis findings and recommendations
		"""
		if input_data is None:
			input_data = {}

		# Get portfolio metrics from context or input
		metrics = input_data.get("portfolio_metrics", {})
		if not metrics and self.context:
			metrics = self.context.get("portfolio_metrics") or {}

		strategy_name = input_data.get("strategy_name")
		if not strategy_name and self.context:
			strategy_name = self.context.get("strategy_name")

		# Load strategy config
		strategy_config = None
		if strategy_name:
			strategy_config = self._load_strategy_config(strategy_name)

		# Perform analysis
		analysis = self._analyze_metrics(metrics, strategy_config)
		recommendations = self._generate_recommendations(metrics, strategy_config, analysis)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"strategy_name": strategy_name,
				"metrics_analysis": analysis,
				"recommendations": recommendations,
				"total_recommendations": len(recommendations),
			},
			"message": f"Analyzed portfolio stats: {len(recommendations)} recommendations"
		}

	def _load_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
		"""Load strategy configuration file.

		Args:
			strategy_name: Name of the strategy

		Returns:
			Strategy config dict or None if not found
		"""
		try:
			# Try multiple possible locations
			strategy_file = get_db_root() / "strategies" / f"{strategy_name}.yml"

			if not strategy_file.exists():
				self.logger.warning(f"Strategy config not found: {strategy_file}")
				return None

			with open(strategy_file, 'r') as f:
				config = yaml.safe_load(f)
				return config
		except Exception as e:
			self.logger.warning(f"Could not load strategy config: {e}")
			return None

	def _analyze_metrics(self, metrics: Dict[str, Any], strategy_config: Optional[Dict]) -> Dict[str, Any]:
		"""Analyze portfolio metrics.

		Args:
			metrics: Portfolio metrics dict
			strategy_config: Strategy configuration

		Returns:
			Analysis dict with findings
		"""
		analysis = {
			"returns_analysis": self._analyze_returns(metrics, strategy_config),
			"risk_analysis": self._analyze_risk(metrics, strategy_config),
			"trade_quality_analysis": self._analyze_trade_quality(metrics, strategy_config),
			"position_mgmt_analysis": self._analyze_position_management(metrics, strategy_config),
		}
		return analysis

	def _analyze_returns(self, metrics: Dict, strategy_config: Optional[Dict]) -> Dict[str, Any]:
		"""Analyze return metrics.

		Args:
			metrics: Portfolio metrics
			strategy_config: Strategy config

		Returns:
			Returns analysis dict
		"""
		total_return = metrics.get("total_return_pct", 0)
		benchmark_return = metrics.get("benchmark_return_pct", 0)
		excess_return = total_return - benchmark_return
		sharpe = metrics.get("sharpe_ratio", 0)
		sortino = metrics.get("sortino_ratio", 0)
		calmar = metrics.get("calmar_ratio", 0)

		return {
			"total_return": total_return,
			"excess_return": excess_return,
			"sharpe_ratio": sharpe,
			"sortino_ratio": sortino,
			"calmar_ratio": calmar,
			"assessment": self._assess_return_quality(total_return, sharpe, calmar),
		}

	def _analyze_risk(self, metrics: Dict, strategy_config: Optional[Dict]) -> Dict[str, Any]:
		"""Analyze risk metrics.

		Args:
			metrics: Portfolio metrics
			strategy_config: Strategy config

		Returns:
			Risk analysis dict
		"""
		max_drawdown = metrics.get("max_drawdown_pct", 0)
		max_dd_duration = metrics.get("max_drawdown_duration_days", 0)
		max_exposure = metrics.get("max_gross_exposure_pct", 0)

		# Expected max drawdown from config (if available)
		expected_atr_stop = "1.3 ATR"  # From momentum_cac config
		if strategy_config:
			exit_params = strategy_config.get("exit", {}).get("parameters", {})
			stop_loss = exit_params.get("stop_loss", {}).get("description", "")

		return {
			"max_drawdown_pct": max_drawdown,
			"drawdown_duration_days": max_dd_duration,
			"max_exposure_pct": max_exposure,
			"assessment": self._assess_risk_level(max_drawdown, max_dd_duration),
		}

	def _analyze_trade_quality(self, metrics: Dict, strategy_config: Optional[Dict]) -> Dict[str, Any]:
		"""Analyze trade quality metrics.

		Args:
			metrics: Portfolio metrics
			strategy_config: Strategy config

		Returns:
			Trade quality analysis dict
		"""
		total_trades = metrics.get("total_trades", 0)
		closed_trades = metrics.get("closed_trades", 0)
		open_trades = metrics.get("open_trades", 0)
		win_rate = metrics.get("win_rate_pct", 0)
		profit_factor = metrics.get("profit_factor", 0)
		expectancy = metrics.get("expectancy_pct", 0)

		avg_win = metrics.get("avg_winning_trade_pct", 0)
		avg_loss = metrics.get("avg_losing_trade_pct", 0)
		best_trade = metrics.get("best_trade_pct", 0)
		worst_trade = metrics.get("worst_trade_pct", 0)

		# Calculate risk/reward ratio
		rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

		return {
			"total_trades": total_trades,
			"closed_trades": closed_trades,
			"open_trades": open_trades,
			"win_rate_pct": win_rate,
			"profit_factor": profit_factor,
			"expectancy_pct": expectancy,
			"avg_win_pct": avg_win,
			"avg_loss_pct": avg_loss,
			"rr_ratio": rr_ratio,
			"best_trade_pct": best_trade,
			"worst_trade_pct": worst_trade,
			"assessment": self._assess_trade_quality(win_rate, profit_factor, expectancy),
		}

	def _analyze_position_management(self, metrics: Dict, strategy_config: Optional[Dict]) -> Dict[str, Any]:
		"""Analyze position management effectiveness.

		Args:
			metrics: Portfolio metrics
			strategy_config: Strategy config

		Returns:
			Position management analysis dict
		"""
		avg_win_duration = metrics.get("avg_winning_trade_duration_days", 0)
		avg_loss_duration = metrics.get("avg_losing_trade_duration_days", 0)
		open_pnl = metrics.get("open_trade_pnl", 0)

		# Expected holding period from config
		expected_holding = 12  # From momentum_cac
		if strategy_config:
			exit_params = strategy_config.get("exit", {}).get("parameters", {})
			hp_formula = exit_params.get("holding_period", {}).get("formula", 12)
			# Convert formula to numeric value
			if isinstance(hp_formula, str):
				try:
					expected_holding = int(float(hp_formula))
				except (ValueError, TypeError):
					expected_holding = 12
			else:
				expected_holding = int(hp_formula) if hp_formula else 12

		return {
			"avg_win_duration_days": avg_win_duration,
			"avg_loss_duration_days": avg_loss_duration,
			"open_pnl": open_pnl,
			"expected_holding_days": expected_holding,
			"assessment": self._assess_position_management(
				avg_win_duration, avg_loss_duration, expected_holding
			),
		}

	def _assess_return_quality(self, total_return: float, sharpe: float, calmar: float) -> str:
		"""Assess overall return quality.

		Args:
			total_return: Total return percentage
			sharpe: Sharpe ratio
			calmar: Calmar ratio

		Returns:
			Assessment string
		"""
		if total_return > 20 and sharpe > 1.5:
			return "excellent"
		elif total_return > 10 and sharpe > 1:
			return "good"
		elif total_return > 0 and sharpe > 0.5:
			return "acceptable"
		elif total_return < -20:
			return "poor"
		else:
			return "marginal"

	def _assess_risk_level(self, max_drawdown: float, duration_days: int) -> str:
		"""Assess risk level.

		Args:
			max_drawdown: Max drawdown percentage
			duration_days: Duration of max drawdown in days

		Returns:
			Risk assessment string
		"""
		if max_drawdown < 10 and duration_days < 30:
			return "low"
		elif max_drawdown < 20 and duration_days < 60:
			return "moderate"
		elif max_drawdown < 35 and duration_days < 90:
			return "moderate-high"
		else:
			return "high"

	def _assess_trade_quality(self, win_rate: float, profit_factor: float, expectancy: float) -> str:
		"""Assess trade quality.

		Args:
			win_rate: Win rate percentage
			profit_factor: Profit factor
			expectancy: Expectancy percentage

		Returns:
			Trade quality assessment
		"""
		if win_rate > 55 and profit_factor > 2.0 and expectancy > 1.0:
			return "excellent"
		elif win_rate > 50 and profit_factor > 1.5 and expectancy > 0.5:
			return "good"
		elif win_rate > 45 and profit_factor > 1.2 and expectancy > 0.1:
			return "acceptable"
		elif profit_factor < 1.0:
			return "negative"
		else:
			return "marginal"

	def _assess_position_management(self, win_duration: float, loss_duration: float, expected_holding: int) -> str:
		"""Assess position management effectiveness.

		Args:
			win_duration: Average winning trade duration in days
			loss_duration: Average losing trade duration in days
			expected_holding: Expected holding period from config

		Returns:
			Assessment string
		"""
		# Ideally we exit winners faster (before trend reversal) and cut losses quickly
		if win_duration > loss_duration and win_duration < expected_holding:
			return "good"
		elif abs(win_duration - loss_duration) < 2:
			return "passive"  # Not proactively managing either direction
		elif loss_duration > win_duration * 1.5:
			return "poor"  # Holding losers too long
		else:
			return "acceptable"

	def _generate_recommendations(
		self,
		metrics: Dict[str, Any],
		strategy_config: Optional[Dict],
		analysis: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Generate recommendations based on analysis.

		Args:
			metrics: Portfolio metrics
			strategy_config: Strategy configuration
			analysis: Analysis findings

		Returns:
			List of recommendation dicts
		"""
		recommendations = []

		# Returns analysis recommendations
		returns_analysis = analysis.get("returns_analysis", {})
		if returns_analysis.get("assessment") == "poor":
			recommendations.append({
				"category": "returns",
				"priority": "high",
				"title": "Negative Returns",
				"description": f"Strategy is losing money ({returns_analysis.get('total_return', 0):.1f}% return)",
				"recommendation": "Review entry conditions and signal quality. Check if watchlist has sufficient candidates and if entry filters are too strict or too loose.",
				"metrics_involved": ["total_return", "sharpe_ratio"],
			})

		if returns_analysis.get("sharpe_ratio", 0) < 0:
			recommendations.append({
				"category": "risk_adjusted_returns",
				"priority": "high",
				"title": "Negative Sharpe Ratio",
				"description": "Risk-adjusted returns are negative, indicating volatility is not compensated by returns",
				"recommendation": "Increase signal selectivity. Consider raising entry thresholds (e.g., RSI > 65, MACD > 0.7) to focus on higher-conviction setups.",
				"metrics_involved": ["sharpe_ratio", "win_rate"],
			})

		# Risk analysis recommendations
		risk_analysis = analysis.get("risk_analysis", {})
		if risk_analysis.get("assessment") == "high":
			recommendations.append({
				"category": "risk_management",
				"priority": "high",
				"title": "Excessive Drawdown",
				"description": f"Max drawdown of {risk_analysis.get('max_drawdown_pct', 0):.1f}% over {risk_analysis.get('drawdown_duration_days', 0)} days",
				"recommendation": "Tighten stop loss or increase position sizing constraints. Consider reducing position size or adding regime filters.",
				"metrics_involved": ["max_drawdown", "max_drawdown_duration"],
			})

		if risk_analysis.get("max_exposure_pct", 0) > 70:
			recommendations.append({
				"category": "position_sizing",
				"priority": "medium",
				"title": "Excessive Concentration",
				"description": f"Max gross exposure reached {risk_analysis.get('max_exposure_pct', 0):.1f}%",
				"recommendation": "Reduce position size per trade or limit concurrent positions. Check position_size formula in entry parameters.",
				"metrics_involved": ["max_gross_exposure"],
			})

		# Trade quality recommendations
		trade_analysis = analysis.get("trade_quality_analysis", {})
		if trade_analysis.get("assessment") == "negative":
			recommendations.append({
				"category": "trade_quality",
				"priority": "critical",
				"title": "Unprofitable Trades",
				"description": f"Profit factor of {trade_analysis.get('profit_factor', 0):.2f} (below 1.0 threshold)",
				"recommendation": "Review entry and exit logic. Losses exceed gains. Check if stop loss is too tight or take profit is too wide.",
				"metrics_involved": ["profit_factor", "expectancy"],
			})

		if trade_analysis.get("win_rate_pct", 0) < 35:
			recommendations.append({
				"category": "signal_quality",
				"priority": "high",
				"title": "Low Win Rate",
				"description": f"Only {trade_analysis.get('win_rate_pct', 0):.1f}% of trades are profitable",
				"recommendation": "Improve signal filters. Add confirmation from multiple indicators. Consider higher entry thresholds or additional regime filters.",
				"metrics_involved": ["win_rate", "rsi_threshold", "macd_threshold"],
			})

		if trade_analysis.get("rr_ratio", 0) < 1.0:
			recommendations.append({
				"category": "position_sizing",
				"priority": "high",
				"title": "Poor Risk/Reward Ratio",
				"description": f"Risk/Reward ratio of {trade_analysis.get('rr_ratio', 0):.2f} (avg win {trade_analysis.get('avg_win_pct', 0):.2f}% vs avg loss {trade_analysis.get('avg_loss_pct', 0):.2f}%)",
				"recommendation": "Increase take profit target or tighten stop loss. Adjust exit parameters (take_profit/stop_loss formula).",
				"metrics_involved": ["avg_winning_trade", "avg_losing_trade"],
			})

		# Position management recommendations
		pos_mgmt = analysis.get("position_mgmt_analysis", {})
		if pos_mgmt.get("avg_win_duration_days", 0) < pos_mgmt.get("avg_loss_duration_days", 0):
			recommendations.append({
				"category": "exit_timing",
				"priority": "medium",
				"title": "Exiting Winners Too Early",
				"description": f"Winning trades close in {pos_mgmt.get('avg_win_duration_days', 0):.1f} days but losing trades hold for {pos_mgmt.get('avg_loss_duration_days', 0):.1f} days",
				"recommendation": "Let winners run longer. Increase take_profit target or holding_period. Review exit conditions.",
				"metrics_involved": ["avg_winning_duration", "avg_losing_duration"],
			})

		if pos_mgmt.get("avg_loss_duration_days", 0) > pos_mgmt.get("expected_holding_days", 12):
			recommendations.append({
				"category": "position_management",
				"priority": "high",
				"title": "Holding Losses Too Long",
				"description": f"Losing trades held for {pos_mgmt.get('avg_loss_duration_days', 0):.1f} days (expected max: {pos_mgmt.get('expected_holding_days', 12)} days)",
				"recommendation": "Enable trailing stop or reduce holding_period. Cut losses faster to preserve capital.",
				"metrics_involved": ["avg_losing_duration", "holding_period"],
			})

		# Trade count recommendations
		total_trades = trade_analysis.get("total_trades", 0)
		if total_trades == 0:
			recommendations.append({
				"category": "signal_generation",
				"priority": "critical",
				"title": "No Trades Generated",
				"description": "Strategy produced zero trades during backtest period",
				"recommendation": "Verify strategy is enabled and watchlist is populated. Check if entry conditions are too strict or if data is available.",
				"metrics_involved": ["total_trades"],
			})
		elif total_trades < 5:
			recommendations.append({
				"category": "strategy_tuning",
				"priority": "medium",
				"title": "Insufficient Trade Sample",
				"description": f"Only {total_trades} trades generated (need 20+ for statistical significance)",
				"recommendation": "Relax entry filters or extend backtest period. Review watchlist parameters and signal thresholds.",
				"metrics_involved": ["total_trades"],
			})
		elif total_trades > 200:
			recommendations.append({
				"category": "signal_quality",
				"priority": "medium",
				"title": "Excessive Trading",
				"description": f"{total_trades} trades (avg {total_trades / max(metrics.get('period_days', 1), 1):.1f} per day)",
				"recommendation": "Add holding period filter or entry confirmation. Reduce transaction frequency to improve profitability.",
				"metrics_involved": ["total_trades", "transaction_costs"],
			})

		return recommendations
