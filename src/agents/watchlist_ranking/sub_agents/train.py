"""Training agent for LGBM ranking model with walk-forward validation."""

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
from core.agent import Agent
from utils.env import get_db_root


class TrainAgent(Agent):
	"""Train LGBM model for ticker ranking using walk-forward validation.

	Implements proper temporal validation:
	1. Builds cross-sectional dataset: (ticker, date) rows across all history
	2. Runs walk-forward: train on 3 months, test on 1 month, roll forward
	3. Computes out-of-sample metrics per fold
	4. Retrains final model on all data for live ranking
	"""

	def __init__(self, name: str = "TrainAgent", context: Optional[Any] = None):
		"""Initialize train agent.

		Args:
			name: Agent name
			context: Optional shared AgentContext
		"""
		super().__init__(name, context)
		self.model_dir = get_db_root() / "models" / "watchlist_ranking"
		self.model_dir.mkdir(parents=True, exist_ok=True)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Train or load LGBM model with walk-forward validation.

		Args:
			input_data: Dict with 'mode' ('train'|'rank') and 'strategy_name'

		Returns:
			Response with walk-forward metrics and model path
		"""
		if input_data is None:
			input_data = {}

		mode = input_data.get("mode", "rank")
		strategy_name = input_data.get("strategy_name")

		if not strategy_name:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "strategy_name required"
			}

		model_path = self._get_model_path(strategy_name)

		if mode == "train":
			return self._train_model(strategy_name, model_path)
		else:
			return self._load_model(strategy_name, model_path)

	def _train_model(self, strategy_name: str, model_path: Path) -> Dict[str, Any]:
		"""Train LGBM model with walk-forward validation.

		Args:
			strategy_name: Strategy name
			model_path: Path to save final model

		Returns:
			Training result with fold metrics and final model
		"""
		data_history = self.context.get("data_history") or {}

		if not data_history:
			return {
				"status": "error",
				"input": {"mode": "train", "strategy_name": strategy_name},
				"output": {},
				"message": "No data history available"
			}

		self.logger.info(f"[TRAIN] Building cross-sectional dataset for {strategy_name}")

		try:
			# Build full cross-sectional dataset
			full_df = self._build_cross_sectional_dataset(data_history)

			if len(full_df) == 0:
				self.logger.warning("[TRAIN] No valid training data generated")
				self.context.set("lgb_model", None)
				return {
					"status": "success",
					"input": {"mode": "train", "strategy_name": strategy_name},
					"output": {
						"model_path": str(model_path),
						"samples": 0,
						"features": 0,
						"metrics": {
							"status": "No model trained",
							"reason": "Insufficient historical data"
						},
						"fallback": "Feature-based scoring enabled"
					},
					"message": "Insufficient data for model training"
				}

			self.logger.info(f"[TRAIN] Cross-sectional dataset: {len(full_df)} rows, {len(full_df.columns) - 4} features")

			# Run walk-forward validation
			fold_results = self._walk_forward_validate(full_df)

			if not fold_results:
				self.logger.warning("[TRAIN] Walk-forward validation produced no valid folds")
				self.context.set("lgb_model", None)
				return {
					"status": "success",
					"input": {"mode": "train", "strategy_name": strategy_name},
					"output": {
						"samples": len(full_df),
						"folds": 0,
						"metrics": {"status": "No valid folds", "reason": "Insufficient data per fold"}
					},
					"message": "Walk-forward validation failed"
				}

			self.logger.info(f"[TRAIN] Walk-forward: {len(fold_results)} folds")

			# Retrain final model on all data
			final_model = self._retrain_final_model(full_df)

			# Save model
			with open(model_path, "wb") as f:
				pickle.dump(final_model, f)

			self.logger.info(f"[TRAIN] Model saved to {model_path}")
			self.context.set("lgb_model", final_model)

			# Compute summary statistics
			avg_ic = np.mean([f.get("ic", 0) for f in fold_results])
			avg_rmse = np.mean([f.get("rmse", 0) for f in fold_results])
			avg_mae = np.mean([f.get("mae", 0) for f in fold_results])
			positive_ic_pct = 100 * sum(1 for f in fold_results if f.get("ic", 0) > 0) / len(fold_results)

			return {
				"status": "success",
				"input": {"mode": "train", "strategy_name": strategy_name},
				"output": {
					"model_path": str(model_path),
					"samples": len(full_df),
					"features": len([c for c in full_df.columns if c not in ["date", "ticker", "label", "period"]]),
					"folds": len(fold_results),
					"fold_results": fold_results,
					"metrics": {
						"avg_ic": float(round(avg_ic, 4)),
						"avg_rmse": float(round(avg_rmse, 6)),
						"avg_mae": float(round(avg_mae, 6)),
						"positive_ic_pct": float(round(positive_ic_pct, 1)),
					},
					"model": {
						"type": "LightGBM",
						"params": {
							"objective": "regression",
							"num_leaves": 31,
							"learning_rate": 0.05,
						},
						"rounds": 100,
					}
				},
				"message": f"Walk-forward trained on {len(full_df)} samples, {len(fold_results)} folds, avg IC={avg_ic:.4f}"
			}

		except ImportError as e:
			self.logger.warning(f"[TRAIN] Import error: {str(e)}")
			self.context.set("lgb_model", None)
			return {
				"status": "success",
				"input": {"mode": "train", "strategy_name": strategy_name},
				"output": {
					"metrics": {
						"status": "Training failed",
						"reason": f"Import error: {str(e)}"
					},
					"fallback": "Feature-based scoring enabled"
				},
				"message": f"Training failed: {str(e)}"
			}
		except Exception as e:
			self.logger.error(f"[TRAIN] Training failed: {str(e)}")
			self.context.set("lgb_model", None)
			return {
				"status": "success",
				"input": {"mode": "train", "strategy_name": strategy_name},
				"output": {
					"metrics": {
						"status": "Training failed",
						"reason": str(e)
					},
					"fallback": "Feature-based scoring enabled"
				},
				"message": f"Training failed: {str(e)}"
			}

	def _build_cross_sectional_dataset(self, data_history: Dict, max_years: int = 5) -> pd.DataFrame:
		"""Build full cross-sectional dataset with all (ticker, date) rows.

		Args:
			data_history: Dict of ticker → DataFrame
			max_years: Limit history to last N years

		Returns:
			DataFrame with columns: date, ticker, features..., label
		"""
		rows = []
		cutoff = pd.Timestamp.now() - pd.DateOffset(years=max_years)
		exclude_cols = {"timestamp", "ticker", "Dividends", "Stock Splits"}

		for ticker, df in data_history.items():
			if df is None or len(df) < 6:
				continue

			# Sort ascending by timestamp for forward-looking labels
			df_asc = df.sort_values("timestamp").reset_index(drop=True)
			df_asc = df_asc[df_asc["timestamp"] >= cutoff]

			if len(df_asc) < 6:
				continue

			feature_cols = [c for c in df_asc.columns if c not in exclude_cols]

			# Generate one row per date (with label from T+5)
			for i in range(len(df_asc) - 5):
				cur_close = df_asc.iloc[i].get("close")
				fut_close = df_asc.iloc[i + 5].get("close")

				if pd.isna(cur_close) or pd.isna(fut_close) or cur_close == 0:
					continue

				# True forward 5-day return
				label = (fut_close - cur_close) / cur_close

				row = {col: df_asc.iloc[i][col] for col in feature_cols}
				row["date"] = df_asc.iloc[i]["timestamp"]
				row["ticker"] = ticker
				row["label"] = label
				rows.append(row)

		if not rows:
			return pd.DataFrame()

		full_df = pd.DataFrame(rows).fillna(0)
		full_df["period"] = full_df["date"].dt.to_period("M")
		return full_df

	def _walk_forward_validate(self, full_df: pd.DataFrame, train_months: int = 3, test_months: int = 1) -> List[Dict[str, Any]]:
		"""Run walk-forward validation: train on past N months, test on next month.

		Args:
			full_df: Cross-sectional dataset
			train_months: Number of months to train on
			test_months: Number of months to test on

		Returns:
			List of fold results with metrics
		"""
		import lightgbm as lgb
		from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
		from scipy.stats import spearmanr

		full_df = full_df.copy()
		periods = sorted(full_df["period"].unique())
		feature_cols = [c for c in full_df.columns if c not in ["date", "ticker", "label", "period"]]

		fold_results = []
		params = {
			"objective": "regression",
			"num_leaves": 31,
			"learning_rate": 0.05,
			"verbose": -1,
		}

		# Walk-forward loop
		for i in range(train_months, len(periods)):
			# Training periods: [i-train_months, i-1]
			train_start = max(0, i - train_months)
			train_periods = periods[train_start:i]

			# Test period: month i
			test_period = periods[i:i + test_months] if i + test_months <= len(periods) else periods[i:]

			# Split data
			train_mask = full_df["period"].isin(train_periods)
			test_mask = full_df["period"].isin(test_period)

			X_train = full_df[train_mask][feature_cols].fillna(0)
			y_train = full_df[train_mask]["label"]
			X_test = full_df[test_mask][feature_cols].fillna(0)
			y_test = full_df[test_mask]["label"]

			# Skip if insufficient data
			if len(X_train) < 20 or len(X_test) < 5:
				self.logger.debug(f"[TRAIN] Skipping fold {periods[i]}: train={len(X_train)}, test={len(X_test)}")
				continue

			try:
				# Train model
				train_data = lgb.Dataset(X_train, label=y_train)
				model = lgb.train(params, train_data, num_boost_round=100)

				# Predict
				y_pred = model.predict(X_test)

				# Compute metrics
				rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
				mae = float(mean_absolute_error(y_test, y_pred))
				r2 = float(r2_score(y_test, y_pred))

				# Information Coefficient (Spearman rank correlation)
				ic_val, _ = spearmanr(y_pred, y_test)
				ic = float(ic_val) if not np.isnan(ic_val) else 0.0

				fold_results.append({
					"period": str(test_period[0]),
					"train_n": int(len(X_train)),
					"test_n": int(len(X_test)),
					"rmse": round(rmse, 6),
					"mae": round(mae, 6),
					"r2": round(r2, 4),
					"ic": round(ic, 4),
				})

			except Exception as e:
				self.logger.warning(f"[TRAIN] Fold {periods[i]} failed: {str(e)}")
				continue

		return fold_results

	def _retrain_final_model(self, full_df: pd.DataFrame) -> Any:
		"""Retrain final model on all available data.

		Args:
			full_df: Full cross-sectional dataset

		Returns:
			Trained LightGBM model
		"""
		import lightgbm as lgb

		feature_cols = [c for c in full_df.columns if c not in ["date", "ticker", "label", "period"]]
		X = full_df[feature_cols].fillna(0)
		y = full_df["label"]

		# Remove rows with missing labels
		valid_idx = y.notna()
		X = X[valid_idx]
		y = y[valid_idx]

		params = {
			"objective": "regression",
			"num_leaves": 31,
			"learning_rate": 0.05,
			"verbose": -1,
		}

		train_data = lgb.Dataset(X, label=y)
		model = lgb.train(params, train_data, num_boost_round=100)

		self.logger.info(f"[TRAIN] Final model trained on {len(X)} samples")
		return model

	def _load_model(self, strategy_name: str, model_path: Path) -> Dict[str, Any]:
		"""Load pre-trained LGBM model.

		Args:
			strategy_name: Strategy name
			model_path: Path to model file

		Returns:
			Load result
		"""
		if not model_path.exists():
			self.logger.warning(f"[TRAIN] Model not found at {model_path}, skipping load")
			self.context.set("lgb_model", None)
			return {
				"status": "success",
				"input": {"mode": "rank", "strategy_name": strategy_name},
				"output": {"model_path": str(model_path), "loaded": False},
				"message": "No model to load"
			}

		try:
			with open(model_path, "rb") as f:
				model = pickle.load(f)

			self.logger.info(f"[TRAIN] Loaded model from {model_path}")
			self.context.set("lgb_model", model)

			return {
				"status": "success",
				"input": {"mode": "rank", "strategy_name": strategy_name},
				"output": {"model_path": str(model_path), "loaded": True},
				"message": "Model loaded successfully"
			}

		except Exception as e:
			self.logger.error(f"[TRAIN] Failed to load model: {str(e)}")
			self.context.set("lgb_model", None)
			return {
				"status": "success",
				"input": {"mode": "rank", "strategy_name": strategy_name},
				"output": {"model_path": str(model_path), "loaded": False},
				"message": f"Failed to load model: {str(e)}"
			}

	def _get_model_path(self, strategy_name: str) -> Path:
		"""Get model file path for strategy.

		Args:
			strategy_name: Strategy name

		Returns:
			Path to model file
		"""
		return self.model_dir / f"{strategy_name}_lgb.pkl"
