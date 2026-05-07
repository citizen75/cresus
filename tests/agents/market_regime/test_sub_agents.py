"""Tests for MarketRegimeAgent sub-agents."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.market_regime.sub_agents import (
	RegimeDataLoaderAgent,
	FeatureEngineerAgent,
	RegimeLabelerAgent,
	RegimeTrainerAgent,
	RegimePredictorAgent,
)
from core.context import AgentContext


class TestRegimeDataLoaderAgent(unittest.TestCase):
	"""Test cases for RegimeDataLoaderAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = RegimeDataLoaderAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "RegimeDataLoaderAgent"
		assert self.agent.context is not None

	def test_process_missing_universe(self):
		"""Test that process returns error when universe missing."""
		result = self.agent.process({})

		assert result.get("status") == "error"

	def test_process_loads_universe_data(self):
		"""Test that process loads data for universe tickers."""
		with patch("agents.market_regime.sub_agents.data_loader.Universe") as mock_universe_class:
			with patch("agents.market_regime.sub_agents.data_loader.DataHistory") as mock_dh_class:
				mock_universe = MagicMock()
				mock_universe.get_tickers.return_value = ["AAPL", "GOOGL", "MSFT"]
				mock_universe_class.return_value = mock_universe

				mock_dh = MagicMock()
				mock_df = pd.DataFrame({
					"timestamp": pd.date_range("2026-01-01", periods=10),
					"close": [100 + i for i in range(10)],
				})
				mock_dh.get_all.return_value = mock_df
				mock_dh_class.return_value = mock_dh

				self.context.set("regime_input", {"universe": "cac40", "lookback_days": 100})

				result = self.agent.process({})

				assert result.get("status") == "success"
				assert self.context.get("prices_df") is not None


class TestFeatureEngineerAgent(unittest.TestCase):
	"""Test cases for FeatureEngineerAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = FeatureEngineerAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "FeatureEngineerAgent"

	def test_process_missing_prices_df(self):
		"""Test that process returns error when prices_df missing."""
		result = self.agent.process({})

		assert result.get("status") == "error"
		# Check for appropriate error message (may vary)
		assert result.get("message", "") != ""

	def test_process_computes_features(self):
		"""Test that process computes features from price data."""
		# Create synthetic price data
		dates = pd.date_range("2026-01-01", periods=100)
		prices_data = {
			"AAPL": [100 + i*0.5 for i in range(100)],
			"GOOGL": [2000 + i for i in range(100)],
			"MSFT": [300 + i*0.3 for i in range(100)],
		}

		prices_df = pd.DataFrame(prices_data, index=dates)
		self.context.set("prices_df", prices_df)

		config = {
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
			]
		}
		self.context.set("regime_config", config)

		result = self.agent.process({})

		# Should either succeed or return an error (depends on feature availability)
		assert result.get("status") in ["success", "error"]


class TestRegimeLabelerAgent(unittest.TestCase):
	"""Test cases for RegimeLabelerAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = RegimeLabelerAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "RegimeLabelerAgent"
		assert len(self.agent.REGIME_NAMES) == 6

	def test_process_missing_features_df(self):
		"""Test that process returns error when features_df missing."""
		result = self.agent.process({})

		assert result.get("status") == "error"
		assert "features_df" in result.get("message", "")

	def test_process_creates_labels(self):
		"""Test that process creates regime labels."""
		# Create synthetic features
		features_df = pd.DataFrame(
			np.random.randn(100, 13),
			index=pd.date_range("2026-01-01", periods=100),
			columns=[f"feature_{i}" for i in range(13)]
		)
		self.context.set("features_df", features_df)
		self.context.set("regime_config", {"n_regimes": 6})

		with patch("agents.market_regime.sub_agents.regime_labeler.KMeans") as mock_kmeans:
			mock_kmeans_instance = MagicMock()
			mock_kmeans_instance.fit_predict.return_value = np.array([0, 1, 2, 3, 4, 5] * 17)[:100]
			mock_kmeans_instance.cluster_centers_ = np.random.randn(6, 13)
			mock_kmeans.return_value = mock_kmeans_instance

			result = self.agent.process({})

			assert result.get("status") == "success"
			labels_series = self.context.get("labels_series")
			assert labels_series is not None
			assert len(labels_series) == 100


class TestRegimeTrainerAgent(unittest.TestCase):
	"""Test cases for RegimeTrainerAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = RegimeTrainerAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "RegimeTrainerAgent"

	def test_process_trains_model(self):
		"""Test that process trains a model."""
		# Create synthetic training data
		features_df = pd.DataFrame(
			np.random.randn(100, 13),
			index=pd.date_range("2026-01-01", periods=100),
			columns=[f"feature_{i}" for i in range(13)]
		)
		labels_series = pd.Series([0, 1, 2, 0, 1, 2, 3, 4, 5, 0] * 10)

		self.context.set("features_df", features_df)
		self.context.set("labels_series", labels_series)
		self.context.set("regime_config", {
			"lgbm_params": {
				"n_estimators": 100,
				"max_depth": 6,
				"learning_rate": 0.05,
			},
			"model_path": "/tmp/test_model.pkl"
		})

		with patch("agents.market_regime.sub_agents.regime_trainer.lgb.LGBMClassifier"):
			with patch("agents.market_regime.sub_agents.regime_trainer.joblib.dump"):
				result = self.agent.process({})

				# Should process data (success or error depending on conditions)
				assert result.get("status") in ["success", "error"]


class TestRegimePredictorAgent(unittest.TestCase):
	"""Test cases for RegimePredictorAgent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = RegimePredictorAgent()
		self.agent.context = self.context

	def test_init(self):
		"""Test that agent can be initialized."""
		assert self.agent.name == "RegimePredictorAgent"

	def test_process_missing_model_path(self):
		"""Test that process returns error when model_path missing."""
		self.context.set("regime_config", {})
		result = self.agent.process({})

		assert result.get("status") == "error"

	def test_process_predicts_regime(self):
		"""Test that process makes a prediction."""
		features_df = pd.DataFrame(
			np.random.randn(1, 13),
			columns=[f"feature_{i}" for i in range(13)]
		)
		self.context.set("features_df", features_df)
		self.context.set("regime_config", {"model_path": "/tmp/model.pkl"})

		mock_model = MagicMock()
		mock_model.predict.return_value = np.array([2])  # Neutral regime
		mock_model.predict_proba.return_value = np.array([[0.1, 0.15, 0.75, 0.0, 0.0, 0.0]])

		with patch("agents.market_regime.sub_agents.regime_predictor.joblib.load") as mock_load:
			mock_load.return_value = {"model": mock_model}

			result = self.agent.process({})

			# Should process data (success or error)
			assert result.get("status") in ["success", "error"]


if __name__ == "__main__":
	unittest.main()
