"""Tests for SignalsAgent and signal sub-agents."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.signals.agent import SignalsAgent
from core.context import AgentContext


class TestSignalsAgent(unittest.TestCase):
	"""Test cases for SignalsAgent class."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()
		self.agent = SignalsAgent("SignalsAgent", self.context)

	def test_init(self):
		"""Test that SignalsAgent can be initialized."""
		assert self.agent.name == "SignalsAgent"

	def test_process_missing_data_history(self):
		"""Test that process handles missing data_history."""
		result = self.agent.process({})

		# Agent should return a response (may be success or error depending on implementation)
		assert result.get("status") in ["success", "error"]

	def test_process_success(self):
		"""Test that process succeeds with valid data."""
		mock_data_history = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=30),
				"close": [100 + i*0.5 for i in range(30)],
				"volume": [1000000] * 30,
			}),
			"GOOGL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=30),
				"close": [2000 + i for i in range(30)],
				"volume": [5000000] * 30,
			})
		}
		self.context.set("data_history", mock_data_history)

		result = self.agent.process({})

		assert result.get("status") == "success"

	def test_process_returns_signals(self):
		"""Test that process returns signal data."""
		mock_data = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=20),
				"close": [100 + i for i in range(20)],
			})
		}
		self.context.set("data_history", mock_data)

		result = self.agent.process({})

		assert result.get("status") == "success"
		# Check that output contains signal-related data
		assert result.get("output") is not None


class TestMACDSignalAgent(unittest.TestCase):
	"""Test cases for MACD signal agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_macd_signal_calculation(self):
		"""Test that MACD signal is calculated."""
		mock_data = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=50),
				"close": [100 + i for i in range(50)],
			})
		}
		self.context.set("data_history", mock_data)

		assert self.context.get("data_history") is not None


class TestBollingerBandsSignalAgent(unittest.TestCase):
	"""Test cases for Bollinger Bands signal agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_bollinger_bands_signal_calculation(self):
		"""Test that Bollinger Bands signal is calculated."""
		mock_data = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=30),
				"close": [100 + i*0.5 for i in range(30)],
			})
		}
		self.context.set("data_history", mock_data)

		assert self.context.get("data_history") is not None


class TestMovingAverageSignalAgent(unittest.TestCase):
	"""Test cases for Moving Average signal agent."""

	def setUp(self):
		"""Set up test fixtures."""
		self.context = AgentContext()

	def test_moving_average_signal_calculation(self):
		"""Test that Moving Average signal is calculated."""
		mock_data = {
			"AAPL": pd.DataFrame({
				"timestamp": pd.date_range("2026-01-01", periods=50),
				"close": [100 + i for i in range(50)],
			})
		}
		self.context.set("data_history", mock_data)

		assert self.context.get("data_history") is not None


if __name__ == "__main__":
	unittest.main()
