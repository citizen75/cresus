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

		self.logger.info(f"[ALPHAS] Processing {len(alpha_definitions)} alphas for {len(data_history)} tickers")

		# Calculate alphas for each ticker
		alphas_added = 0
		alphas_skipped = 0
		errors = []

		for ticker, data in data_history.items():
			if not isinstance(data, pd.DataFrame) or data.empty:
				continue

			try:
				# Calculate each alpha for this ticker
				for alpha_name, alpha_formula in alpha_definitions.items():
					try:
						# Skip if alpha already exists in the data
						if alpha_name in data.columns:
							self.logger.debug(f"[ALPHAS] Skipping {alpha_name} for {ticker} - already exists")
							alphas_skipped += 1
							continue

						# Evaluate the formula with the data
						result = self._evaluate_formula(alpha_formula, data, ticker)

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

		# Store alpha names for CLI display
		self.context.set("alpha_names", list(alpha_definitions.keys()))

		# Log results
		if errors:
			self.logger.warning(f"[ALPHAS] {len(errors)} calculation errors")

		self.logger.info(f"[ALPHAS] Added {alphas_added} alpha values, skipped {alphas_skipped} existing alphas across {len(data_history)} tickers")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"alphas_calculated": alphas_added,
				"alphas_skipped": alphas_skipped,
				"alpha_count": len(alpha_definitions),
				"ticker_count": len(data_history),
				"errors": len(errors),
				"alpha_names": list(alpha_definitions.keys())
			},
			"message": f"Processed {len(alpha_definitions)} alphas: {alphas_added} calculated, {alphas_skipped} skipped (already exist)"
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

	def _evaluate_formula(self, formula: str, data: pd.DataFrame, ticker: str = "") -> pd.Series:
		"""Evaluate alpha formula for a single ticker's data.

		Supports both simple indicators (rsi_7), composites (roc_20 - roc_250),
		and conditional expressions (rsi_7 < 25, close > ema_20).

		Args:
			formula: Formula string
			data: OHLCV DataFrame for the ticker (sorted ascending by date, newest last)
			ticker: Ticker symbol for error reporting

		Returns:
			Series with calculated alpha values

		Raises:
			Exception: If formula evaluation fails
		"""
		from src.tools.indicators import calculate
		from src.tools.formula.dsl_helpers import is_dsl_formula
		from src.tools.formula.dsl_parser import evaluate_dsl
		import numpy as np

		# Check if it's a DSL formula (contains comparison/logical operators or shift notation)
		if is_dsl_formula(formula) or any(op in formula for op in ['<', '>', '<=', '>=', '==', '!=']):
			# Conditional/DSL formula - evaluate row by row
			return self._evaluate_dsl_formula(formula, data, ticker)

		# Parse as a simple indicator
		try:
			result = calculate([formula], data)
			return result[formula]
		except Exception:
			# Try as composite formula (e.g., "roc_20 - roc_250")
			if any(op in formula for op in ['+', '-', '*', '/', '(', ')']):
				return self._evaluate_composite_formula(formula, data, ticker)
			# Try as expression
			ticker_str = f" for {ticker}" if ticker else ""
			self.logger.error(f"[ALPHAS] Failed to calculate {formula}{ticker_str}")
			raise

	def _evaluate_dsl_formula(self, formula: str, data: pd.DataFrame, ticker: str = "") -> pd.Series:
		"""Evaluate DSL formula using vectorized pandas operations.

		Args:
			formula: DSL formula (e.g., "rsi_7 < 25", "close > ema_20")
			data: OHLCV DataFrame sorted ascending by date

		Returns:
			Series of boolean values (0.0/1.0) for each row
		"""
		import re
		import numpy as np
		from src.tools.indicators import calculate

		try:
			# Extract all indicator/column references from formula
			pattern = r'([a-z_]+(?:_\d+)?(?:\[\d+\])?)'
			matches = set(re.findall(pattern, formula, re.IGNORECASE))

			# Pre-calculate all indicators as columns
			data_work = data.copy()
			for match in matches:
				# Skip OHLCV columns
				if match.lower() in ['close', 'high', 'low', 'open', 'volume']:
					if match.upper() not in data_work.columns and match.lower() not in data_work.columns:
						if match.upper() in data.columns:
							data_work[match.lower()] = data[match.upper()]
						elif match in data.columns:
							data_work[match] = data[match]
					continue

				# Skip shift notation (handled in vectorized expression)
				if '[' in match:
					base_name = match.split('[')[0]
					if base_name not in matches or base_name == match:
						try:
							result = calculate([base_name], data_work)
							data_work[base_name] = result[base_name]
						except Exception:
							pass
					continue

				# Calculate indicator
				if match not in data_work.columns:
					try:
						result = calculate([match], data_work)
						data_work[match] = result[match]
					except Exception:
						pass

			# Convert DSL formula to vectorized pandas expression
			# Replace logical operators and comparisons
			vectorized_formula = self._convert_dsl_to_vectorized(formula)

			# Evaluate vectorized formula
			try:
				result = pd.eval(vectorized_formula, local_dict=data_work)
				if isinstance(result, pd.Series):
					return result.fillna(0).astype(float)
				else:
					# Handle scalar results
					return pd.Series([1.0 if result else 0.0] * len(data), index=data.index)
			except Exception:
				# Fall back to row-by-row evaluation
				return self._evaluate_dsl_formula_rowwise(formula, data, ticker)

		except Exception as e:
			ticker_str = f" for {ticker}" if ticker else ""
			self.logger.error(f"[ALPHAS] Failed to vectorize '{formula}'{ticker_str}: {str(e)}")
			# Fall back to row-by-row
			return self._evaluate_dsl_formula_rowwise(formula, data, ticker)

	def _convert_dsl_to_vectorized(self, formula: str) -> str:
		"""Convert DSL formula to pandas-compatible vectorized expression.

		Args:
			formula: DSL formula with logical operators

		Returns:
			Pandas-compatible expression
		"""
		import re
		# Replace DSL operators with pandas operators
		result = formula
		result = result.replace(' and ', ' & ')
		result = result.replace(' or ', ' | ')
		result = result.replace(' not ', ' ~')
		result = re.sub(r'\bnot\b', '~', result)
		return result

	def _evaluate_dsl_formula_rowwise(self, formula: str, data: pd.DataFrame, ticker: str = "") -> pd.Series:
		"""Fallback row-by-row evaluation for complex DSL formulas.

		Args:
			formula: DSL formula
			data: OHLCV DataFrame sorted ascending by date
			ticker: Ticker for error messages

		Returns:
			Series of boolean values (0.0/1.0) for each row
		"""
		from src.tools.formula.dsl_parser import evaluate_dsl
		import numpy as np

		# Normalize column names to lowercase
		data_normalized = data.copy()
		col_mapping = {}
		for col in data_normalized.columns:
			lower_col = col.lower()
			if lower_col != col:
				data_normalized[lower_col] = data_normalized[col]
				col_mapping[lower_col] = col

		# Data should be sorted ascending (oldest first)
		# But evaluate_dsl expects newest-first, so we need to reverse for evaluation
		data_desc = data_normalized.iloc[::-1].reset_index(drop=True)

		results = []
		for idx in range(len(data_desc)):
			# Get row and all previous rows (for shift operations like [0], [-1], etc.)
			row_data = data_desc.iloc[idx:].reset_index(drop=True)

			try:
				# Evaluate formula on this row
				result = evaluate_dsl(formula, row_data)
				results.append(1.0 if result else 0.0)
			except (ValueError, ZeroDivisionError) as e:
				error_msg = str(e)
				# Expected edge cases - silently return NaN
				if any(msg in error_msg for msg in ["Not enough data for shift", "Division by zero", "divide by zero"]):
					results.append(np.nan)
				else:
					ticker_str = f" for {ticker}" if ticker else ""
					self.logger.error(f"[ALPHAS] Failed to evaluate '{formula}' at row {idx}{ticker_str}: {error_msg}")
					results.append(np.nan)
			except Exception as e:
				ticker_str = f" for {ticker}" if ticker else ""
				self.logger.error(f"[ALPHAS] Failed to evaluate '{formula}' at row {idx}{ticker_str}: {str(e)}")
				results.append(np.nan)

		# Reverse back to original order (ascending by date)
		return pd.Series(results[::-1], index=data.index)

	def _evaluate_composite_formula(self, formula: str, data: pd.DataFrame, ticker: str = "") -> pd.Series:
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
			ticker_str = f" for {ticker}" if ticker else ""
			self.logger.error(f"[ALPHAS] Failed to evaluate formula '{formula}'{ticker_str}: {str(e)}")
			raise

	def _evaluate_expression(self, expr: str, data: pd.DataFrame, ticker: str = "") -> pd.Series:
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
			ticker_str = f" for {ticker}" if ticker else ""
			self.logger.error(f"[ALPHAS] Failed to evaluate expression '{expr}'{ticker_str}: {str(e)}")
			raise
