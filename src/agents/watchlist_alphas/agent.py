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

		# Extract indicators to calculate from strategy config
		required_indicators = strategy_config.get("indicators", [])

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
		all_alpha_definitions = self._extract_alpha_definitions(alphas_config)

		if not all_alpha_definitions:
			return {
				"status": "success",
				"input": input_data,
				"output": {"alphas_calculated": 0},
				"message": "No valid alphas extracted"
			}

		# Optimization 3: Filter alphas to only those actually used
		alpha_definitions = self._filter_used_alphas(all_alpha_definitions, strategy_config)

		self.logger.info(f"[ALPHAS] Processing {len(alpha_definitions)}/{len(all_alpha_definitions)} alphas (filtered) for {len(data_history)} tickers")
		self.logger.debug(f"[ALPHAS] Pre-calculating {len(required_indicators)} required indicators")

		# Calculate alphas for each ticker
		alphas_added = 0
		alphas_skipped = 0
		errors = []

		for ticker, data in data_history.items():
			if not isinstance(data, pd.DataFrame) or data.empty:
				continue

			try:
				# Optimization 4: Cache pre-calculated indicators - check if already present
				data_enriched = self._ensure_indicators_calculated(data, required_indicators, ticker)

				# Collect calculated alphas to add all at once (avoid fragmentation)
				alphas_to_add = {}

				# Calculate each alpha for this ticker
				for alpha_name, alpha_formula in alpha_definitions.items():
					try:
						# Skip if alpha already exists in the data (cache)
						if alpha_name in data_enriched.columns:
							self.logger.debug(f"[ALPHAS] Skipping {alpha_name} for {ticker} - already cached")
							alphas_skipped += 1
							continue

						# Evaluate the formula with the enriched data
						result = self._evaluate_formula(alpha_formula, data_enriched, ticker)
						alphas_to_add[alpha_name] = result
						alphas_added += 1
					except Exception as e:
						errors.append(f"{alpha_name}: {str(e)}")
						self.logger.debug(f"[ALPHAS] Error calculating {alpha_name} for {ticker}: {str(e)}")

				# Add all alphas at once using pd.concat (avoid DataFrame fragmentation)
				if alphas_to_add:
					alpha_df = pd.DataFrame(alphas_to_add, index=data_enriched.index)
					data_enriched = pd.concat([data_enriched, alpha_df], axis=1)

				# Update the data_history with enriched data (includes calculated indicators and alphas)
				data_history[ticker] = data_enriched

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

		self.logger.info(f"[ALPHAS] Added {alphas_added} alpha values, skipped {alphas_skipped} cached alphas across {len(data_history)} tickers")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"alphas_calculated": alphas_added,
				"alphas_skipped": alphas_skipped,
				"alpha_count": len(alpha_definitions),
				"total_alphas_available": len(all_alpha_definitions),
				"ticker_count": len(data_history),
				"errors": len(errors),
				"alpha_names": list(alpha_definitions.keys())
			},
			"message": f"Processed {len(alpha_definitions)}/{len(all_alpha_definitions)} alphas: {alphas_added} calculated, {alphas_skipped} cached"
		}

	def _filter_used_alphas(self, all_alphas: Dict[str, str], strategy_config: Dict) -> Dict[str, str]:
		"""Optimization 3: Filter alphas to only those used in signals or other alphas.

		Args:
			all_alphas: All defined alphas
			strategy_config: Strategy configuration

		Returns:
			Filtered dict of only used alphas
		"""
		import re

		# Collect all names that are referenced anywhere
		referenced_names = set()

		# Check signals
		signals = strategy_config.get("signals", {})
		if isinstance(signals, dict):
			for signal_config in signals.values():
				if isinstance(signal_config, dict):
					formula = signal_config.get("formula", "")
				else:
					formula = str(signal_config)
				referenced_names.update(self._extract_referenced_names(formula))

		# Check entry/exit conditions
		for section in ["entry", "exit", "watchlist"]:
			section_config = strategy_config.get(section, {})
			if isinstance(section_config, dict):
				for key, val in section_config.items():
					if isinstance(val, dict):
						formula = val.get("formula", "")
					else:
						formula = str(val)
					referenced_names.update(self._extract_referenced_names(formula))

		# If no references found, return all alphas (safety fallback)
		if not referenced_names:
			self.logger.debug("[ALPHAS] No specific alpha references found, using all alphas")
			return all_alphas

		# Filter to only referenced alphas
		used_alphas = {name: formula for name, formula in all_alphas.items()
						if name in referenced_names}

		if used_alphas:
			self.logger.info(f"[ALPHAS] Filtered to {len(used_alphas)} used alphas (from {len(all_alphas)} total)")
			return used_alphas
		else:
			# If no alphas are directly referenced, use all (for feature engineering)
			self.logger.debug("[ALPHAS] No alphas directly referenced in signals, using all for features")
			return all_alphas

	def _extract_referenced_names(self, formula: str) -> set:
		"""Extract all identifier names from a formula.

		Args:
			formula: Formula string

		Returns:
			Set of referenced names
		"""
		import re
		# Match identifiers: start with letter/underscore, followed by alphanumeric/underscore
		# Exclude numbers and operators
		pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
		matches = re.findall(pattern, formula)
		# Filter out keywords and operators
		keywords = {'and', 'or', 'not', 'True', 'False'}
		return {m for m in matches if m not in keywords}

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
		"""Evaluate DSL formula using vectorized pandas operations (Optimization 1).

		Tries vectorized evaluation first, falls back to row-by-row if shift notation is complex.

		Args:
			formula: DSL formula (e.g., "rsi_7 < 25", "close > ema_20")
			data: OHLCV DataFrame sorted ascending by date

		Returns:
			Series of boolean values (0.0/1.0) for each row
		"""
		import re
		import numpy as np

		try:
			# Optimization 1: Try vectorized evaluation with shift preprocessing
			return self._evaluate_dsl_formula_vectorized(formula, data, ticker)
		except Exception as e:
			# Log as warning (not debug) since vectorization failed
			error_msg = str(e)
			if "keyword not valid" in error_msg or "not defined" in error_msg:
				self.logger.error(f"[ALPHAS] Vectorized eval failed for '{formula}': {error_msg}")
			else:
				self.logger.debug(f"[ALPHAS] Vectorized eval failed for '{formula}', using row-by-row: {error_msg}")
			return self._evaluate_dsl_formula_rowwise(formula, data, ticker)

	def _evaluate_dsl_formula_vectorized(self, formula: str, data: pd.DataFrame, ticker: str = "") -> pd.Series:
		"""Optimization 1: Vectorized DSL evaluation using pandas shifting.

		Pre-creates shifted columns and evaluates formula on entire DataFrame at once.

		Args:
			formula: DSL formula with shift notation
			data: DataFrame

		Returns:
			Series of results
		"""
		import re
		import numpy as np
		from src.tools.indicators import calculate

		data_work = data.copy()

		# Normalize column names to lowercase for consistency
		col_mapping = {}
		for col in data_work.columns:
			lower_col = col.lower()
			if lower_col != col:
				data_work[lower_col] = data_work[col]
				col_mapping[lower_col] = col

		# Extract all referenced names (indicators, columns)
		pattern = r'([a-z_]+(?:_\d+)?)'
		matches = set(re.findall(pattern, formula, re.IGNORECASE))

		# Pre-calculate missing indicators
		for match in matches:
			if match.lower() in ['close', 'high', 'low', 'open', 'volume']:
				continue
			if match not in data_work.columns:
				try:
					result = calculate([match], data_work)
					data_work[match] = result[match]
				except Exception:
					pass

		# Pre-create shifted columns for shift notation
		shift_pattern = r'(\w+)\[(-?\d+)\]'
		shift_pairs = set(re.findall(shift_pattern, formula))

		for col_name, shift_str in shift_pairs:
			shift = int(shift_str)
			# Handle [0] case - just reference the column as-is
			if shift == 0:
				# Make sure column exists with lowercase name
				if col_name not in data_work.columns and col_name.upper() in data_work.columns:
					data_work[col_name] = data_work[col_name.upper()]
				continue

			# Normalize shift: [-1] = previous, [-2] = 2 bars ago
			# pandas.shift(1) moves down (future bar), so we negate
			pandas_shift = -shift  # Negate for pandas semantics
			# Use absolute value in column name to avoid invalid names like "col_s-20"
			shifted_col_name = f"{col_name}_sh{abs(shift)}" if shift < 0 else f"{col_name}_s{shift}"

			# Get source column (handle case sensitivity)
			source_col = None
			if col_name in data_work.columns:
				source_col = col_name
			elif col_name.upper() in data_work.columns:
				source_col = col_name.upper()
				data_work[col_name] = data_work[col_name.upper()]  # Copy to lowercase
				source_col = col_name

			if source_col:
				data_work[shifted_col_name] = data_work[source_col].shift(pandas_shift)

		# Replace shift notation in formula with shifted column references
		vectorized_formula = formula
		for col_name, shift_str in shift_pairs:
			shift = int(shift_str)
			if shift == 0:
				# [0] means current, just use col_name as-is
				continue
			# Use same naming scheme as above
			shifted_col_name = f"{col_name}_sh{abs(shift)}" if shift < 0 else f"{col_name}_s{shift}"
			pattern = rf'{re.escape(col_name)}\[{re.escape(shift_str)}\]'
			vectorized_formula = re.sub(pattern, shifted_col_name, vectorized_formula)

		# Convert DSL operators to pandas operators
		vectorized_formula = self._convert_dsl_to_vectorized(vectorized_formula)

		# Evaluate
		try:
			result = pd.eval(vectorized_formula, local_dict=data_work)
			if isinstance(result, pd.Series):
				return result.fillna(0).astype(float)
			else:
				return pd.Series([1.0 if result else 0.0] * len(data), index=data.index)
		except Exception as e:
			raise ValueError(f"Vectorized evaluation failed: {str(e)}")

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
		# Replace && and 'and' with &
		result = result.replace('&&', '&')
		result = result.replace(' and ', ' & ')
		# Replace || and 'or' with |
		result = result.replace('||', '|')
		result = result.replace(' or ', ' | ')
		# Replace ! and 'not' with ~
		result = result.replace('!', '~')
		result = result.replace(' not ', ' ~ ')
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

	def _ensure_indicators_calculated(self, data: pd.DataFrame, required_indicators: list, ticker: str = "") -> pd.DataFrame:
		"""Ensure all required indicators are calculated and added to the DataFrame.

		Args:
			data: OHLCV DataFrame
			required_indicators: List of indicator names to calculate
			ticker: Ticker for error reporting

		Returns:
			DataFrame with calculated indicators added as columns
		"""
		from src.tools.indicators import calculate

		if not required_indicators:
			return data

		data_enriched = data.copy()

		# Calculate any missing indicators
		missing_indicators = [ind for ind in required_indicators if ind not in data_enriched.columns]

		if missing_indicators:
			try:
				calculated = calculate(missing_indicators, data_enriched)
				for ind_name, ind_series in calculated.items():
					data_enriched[ind_name] = ind_series.values
				self.logger.debug(f"[ALPHAS] Calculated {len(calculated)} indicators for {ticker}")
			except Exception as e:
				self.logger.warning(f"[ALPHAS] Failed to calculate some indicators for {ticker}: {str(e)}")
				# Continue anyway - some indicators may not be available

		return data_enriched

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
