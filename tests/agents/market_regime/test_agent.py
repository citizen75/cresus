"""Tests for MarketRegimeAgent."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import tempfile
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.market_regime.agent import MarketRegimeAgent
from core.context import AgentContext


class TestMarketRegimeAgent(unittest.TestCase):
	"""Test cases for MarketRegimeAgent class."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = MarketRegimeAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that MarketRegimeAgent can be initialized."""
		agent = MarketRegimeAgent()
		assert agent.name == "MarketRegimeAgent"
		assert hasattr(agent, "REGIME_NAMES")
		assert len(agent.REGIME_NAMES) == 6

	def test_regime_names_constant(self):
		"""Test that REGIME_NAMES has all 6 regimes."""
		assert len(self.agent.REGIME_NAMES) == 6
		assert 0 in self.agent.REGIME_NAMES
		assert self.agent.REGIME_NAMES[0] == "Strong_Bull"
		assert self.agent.REGIME_NAMES[5] == "Crisis_Volatile"

	def test_process_missing_universe(self):
		"""Test that process returns error when universe missing."""
		result = self.agent.process({})

		assert result.get("status") == "error"
		assert "universe parameter required" in result.get("message", "")

	def test_process_train_action(self):
		"""Test process with train action."""
		with patch("agents.market_regime.agent.Flow") as mock_flow_class:
			mock_flow = MagicMock()
			mock_flow.process.return_value = {"status": "success"}
			mock_flow_class.return_value = mock_flow

			with patch.object(self.agent, "_build_train_flow", return_value=mock_flow):
				with patch.object(self.agent, "_load_or_create_config", return_value={}):
					with patch.object(self.agent, "_format_train_result") as mock_format:
						mock_format.return_value = {
							"status": "success",
							"output": {"model_path": "/path/to/model.pkl"}
						}

						result = self.agent.process({
							"universe": "cac40",
							"action": "train"
						})

						assert result.get("status") == "success"
						mock_flow.process.assert_called_once()

	def test_process_predict_action(self):
		"""Test process with predict action."""
		with patch("agents.market_regime.agent.Flow") as mock_flow_class:
			mock_flow = MagicMock()
			mock_flow.process.return_value = {"status": "success"}
			mock_flow_class.return_value = mock_flow

			with patch.object(self.agent, "_build_predict_flow", return_value=mock_flow):
				with patch.object(self.agent, "_load_or_create_config", return_value={}):
					with patch.object(self.agent, "_format_predict_result") as mock_format:
						mock_format.return_value = {
							"status": "success",
							"output": {"regime_id": 0, "regime_name": "Strong_Bull"}
						}

						result = self.agent.process({
							"universe": "nasdaq_100",
							"action": "predict"
						})

						assert result.get("status") == "success"
						mock_flow.process.assert_called_once()

	def test_process_default_action_is_predict(self):
		"""Test that default action is predict."""
		with patch("agents.market_regime.agent.Flow") as mock_flow_class:
			mock_flow = MagicMock()
			mock_flow.process.return_value = {"status": "success"}
			mock_flow_class.return_value = mock_flow

			with patch.object(self.agent, "_build_predict_flow", return_value=mock_flow):
				with patch.object(self.agent, "_load_or_create_config", return_value={}):
					with patch.object(self.agent, "_format_predict_result") as mock_format:
						mock_format.return_value = {"status": "success"}

						result = self.agent.process({"universe": "etf_pea"})

						# Should use predict flow when action not specified
						mock_flow.process.assert_called_once()

	def test_process_stores_in_context(self):
		"""Test that process stores config and input in context."""
		mock_config = {"universe": "cac40", "model_path": "/path/model.pkl"}

		with patch("agents.market_regime.agent.Flow") as mock_flow_class:
			mock_flow = MagicMock()
			mock_flow.process.return_value = {"status": "success"}
			mock_flow_class.return_value = mock_flow

			with patch.object(self.agent, "_build_predict_flow", return_value=mock_flow):
				with patch.object(self.agent, "_load_or_create_config", return_value=mock_config):
					with patch.object(self.agent, "_format_predict_result") as mock_format:
						mock_format.return_value = {"status": "success"}

						self.agent.process({
							"universe": "cac40",
							"action": "predict",
							"lookback_days": 100
						})

						# Verify context was set
						assert self.context.get("regime_config") == mock_config
						assert self.context.get("regime_input") is not None

	def test_load_or_create_config_creates_default(self):
		"""Test that config is created with defaults if not exists."""
		with tempfile.TemporaryDirectory() as tmpdir:
			with patch("agents.market_regime.agent.get_db_root") as mock_db_root:
				mock_db_root.return_value = Path(tmpdir)

				config = self.agent._load_or_create_config("test_universe")

				# Verify default config structure
				assert "universe" in config
				assert "features" in config
				assert "training" in config
				assert "lgbm_params" in config
				assert len(config["features"]) == 13

	def test_load_or_create_config_loads_existing(self):
		"""Test that config loads from file if exists."""
		with tempfile.TemporaryDirectory() as tmpdir:
			# Create a config file
			regimes_dir = Path(tmpdir) / "regimes"
			regimes_dir.mkdir(parents=True, exist_ok=True)
			config_path = regimes_dir / "test_universe.yml"

			test_config = {
				"universe": "test_universe",
				"model_path": "/custom/path.pkl",
				"features": ["custom_feature"],
			}

			with open(config_path, "w") as f:
				yaml.dump(test_config, f)

			with patch("agents.market_regime.agent.get_db_root") as mock_db_root:
				mock_db_root.return_value = Path(tmpdir)

				config = self.agent._load_or_create_config("test_universe")

				assert config["model_path"] == "/custom/path.pkl"
				assert "custom_feature" in config["features"]

	def test_get_default_config(self):
		"""Test default config generation."""
		with patch("agents.market_regime.agent.get_db_root") as mock_db_root:
			mock_db_root.return_value = Path("/tmp/db")

			config = self.agent._get_default_config("cac40")

			assert config["universe"] == "cac40"
			assert "model_path" in config
			assert config["model_path"].endswith("cac40_regime.pkl")
			assert config["training"]["lookback_days"] == 1000
			assert config["training"]["n_regimes"] == 6
			assert len(config["features"]) == 13

	def test_format_train_result(self):
		"""Test formatting of training result."""
		import pandas as pd
		import numpy as np

		# Setup context with training data
		labels_series = pd.Series([0, 1, 2, 0, 1], index=range(5))
		prices_df = pd.DataFrame({
			"close": [100, 101, 102, 103, 104]
		}, index=pd.date_range("2026-01-01", periods=5))

		training_result = {
			"model_path": "/path/model.pkl",
			"n_samples_train": 40,
			"n_samples_test": 10,
			"n_features": 13,
			"metrics": {
				"accuracy": 0.85,
				"f1_macro": 0.82,
				"f1_weighted": 0.83,
				"per_class_f1": {0: 0.8, 1: 0.8, 2: 0.8},
				"feature_importance": {"feat1": 0.5, "feat2": 0.3, "feat3": 0.2}
			}
		}

		self.context.set("training_result", training_result)
		self.context.set("labels_series", labels_series)
		self.context.set("prices_df", prices_df)

		config = self.agent._get_default_config("cac40")

		result = self.agent._format_train_result({}, "cac40", config)

		assert result["status"] == "success"
		assert result["output"]["action"] == "train"
		assert result["output"]["universe"] == "cac40"
		assert "regime_distribution" in result["output"]
		assert len(result["output"]["top_features"]) <= 5

	def test_format_predict_result(self):
		"""Test formatting of prediction result."""
		prediction_result = {
			"regime_id": 2,
			"regime_name": "Neutral_Sideways",
			"confidence": 0.75,
			"probabilities": {0: 0.1, 1: 0.15, 2: 0.75, 3: 0.0, 4: 0.0, 5: 0.0}
		}

		config = {"model_path": "/path/model.pkl"}

		self.context.set("prediction_result", prediction_result)
		self.context.set("regime_config", config)

		result = self.agent._format_predict_result({}, "cac40")

		assert result["status"] == "success"
		assert result["output"]["action"] == "predict"
		assert result["output"]["regime_id"] == 2
		assert result["output"]["regime_name"] == "Neutral_Sideways"
		assert result["output"]["confidence"] == 0.75

	def test_build_train_flow(self):
		"""Test that train flow is built with correct agents."""
		config = self.agent._get_default_config("cac40")
		flow = self.agent._build_train_flow(config)

		assert flow is not None
		assert flow.context is self.context

	def test_build_predict_flow(self):
		"""Test that predict flow is built with correct agents."""
		config = self.agent._get_default_config("cac40")
		flow = self.agent._build_predict_flow(config)

		assert flow is not None
		assert flow.context is self.context

	def test_process_with_lookback_days(self):
		"""Test that lookback_days is passed to context."""
		with patch("agents.market_regime.agent.Flow") as mock_flow_class:
			mock_flow = MagicMock()
			mock_flow.process.return_value = {"status": "success"}
			mock_flow_class.return_value = mock_flow

			with patch.object(self.agent, "_build_predict_flow", return_value=mock_flow):
				with patch.object(self.agent, "_load_or_create_config", return_value={}):
					with patch.object(self.agent, "_format_predict_result") as mock_format:
						mock_format.return_value = {"status": "success"}

						self.agent.process({
							"universe": "cac40",
							"lookback_days": 500
						})

						regime_input = self.context.get("regime_input")
						assert regime_input["lookback_days"] == 500

	def test_process_error_handling(self):
		"""Test that exceptions are handled gracefully."""
		with patch.object(self.agent, "_load_or_create_config", side_effect=Exception("Test error")):
			result = self.agent.process({"universe": "cac40"})

			assert result["status"] == "error"
			assert "Market regime detection failed" in result["message"]


if __name__ == "__main__":
	unittest.main()
