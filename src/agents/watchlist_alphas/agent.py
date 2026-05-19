"""Watchlist Alphas Agent - Calculate alpha factors for feature engineering."""

from typing import Any, Dict, Optional, List
import pandas as pd
from core.agent import Agent


class WatchlistAlphasAgent(Agent):
	"""Calculate alpha factors from strategy config for all tickers.

	Reads alpha definitions from strategy configuration and calculates them
	for all series in data_history, adding alpha columns to the data.
	"""

	def __init__(self, name: str = "WatchlistAlphasAgent", context: Optional[Any] = None):
		"""Initialize alphas agent.

		Args:
			name: Agent name
			context: Optional shared AgentContext
		"""
		super().__init__(name, context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Calculate alphas for all tickers in data_history.

		Reads alphas from strategy config and calculates them for each ticker,
		adding alpha columns to data_history in context.

		Args:
			input_data: Optional input data (unused)

		Returns:
			Response with status and alpha calculation results
		"""
		if input_data is None:
			input_data = {}

		# Get strategy config and data
		strategy_config = self.context.get("strategy_config") or {}
		data_history = self.context.get("data_history") or {}

		if not data_history:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No data_history in context"
			}

		# Extract alphas from strategy config
		features = strategy_config.get("features", {})
		alphas_config = features.get("alphas", {})

		if not alphas_config:
			self.logger.info("[ALPHAS] No alphas configured in strategy")
			return {
				"status": "success",
				"input": input_data,
				"output": {"alphas_calculated": 0},
				"message": "No alphas configured"
			}

		# Flatten alpha definitions from all categories
		alpha_definitions = self._extract_alpha_definitions(alphas_config)

		if not alpha_definitions:
			return {
				"status": "success",
				"input": input_data,
				"output": {"alphas_calculated": 0},
				"message": "No valid alphas extracted"
			}

		self.logger.info(f"[ALPHAS] Calculating {len(alpha_definitions)} alphas for {len(data_history)} tickers")

		# Calculate alphas for each ticker
		alphas_added = 0
		errors = []

		for ticker, data in data_history.items():
			if not isinstance(data, pd.DataFrame) or data.empty:
				continue

			try:
				# Calculate each alpha for this ticker
				for alpha_name, alpha_formula in alpha_definitions.items():
					try:
						# Evaluate the formula with the data
						result = self._evaluate_formula(alpha_formula, data)

						# Add alpha column to data
						data[alpha_name] = result
						alphas_added += 1
					except Exception as e:
						errors.append(f"{alpha_name}: {str(e)}")
						self.logger.debug(f"[ALPHAS] Error calculating {alpha_name} for {ticker}: {str(e)}")

			except Exception as e:
				self.logger.error(f"[ALPHAS] Error processing {ticker}: {str(e)}")
				errors.append(f"{ticker}: {str(e)}")

		# Update context with modified data_history
		self.context.set("data_history", data_history)

		# Log results
		if errors:
			self.logger.warning(f"[ALPHAS] {len(errors)} calculation errors")

		self.logger.info(f"[ALPHAS] Added {alphas_added} alpha values across {len(data_history)} tickers")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"alphas_calculated": alphas_added,
				"alpha_count": len(alpha_definitions),
				"ticker_count": len(data_history),
				"errors": len(errors)
			},
			"message": f"Calculated {len(alpha_definitions)} alphas for {len(data_history)} tickers"
		}

	def _extract_alpha_definitions(self, alphas_config: Dict) -> Dict[str, str]:
		"""Extract alpha name -> formula mappings from config.

		Args:
			alphas_config: Alphas config section (may have categories)

		Returns:
			Dictionary mapping alpha names to formulas
		"""
		alpha_definitions = {}

		# Handle different config formats
		for category_key, category_value in alphas_config.items():
			if isinstance(category_value, list):
				# List of alpha definitions with name/formula
				for alpha in category_value:
					if isinstance(alpha, dict):
						alpha_name = alpha.get("name")
						alpha_formula = alpha.get("formula")
						if alpha_name and alpha_formula:
							alpha_definitions[alpha_name] = alpha_formula
					elif isinstance(alpha, str):
						# Simple string formula (legacy format)
						alpha_definitions[f"alpha_{category_key}_{len(alpha_definitions)}"] = alpha
			elif isinstance(category_value, str):
				# Single string formula
				alpha_definitions[f"alpha_{category_key}"] = category_value

		return alpha_definitions

	def _evaluate_formula(self, formula: str, data: pd.DataFrame) -> pd.Series:
		"""Evaluate alpha formula for a single ticker's data.

		Args:
			formula: Formula string (e.g., "rsi_14", "roc_20 - roc_250")
			data: OHLCV DataFrame for the ticker

		Returns:
			Series with calculated alpha values

		Raises:
			Exception: If formula evaluation fails
		"""
		from src.tools.indicators import calculate, parse_formula

		# Parse the formula
		try:
			indicator_name, params = parse_formula(formula)
		except Exception:
			# If parse_formula fails, try to evaluate as a simple expression
			return self._evaluate_expression(formula, data)

		# Check if it's a composite formula (e.g., "roc_20 - roc_250")
		if any(op in formula for op in ['+', '-', '*', '/', '(', ')']):
			# Composite formula - need to calculate components and combine
			return self._evaluate_composite_formula(formula, data)

		# Single indicator - calculate it
		try:
			result = calculate([formula], data)
			return result[formula]
		except Exception as e:
			self.logger.debug(f"[ALPHAS] Failed to calculate {formula}: {str(e)}")
			raise

	def _evaluate_composite_formula(self, formula: str, data: pd.DataFrame) -> pd.Series:
		"""Evaluate composite formulas with operators.

		Args:
			formula: Formula with operators (e.g., "roc_20 - roc_250")
			data: OHLCV DataFrame

		Returns:
			Series with calculated values
		"""
		from src.tools.indicators import calculate
		import re

		# Extract indicator references from the formula
		# Match patterns like "roc_20", "ema_10", "close[0]", etc.
		pattern = r'([a-z_]+(?:_\d+)?(?:\[\d+\])?)'
		matches = set(re.findall(pattern, formula, re.IGNORECASE))

		# Calculate each indicator
		indicators_data = {}
		for match in matches:
			if match in ['close', 'high', 'low', 'open', 'volume']:
				# Column reference
				if match.upper() in data.columns:
					indicators_data[match] = data[match.upper()]
				elif match in data.columns:
					indicators_data[match] = data[match]
				continue

			try:
				result = calculate([match], data)
				indicators_data[match] = result[match]
			except Exception:
				# If calculation fails, try to get from data columns
				if match.upper() in data.columns:
					indicators_data[match] = data[match.upper()]
				elif match in data.columns:
					indicators_data[match] = data[match]

		# Evaluate the formula with the calculated indicators
		try:
			# Create a safe namespace with the indicators
			namespace = {k: v.values for k, v in indicators_data.items()}
			result = eval(formula, {"__builtins__": {}}, namespace)
			return pd.Series(result, index=data.index)
		except Exception as e:
			self.logger.debug(f"[ALPHAS] Failed to evaluate formula '{formula}': {str(e)}")
			raise

	def _evaluate_expression(self, expr: str, data: pd.DataFrame) -> pd.Series:
		"""Evaluate expression-based alpha (for complex formulas).

		Args:
			expr: Expression string (e.g., "close > ema_20")
			data: OHLCV DataFrame

		Returns:
			Series with calculated values
		"""
		try:
			# Create namespace with data columns
			namespace = {col.lower(): data[col].values for col in data.columns}

			# Also add common references
			namespace['close'] = data['CLOSE'].values if 'CLOSE' in data.columns else data['Close'].values
			namespace['open'] = data['OPEN'].values if 'OPEN' in data.columns else data['Open'].values
			namespace['high'] = data['HIGH'].values if 'HIGH' in data.columns else data['High'].values
			namespace['low'] = data['LOW'].values if 'LOW' in data.columns else data['Low'].values

			# Evaluate the expression
			result = eval(expr, {"__builtins__": {}}, namespace)

			if isinstance(result, (list, tuple)):
				return pd.Series(result, index=data.index)
			else:
				return pd.Series(result, index=data.index) if not isinstance(result, pd.Series) else result
		except Exception as e:
			self.logger.debug(f"[ALPHAS] Failed to evaluate expression '{expr}': {str(e)}")
			raise
