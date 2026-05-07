"""Train LightGBM regime classifier."""

from typing import Any, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import accuracy_score, f1_score, classification_report
import joblib
from core.agent import Agent
from utils.env import get_db_root


class RegimeTrainerAgent(Agent):
	"""Train LightGBM classifier on labeled feature data.

	Reads from context:
		features_df: feature matrix
		labels_series: regime labels
		cluster_to_regime_map: mapping from clusters
		regime_config: model path and LGBM parameters

	Writes to context:
		training_result: training metrics and model path
	"""

	def __init__(self, name: str = "RegimeTrainerAgent"):
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Train LightGBM model."""
		if input_data is None:
			input_data = {}

		features_df = self.context.get("features_df")
		labels_series = self.context.get("labels_series")
		cluster_to_regime_map = self.context.get("cluster_to_regime_map") or {}
		regime_config = self.context.get("regime_config") or {}
		regime_input = self.context.get("regime_input") or {}

		if features_df is None or labels_series is None:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "Missing features_df or labels_series in context"
			}

		try:
			# Prepare data
			feature_names = list(features_df.columns)
			X, y, X_test, y_test = self._prepare_data(
				features_df, labels_series, feature_names, regime_config.get("test_split", 0.2)
			)

			if len(X) < 50:
				return {
					"status": "error",
					"input": input_data,
					"output": {},
					"message": f"Insufficient training data: {len(X)} samples"
				}

			self.logger.info(f"Training on {len(X)} samples, testing on {len(X_test)}")

			# Train LightGBM
			lgbm_params = regime_config.get("lgbm_params", {})
			model = self._train_lgbm(X, y, lgbm_params, feature_names)

			# Evaluate
			metrics = self._evaluate(model, X_test, y_test, feature_names)

			# Save model
			model_path = regime_config.get("model_path")
			if not model_path:
				db_root = get_db_root()
				model_path = str(db_root / "models" / f"{regime_input.get('universe', 'default')}_regime.pkl")

			self._save_model(
				model, cluster_to_regime_map, feature_names, model_path, regime_input, regime_config
			)

			# Prepare output
			training_result = {
				"model_path": model_path,
				"n_samples_train": len(X),
				"n_samples_test": len(X_test),
				"n_features": len(feature_names),
				"feature_names": feature_names,
				"metrics": metrics,
			}

			self.context.set("training_result", training_result)

			# Regime distribution
			regime_dist = {}
			from agents.market_regime.agent import MarketRegimeAgent
			for regime_id, regime_name in MarketRegimeAgent.REGIME_NAMES.items():
				count = (y == regime_id).sum()
				regime_dist[f"{regime_id}_{regime_name}"] = int(count)

			return {
				"status": "success",
				"input": input_data,
				"output": {
					"model_path": model_path,
					"accuracy": float(metrics["accuracy"]),
					"n_samples": {"train": len(X), "test": len(X_test)},
					"regime_distribution": regime_dist,
					"top_features": sorted(
						list(zip(feature_names, model.feature_importances_)),
						key=lambda x: x[1],
						reverse=True,
					)[:5],
				},
				"message": f"Trained model saved to {model_path}"
			}

		except Exception as e:
			self.logger.exception(f"Error in training: {e}")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Training failed: {str(e)}"
			}

	def _prepare_data(
		self,
		features_df: pd.DataFrame,
		labels_series: pd.Series,
		feature_names: list,
		test_split: float
	) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
		"""Align features and labels, drop NaN, time-ordered split."""
		# Align and drop NaN
		aligned = pd.concat([features_df[feature_names], labels_series], axis=1)
		aligned.columns = feature_names + ["label"]
		aligned = aligned.dropna()

		if len(aligned) == 0:
			raise ValueError("No valid data after dropping NaN")

		# Time-ordered split
		split_idx = int(len(aligned) * (1 - test_split))
		train_data = aligned.iloc[:split_idx]
		test_data = aligned.iloc[split_idx:]

		X_train = train_data[feature_names].values
		y_train = train_data["label"].values.astype(int)
		X_test = test_data[feature_names].values
		y_test = test_data["label"].values.astype(int)

		return X_train, y_train, X_test, y_test

	def _train_lgbm(
		self, X_train: np.ndarray, y_train: np.ndarray, lgbm_params: dict, feature_names: list
	) -> lgb.LGBMClassifier:
		"""Create and fit LightGBM classifier."""
		params = {
			"objective": "multiclass",
			"num_class": 6,
			"n_estimators": lgbm_params.get("n_estimators", 200),
			"max_depth": lgbm_params.get("max_depth", 6),
			"learning_rate": lgbm_params.get("learning_rate", 0.05),
			"num_leaves": lgbm_params.get("num_leaves", 31),
			"min_child_samples": lgbm_params.get("min_child_samples", 20),
			"random_state": 42,
			"verbose": -1,
		}

		model = lgb.LGBMClassifier(**params)
		# Convert to DataFrame with feature names to match prediction
		X_train_df = pd.DataFrame(X_train, columns=feature_names)
		model.fit(X_train_df, y_train)

		return model

	def _evaluate(
		self, model: lgb.LGBMClassifier, X_test: np.ndarray, y_test: np.ndarray, feature_names: list
	) -> dict:
		"""Compute classification metrics."""
		# Convert to DataFrame with feature names to match training
		X_test_df = pd.DataFrame(X_test, columns=feature_names)
		y_pred = model.predict(X_test_df)
		y_proba = model.predict_proba(X_test_df)

		accuracy = float(accuracy_score(y_test, y_pred))
		f1_macro = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
		f1_weighted = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

		# Per-class F1
		f1_per_class = {}
		from agents.market_regime.agent import MarketRegimeAgent
		for regime_id, regime_name in MarketRegimeAgent.REGIME_NAMES.items():
			f1 = f1_score(y_test, y_pred, labels=[regime_id], average="weighted", zero_division=0)
			f1_per_class[f"{regime_id}_{regime_name}"] = float(f1)

		# Feature importance
		feature_importance = dict(zip(feature_names, model.feature_importances_))

		return {
			"accuracy": accuracy,
			"f1_macro": f1_macro,
			"f1_weighted": f1_weighted,
			"per_class_f1": f1_per_class,
			"feature_importance": feature_importance,
		}

	def _save_model(
		self,
		model: lgb.LGBMClassifier,
		cluster_to_regime_map: dict,
		feature_names: list,
		model_path: str,
		regime_input: dict,
		regime_config: dict
	) -> None:
		"""Save model artifact with joblib."""
		path = Path(model_path)
		path.parent.mkdir(parents=True, exist_ok=True)

		from agents.market_regime.agent import MarketRegimeAgent

		artifact = {
			"model": model,
			"feature_names": feature_names,
			"cluster_to_regime_map": cluster_to_regime_map,
			"universe": regime_input.get("universe", "default"),
			"trained_at": datetime.now().isoformat(),
			"n_regimes": regime_config.get("n_regimes", 6),
			"regime_names": MarketRegimeAgent.REGIME_NAMES,
		}

		joblib.dump(artifact, model_path)
		self.logger.info(f"Saved model to {model_path}")
