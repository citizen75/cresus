"""Diagnostic test to identify data leakage in training."""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import spearmanr
from typing import Dict, Any, Optional
from pathlib import Path
from core.agent import Agent


class TrainDiagnostic(Agent):
	"""Diagnostic agent to test for data leakage by strict train/test split."""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Train on 2021-2025 data, test on 2026 data only.

		If metrics are still unrealistically high, leakage is confirmed.

		Args:
			input_data: Dict with 'data_history' and 'strategy_name'

		Returns:
			Diagnostic results
		"""
		if input_data is None:
			input_data = {}

		data_history = self.context.get("data_history") or {}
		strategy_name = self.context.get("strategy_name") or "unknown"

		if not data_history:
			return {
				"status": "error",
				"message": "No data_history in context"
			}

		self.logger.info("[DIAGNOSTIC] Building diagnostic dataset: train 2021-2025, test 2026")

		# Build cross-sectional dataset
		train_rows = []
		test_rows = []
		exclude_cols = {"timestamp", "ticker", "Dividends", "Stock Splits"}

		for ticker, df in data_history.items():
			if df is None or len(df) < 6:
				continue

			df_asc = df.sort_values("timestamp").reset_index(drop=True)
			if len(df_asc) < 6:
				continue

			feature_cols = [c for c in df_asc.columns if c not in exclude_cols]

			for i in range(len(df_asc) - 5):
				cur_close = df_asc.iloc[i].get("close")
				fut_close = df_asc.iloc[i + 5].get("close")
				cur_date = pd.to_datetime(df_asc.iloc[i]["timestamp"])

				if pd.isna(cur_close) or pd.isna(fut_close) or cur_close == 0:
					continue

				label = (fut_close - cur_close) / cur_close

				row = {col: df_asc.iloc[i][col] for col in feature_cols}
				row["date"] = cur_date
				row["ticker"] = ticker
				row["label"] = label

				# Split: 2021-2025 for training, 2026 for testing
				if cur_date.year >= 2026:
					test_rows.append(row)
				elif cur_date.year >= 2021:
					train_rows.append(row)

		if not train_rows or not test_rows:
			return {
				"status": "error",
				"message": f"Insufficient data: train_rows={len(train_rows)}, test_rows={len(test_rows)}"
			}

		df_train = pd.DataFrame(train_rows).fillna(0)
		df_test = pd.DataFrame(test_rows).fillna(0)

		self.logger.info(f"[DIAGNOSTIC] Train: {len(df_train)} rows, Test: {len(df_test)} rows")

		# Get feature columns
		feature_cols = [c for c in df_train.columns if c not in ["date", "ticker", "label"]]
		X_train = df_train[feature_cols].fillna(0)
		y_train = df_train["label"]
		X_test = df_test[feature_cols].fillna(0)
		y_test = df_test["label"]

		# Train model
		params = {
			"objective": "regression",
			"num_leaves": 31,
			"learning_rate": 0.05,
			"verbose": -1,
		}

		try:
			train_data = lgb.Dataset(X_train, label=y_train)
			model = lgb.train(params, train_data, num_boost_round=100)

			# Predict
			y_pred_train = model.predict(X_train)
			y_pred_test = model.predict(X_test)

			# Metrics on training data
			ic_train, _ = spearmanr(y_pred_train, y_train)
			rmse_train = np.sqrt(mean_squared_error(y_train, y_pred_train))
			r2_train = r2_score(y_train, y_pred_train)

			# Metrics on TEST data (2026 only)
			ic_test, _ = spearmanr(y_pred_test, y_test)
			rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
			r2_test = r2_score(y_test, y_pred_test)

			self.logger.info(f"[DIAGNOSTIC] Training set (2021-2025): IC={ic_train:.4f}, RMSE={rmse_train:.6f}, R²={r2_train:.4f}")
			self.logger.info(f"[DIAGNOSTIC] Test set (2026 only): IC={ic_test:.4f}, RMSE={rmse_test:.6f}, R²={r2_test:.4f}")
			self.logger.info(f"[DIAGNOSTIC] IC Drop: {ic_train - ic_test:.4f}")

			return {
				"status": "success",
				"output": {
					"train": {
						"samples": len(df_train),
						"ic": float(ic_train),
						"rmse": float(rmse_train),
						"r2": float(r2_train),
					},
					"test_2026": {
						"samples": len(df_test),
						"ic": float(ic_test),
						"rmse": float(rmse_test),
						"r2": float(r2_test),
					},
					"ic_drop": float(ic_train - ic_test),
					"has_leakage": ic_test < 0.1 and ic_train > 0.5,
				},
				"message": f"Diagnostic: IC train={ic_train:.4f}, test={ic_test:.4f}, drop={ic_train - ic_test:.4f}"
			}

		except Exception as e:
			self.logger.error(f"[DIAGNOSTIC] Test failed: {str(e)}")
			return {
				"status": "error",
				"message": f"Diagnostic failed: {str(e)}"
			}
