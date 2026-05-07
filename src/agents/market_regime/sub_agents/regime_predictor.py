"""Predict market regime using trained model."""

from typing import Any, Dict, Optional
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from core.agent import Agent


class RegimePredictorAgent(Agent):
	"""Load trained model and predict regime for session_date.

	Reads from context:
		features_df: feature matrix
		regime_config: model_path
		regime_input: session_date

	Writes to context:
		prediction_result: regime prediction and probabilities
	"""

	def __init__(self, name: str = "RegimePredictorAgent"):
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Load model and predict."""
		if input_data is None:
			input_data = {}

		features_df = self.context.get("features_df")
		regime_config = self.context.get("regime_config") or {}
		regime_input = self.context.get("regime_input") or {}

		if features_df is None or features_df.empty:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No features_df in context"
			}

		try:
			model_path = regime_config.get("model_path")
			if not model_path:
				return {
					"status": "error",
					"input": input_data,
					"output": {},
					"message": "No model_path in regime_config"
				}

			# Load model
			artifact = self._load_model(model_path)
			model = artifact["model"]
			feature_names = artifact["feature_names"]
			regime_names = artifact.get("regime_names", {})

			# Extract feature row
			session_date = regime_input.get("session_date")
			if not session_date:
				from datetime import datetime
				session_date = datetime.now().date().isoformat()

			feature_row = self._extract_feature_row(features_df, session_date, feature_names)

			if feature_row is None:
				return {
					"status": "error",
					"input": input_data,
					"output": {},
					"message": f"Could not extract features for {session_date}"
				}

			# Predict
			prediction = self._predict(model, feature_row, feature_names, regime_names)

			# Get current feature values
			try:
				row_idx = features_df.index.get_indexer_for([pd.Timestamp(session_date)])[0]
				if row_idx >= 0:
					features_used = features_df.iloc[row_idx].to_dict()
				else:
					features_used = {}
			except Exception:
				features_used = {}

			# Store in context
			self.context.set("prediction_result", prediction)

			return {
				"status": "success",
				"input": input_data,
				"output": {
					"session_date": session_date,
					"regime_id": int(prediction["regime_id"]),
					"regime_name": prediction["regime_name"],
					"confidence": float(prediction["confidence"]),
					"probabilities": {
						k: float(v) for k, v in prediction["probabilities"].items()
					},
					"model_path": model_path,
				},
				"message": f"Regime prediction: {prediction['regime_name']} (confidence: {prediction['confidence']:.2%})"
			}

		except Exception as e:
			self.logger.exception(f"Error in prediction: {e}")
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Prediction failed: {str(e)}"
			}

	def _load_model(self, model_path: str) -> dict:
		"""Load model artifact."""
		path = Path(model_path)
		if not path.exists():
			raise FileNotFoundError(f"Model not found: {model_path}")

		artifact = joblib.load(model_path)
		return artifact

	def _extract_feature_row(
		self, features_df: pd.DataFrame, session_date: str, feature_names: list
	) -> Optional[np.ndarray]:
		"""Extract feature row for session_date."""
		try:
			# Try exact match
			if session_date in features_df.index.astype(str):
				row = features_df.loc[session_date, feature_names]
			else:
				# Try closest earlier date
				ts = pd.Timestamp(session_date)
				mask = features_df.index <= ts
				if mask.any():
					idx = features_df.index[mask].max()
					row = features_df.loc[idx, feature_names]
				else:
					return None

			# Convert to array
			row_array = np.array(row, dtype=float)

			# Check for NaN
			if np.isnan(row_array).any():
				# Forward fill within features_df
				filled = features_df[feature_names].fillna(method="ffill").iloc[-1]
				row_array = np.array(filled, dtype=float)

			return row_array.reshape(1, -1)

		except Exception as e:
			self.logger.warning(f"Error extracting features for {session_date}: {e}")
			return None

	def _predict(
		self, model, feature_row: np.ndarray, feature_names: list, regime_names: dict
	) -> dict:
		"""Run model prediction."""
		# Convert to DataFrame with feature names to match training
		feature_df = pd.DataFrame(feature_row, columns=feature_names)
		y_pred = model.predict(feature_df)[0]
		y_proba = model.predict_proba(feature_df)[0]

		regime_id = int(y_pred)
		regime_name = regime_names.get(regime_id, f"Regime_{regime_id}")
		confidence = float(y_proba[regime_id])

		# Build probability dict
		probabilities = {}
		for regime_id_label, regime_name_label in regime_names.items():
			prob = float(y_proba[regime_id_label]) if regime_id_label < len(y_proba) else 0.0
			probabilities[f"{regime_id_label}_{regime_name_label}"] = prob

		return {
			"regime_id": regime_id,
			"regime_name": regime_name,
			"confidence": confidence,
			"probabilities": probabilities,
		}
