"""Market regime detection agent - unified train/predict orchestrator."""

from typing import Any, Dict, Optional
from pathlib import Path
import os
import yaml
from datetime import datetime
from core.agent import Agent
from core.flow import Flow
from utils.env import get_db_root
from .sub_agents import (
	RegimeDataLoaderAgent,
	FeatureEngineerAgent,
	RegimeLabelerAgent,
	RegimeTrainerAgent,
	RegimePredictorAgent,
)


class MarketRegimeAgent(Agent):
	"""Unified agent for market regime detection (train + predict).

	Reads action from input_data, builds internal Flow of sub-agents,
	dispatches to either training or prediction pipeline.
	"""

	REGIME_NAMES = {
		0: "Strong_Bull",
		1: "Weak_Bull",
		2: "Neutral_Sideways",
		3: "Weak_Bear",
		4: "Strong_Bear",
		5: "Crisis_Volatile",
	}

	def __init__(self, name: str = "MarketRegimeAgent"):
		super().__init__(name)
		self.project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", "."))

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Dispatch to train or predict sub-pipeline."""
		if input_data is None:
			input_data = {}

		# Parse input
		universe = input_data.get("universe")
		action = input_data.get("action", "predict")
		lookback_days = input_data.get("lookback_days")
		session_date = input_data.get("session_date")
		data_path = input_data.get("data_path")

		if not universe:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "universe parameter required"
			}

		# Set defaults based on action
		if action == "train" and lookback_days is None:
			lookback_days = 1000
		elif action == "predict" and lookback_days is None:
			lookback_days = 100

		try:
			# Load or create config
			config = self._load_or_create_config(universe)

			# Prepare regime input for sub-agents
			regime_input = {
				"universe": universe,
				"action": action,
				"lookback_days": lookback_days or config.get("training", {}).get("lookback_days", 1000),
				"session_date": session_date,
				"data_path": data_path,
			}

			# Store in context for sub-agents
			self.context.set("regime_input", regime_input)
			self.context.set("regime_config", config)

			# Build and execute appropriate flow
			if action == "train":
				flow = self._build_train_flow(config)
				result = flow.process({})
				return self._format_train_result(result, universe, config)
			else:  # predict
				flow = self._build_predict_flow(config)
				result = flow.process({})
				return self._format_predict_result(result, universe)

		except Exception as e:
			self.logger.exception(f"Error in market regime agent: {e}")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Market regime detection failed: {str(e)}"
			}

	def _load_or_create_config(self, universe: str) -> Dict[str, Any]:
		"""Load YAML config or create default."""
		regimes_dir = get_db_root() / "regimes"
		regimes_dir.mkdir(parents=True, exist_ok=True)

		config_path = regimes_dir / f"{universe}.yml"

		if config_path.exists():
			try:
				with open(config_path, "r") as f:
					config = yaml.safe_load(f)
					self.logger.info(f"Loaded config from {config_path}")
					return config
			except Exception as e:
				self.logger.warning(f"Error reading config {config_path}: {e}")

		# Create default config
		config = self._get_default_config(universe)

		try:
			with open(config_path, "w") as f:
				yaml.dump(config, f, default_flow_style=False, sort_keys=False)
				self.logger.info(f"Created default config at {config_path}")
		except Exception as e:
			self.logger.warning(f"Could not save config: {e}")

		return config

	def _get_default_config(self, universe: str) -> Dict[str, Any]:
		"""Return default config dict."""
		db_root = get_db_root()
		model_path = str(db_root / "models" / f"{universe}_regime.pkl")
		return {
			"universe": universe,
			"model_path": model_path,
			"features": [
				"breadth_above_sma20",
				"breadth_above_sma50",
				"breadth_above_sma200",
				"breadth_change_5d",
				"adv_decline_ratio",
				"cross_correlation",
				"dispersion",
				"avg_atr_norm",
				"vol_regime_score",
				"momentum_factor_return",
				"meanrev_factor_return",
				"lowvol_factor_return",
				"quality_factor_return",
			],
			"training": {
				"lookback_days": 1000,
				"n_regimes": 6,
				"test_split": 0.2,
			},
			"lgbm_params": {
				"n_estimators": 200,
				"max_depth": 6,
				"learning_rate": 0.05,
				"num_leaves": 31,
				"min_child_samples": 20,
			},
		}

	def _build_train_flow(self, config: Dict) -> Flow:
		"""Create training sub-agent flow."""
		flow = Flow("RegimeTrainFlow", context=self.context)

		flow.add_step(
			RegimeDataLoaderAgent("DataLoaderStep"),
			step_name="data_loader",
			required=True
		)

		flow.add_step(
			FeatureEngineerAgent("FeatureEngineerStep"),
			step_name="feature_engineer",
			required=True
		)

		flow.add_step(
			RegimeLabelerAgent("RegimeLabelersStep"),
			step_name="regime_labeler",
			required=True
		)

		flow.add_step(
			RegimeTrainerAgent("RegimeTrainerStep"),
			step_name="regime_trainer",
			required=True
		)

		return flow

	def _build_predict_flow(self, config: Dict) -> Flow:
		"""Create prediction sub-agent flow."""
		flow = Flow("RegimePredictFlow", context=self.context)

		flow.add_step(
			RegimeDataLoaderAgent("DataLoaderStep"),
			step_name="data_loader",
			required=True
		)

		flow.add_step(
			FeatureEngineerAgent("FeatureEngineerStep"),
			step_name="feature_engineer",
			required=True
		)

		flow.add_step(
			RegimePredictorAgent("RegimePredictorStep"),
			step_name="regime_predictor",
			required=True
		)

		return flow

	def _format_train_result(self, flow_result: Dict, universe: str, config: Dict) -> Dict[str, Any]:
		"""Format training result for output."""
		training_result = self.context.get("training_result") or {}
		labels_series = self.context.get("labels_series")
		prices_df = self.context.get("prices_df")

		# Compute regime distribution
		regime_dist = {}
		if labels_series is not None:
			labels_clean = labels_series.dropna()
			for regime_id, regime_name in self.REGIME_NAMES.items():
				count = (labels_clean == regime_id).sum()
				regime_dist[f"{regime_id}_{regime_name}"] = int(count)

		# Date range
		date_range = {}
		if prices_df is not None:
			date_range = {
				"start": prices_df.index[0].isoformat(),
				"end": prices_df.index[-1].isoformat(),
			}

		# Feature importance
		top_features = training_result.get("metrics", {}).get("feature_importance", {})
		top_features_sorted = sorted(
			list(top_features.items()),
			key=lambda x: x[1],
			reverse=True
		)[:5]

		output = {
			"action": "train",
			"universe": universe,
			"model_path": training_result.get("model_path", ""),
			"training": {
				"n_samples_train": training_result.get("n_samples_train", 0),
				"n_samples_test": training_result.get("n_samples_test", 0),
				"date_range": date_range,
				"n_features": training_result.get("n_features", 0),
			},
			"metrics": {
				"accuracy": training_result.get("metrics", {}).get("accuracy", 0),
				"f1_macro": training_result.get("metrics", {}).get("f1_macro", 0),
				"f1_weighted": training_result.get("metrics", {}).get("f1_weighted", 0),
				"per_class_f1": training_result.get("metrics", {}).get("per_class_f1", {}),
			},
			"top_features": [{"name": name, "importance": float(importance)} for name, importance in top_features_sorted],
			"regime_distribution": regime_dist,
		}

		return {
			"status": "success",
			"input": {"universe": universe, "action": "train"},
			"output": output,
			"message": f"Trained model saved to {training_result.get('model_path', '')}"
		}

	def _format_predict_result(self, flow_result: Dict, universe: str) -> Dict[str, Any]:
		"""Format prediction result for output."""
		prediction_result = self.context.get("prediction_result") or {}
		regime_config = self.context.get("regime_config") or {}

		output = {
			"action": "predict",
			"universe": universe,
			"regime_id": prediction_result.get("regime_id", -1),
			"regime_name": prediction_result.get("regime_name", "Unknown"),
			"confidence": prediction_result.get("confidence", 0),
			"probabilities": prediction_result.get("probabilities", {}),
			"model_path": regime_config.get("model_path", ""),
		}

		return {
			"status": "success",
			"input": {"universe": universe, "action": "predict"},
			"output": output,
			"message": f"Current regime: {prediction_result.get('regime_name', 'Unknown')}"
		}
