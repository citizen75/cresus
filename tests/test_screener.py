"""Tests for screener manager module."""

import csv
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.tools.screener import ScreenerConfig, ScreenerManager, ScreenerResult


class TestScreenerConfig:
	"""Test ScreenerConfig class."""

	def test_init_minimal(self):
		"""Test configuration creation with minimal parameters."""
		config = ScreenerConfig(
			name="test_screener",
			source="cac40",
			indicators=["rsi_14", "ema_20"],
			formula="rsi_14 > 50"
		)
		assert config.name == "test_screener"
		assert config.source == "cac40"
		assert config.indicators == ["rsi_14", "ema_20"]
		assert config.formula == "rsi_14 > 50"

	def test_init_with_tickers(self):
		"""Test configuration with explicit tickers."""
		tickers = ["AAPL", "MSFT", "GOOGL"]
		config = ScreenerConfig(
			name="tech_screener",
			tickers=tickers,
			indicators=["rsi_14"],
			formula="rsi_14 > 70"
		)
		assert config.tickers == tickers

	def test_init_with_actions(self):
		"""Test configuration with actions."""
		actions = {
			"alert": {"enabled": True, "channels": ["email"]},
			"notification": {"enabled": True}
		}
		config = ScreenerConfig(
			name="alert_screener",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 70",
			actions=actions
		)
		assert config.actions == actions

	def test_to_dict(self):
		"""Test converting configuration to dictionary."""
		config = ScreenerConfig(
			name="test",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50",
			description="Test screener"
		)
		data = config.to_dict()

		assert data["name"] == "test"
		assert data["source"] == "cac40"
		assert data["indicators"] == ["rsi_14"]
		assert data["formula"] == "rsi_14 > 50"
		assert data["description"] == "Test screener"

	def test_from_dict(self):
		"""Test creating configuration from dictionary."""
		data = {
			"name": "from_dict",
			"source": "nasdaq_100",
			"indicators": ["rsi_14", "macd"],
			"formula": "rsi_14 > 50 and macd > 0",
			"description": "Test from dict"
		}
		config = ScreenerConfig.from_dict(data)

		assert config.name == "from_dict"
		assert config.source == "nasdaq_100"
		assert config.indicators == ["rsi_14", "macd"]

	def test_validate_missing_name(self):
		"""Test validation fails without name."""
		config = ScreenerConfig(
			name="",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		is_valid, error = config.validate()
		assert not is_valid
		assert "name is required" in error

	def test_validate_missing_source_and_tickers(self):
		"""Test validation fails without source or tickers."""
		config = ScreenerConfig(
			name="test",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		is_valid, error = config.validate()
		assert not is_valid
		assert "source or tickers" in error

	def test_validate_missing_indicators(self):
		"""Test validation fails without indicators."""
		config = ScreenerConfig(
			name="test",
			source="cac40",
			formula="rsi_14 > 50"
		)
		is_valid, error = config.validate()
		assert not is_valid
		assert "indicator is required" in error

	def test_validate_missing_formula(self):
		"""Test validation fails without formula."""
		config = ScreenerConfig(
			name="test",
			source="cac40",
			indicators=["rsi_14"]
		)
		is_valid, error = config.validate()
		assert not is_valid
		assert "Formula is required" in error

	def test_validate_valid_config(self):
		"""Test validation passes for valid configuration."""
		config = ScreenerConfig(
			name="valid",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		is_valid, error = config.validate()
		assert is_valid
		assert error == ""

	def test_validate_valid_with_tickers(self):
		"""Test validation passes with tickers instead of source."""
		config = ScreenerConfig(
			name="valid",
			tickers=["AAPL", "MSFT"],
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		is_valid, error = config.validate()
		assert is_valid


class TestScreenerResult:
	"""Test ScreenerResult class."""

	def test_init(self):
		"""Test result creation."""
		ts = datetime.now()
		data = [{"ticker": "AAPL", "rsi": 75}]
		result = ScreenerResult("test_screener", "result_123", ts, data)

		assert result.screener_name == "test_screener"
		assert result.result_id == "result_123"
		assert result.timestamp == ts
		assert result.data == data

	def test_get_filename(self):
		"""Test getting result filename."""
		result = ScreenerResult("test", "20250115_103000_abc12345", datetime.now(), [])
		assert result.get_filename() == "20250115_103000_abc12345.csv"


class TestScreenerManager:
	"""Test ScreenerManager class."""

	@pytest.fixture
	def temp_db_path(self):
		"""Create temporary database path."""
		with tempfile.TemporaryDirectory() as tmpdir:
			yield Path(tmpdir)

	@pytest.fixture
	def manager(self, temp_db_path):
		"""Create a screener manager with temp path."""
		return ScreenerManager(db_path=temp_db_path)

	def test_init_sets_paths(self, temp_db_path):
		"""Test initialization sets correct paths."""
		manager = ScreenerManager(db_path=temp_db_path)
		assert manager.base_path == temp_db_path
		assert manager.screeners_path == temp_db_path / "screeners"

	def test_create_screener(self, manager):
		"""Test creating a new screener."""
		config = ScreenerConfig(
			name="my_screener",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		success, message = manager.create_screener(config)

		assert success
		assert "created successfully" in message
		assert manager._get_screener_dir("my_screener").exists()

	def test_create_screener_invalid_config(self, manager):
		"""Test creating screener with invalid config."""
		config = ScreenerConfig(name="invalid")
		success, message = manager.create_screener(config)

		assert not success
		assert "source or tickers" in message.lower()

	def test_create_screener_already_exists(self, manager):
		"""Test creating screener that already exists."""
		config = ScreenerConfig(
			name="duplicate",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)
		success, message = manager.create_screener(config)

		assert not success
		assert "already exists" in message

	def test_get_screener(self, manager):
		"""Test retrieving a screener configuration."""
		config = ScreenerConfig(
			name="test_screener",
			source="nasdaq_100",
			indicators=["rsi_14", "macd"],
			formula="rsi_14 > 50",
			description="Test description"
		)
		manager.create_screener(config)

		retrieved = manager.get_screener("test_screener")
		assert retrieved is not None
		assert retrieved.name == "test_screener"
		assert retrieved.source == "nasdaq_100"
		assert retrieved.indicators == ["rsi_14", "macd"]

	def test_get_screener_not_found(self, manager):
		"""Test retrieving non-existent screener."""
		result = manager.get_screener("nonexistent")
		assert result is None

	def test_list_screeners(self, manager):
		"""Test listing all screeners."""
		configs = [
			ScreenerConfig("screener1", source="cac40", indicators=["rsi_14"], formula="rsi_14 > 50"),
			ScreenerConfig("screener2", source="nasdaq_100", indicators=["rsi_14"], formula="rsi_14 > 70"),
			ScreenerConfig("screener3", tickers=["AAPL"], indicators=["rsi_14"], formula="rsi_14 > 50"),
		]

		for config in configs:
			manager.create_screener(config)

		screeners = manager.list_screeners()
		assert len(screeners) == 3
		assert "screener1" in screeners
		assert "screener2" in screeners
		assert "screener3" in screeners
		assert screeners == sorted(screeners)

	def test_list_screeners_empty(self, manager):
		"""Test listing screeners when none exist."""
		screeners = manager.list_screeners()
		assert screeners == []

	def test_update_screener(self, manager):
		"""Test updating a screener."""
		original = ScreenerConfig(
			name="to_update",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(original)

		updated = ScreenerConfig(
			name="to_update",
			source="nasdaq_100",
			indicators=["rsi_14", "macd"],
			formula="rsi_14 > 50 and macd > 0"
		)
		success, message = manager.update_screener(updated)

		assert success
		assert "updated successfully" in message

		retrieved = manager.get_screener("to_update")
		assert retrieved.source == "nasdaq_100"
		assert retrieved.indicators == ["rsi_14", "macd"]

	def test_update_nonexistent_screener(self, manager):
		"""Test updating non-existent screener."""
		config = ScreenerConfig(
			name="nonexistent",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		success, message = manager.update_screener(config)

		assert not success
		assert "not found" in message

	def test_delete_screener(self, manager):
		"""Test deleting a screener."""
		config = ScreenerConfig(
			name="to_delete",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)
		assert manager._get_screener_dir("to_delete").exists()

		success, message = manager.delete_screener("to_delete")
		assert success
		assert "deleted successfully" in message
		assert not manager._get_screener_dir("to_delete").exists()

	def test_delete_nonexistent_screener(self, manager):
		"""Test deleting non-existent screener."""
		success, message = manager.delete_screener("nonexistent")
		assert not success
		assert "not found" in message

	def test_save_result(self, manager):
		"""Test saving screening results."""
		config = ScreenerConfig(
			name="result_screener",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)

		data = [
			{"ticker": "AAPL", "rsi": 75, "price": 150.5},
			{"ticker": "MSFT", "rsi": 72, "price": 300.2},
		]

		success, message, result_id = manager.save_result("result_screener", data)

		assert success
		assert "2 matches" in message
		assert result_id is not None
		assert (manager._get_results_dir("result_screener") / f"{result_id}.csv").exists()

	def test_save_result_empty_data(self, manager):
		"""Test saving empty results."""
		config = ScreenerConfig(
			name="empty_screener",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)

		success, message, result_id = manager.save_result("empty_screener", [])

		assert success
		assert "0 matches" in message
		assert result_id is not None

	def test_save_result_nonexistent_screener(self, manager):
		"""Test saving results for non-existent screener."""
		data = [{"ticker": "AAPL", "rsi": 75}]
		success, message, result_id = manager.save_result("nonexistent", data)

		assert not success
		assert "not found" in message
		assert result_id is None

	def test_get_result(self, manager):
		"""Test retrieving screening results."""
		config = ScreenerConfig(
			name="read_screener",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)

		original_data = [
			{"ticker": "AAPL", "rsi": "75"},
			{"ticker": "MSFT", "rsi": "72"},
		]

		_, _, result_id = manager.save_result("read_screener", original_data)

		retrieved = manager.get_result("read_screener", result_id)
		assert retrieved is not None
		assert len(retrieved) == 2
		assert retrieved[0]["ticker"] == "AAPL"

	def test_get_result_not_found(self, manager):
		"""Test retrieving non-existent result."""
		config = ScreenerConfig(
			name="test",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)

		result = manager.get_result("test", "nonexistent")
		assert result is None

	def test_list_results(self, manager):
		"""Test listing screener results."""
		config = ScreenerConfig(
			name="list_screener",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)

		# Save multiple results
		for i in range(3):
			data = [{"ticker": f"TICKER{i}", "rsi": 75 + i}]
			manager.save_result("list_screener", data)

		results = manager.list_results("list_screener")
		assert len(results) == 3

		# Check results are sorted by timestamp (newest first)
		for i in range(len(results) - 1):
			assert results[i][1] >= results[i + 1][1]

	def test_list_results_empty(self, manager):
		"""Test listing results when none exist."""
		config = ScreenerConfig(
			name="empty_list",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)

		results = manager.list_results("empty_list")
		assert results == []

	def test_delete_result(self, manager):
		"""Test deleting a result."""
		config = ScreenerConfig(
			name="delete_screener",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)

		data = [{"ticker": "AAPL", "rsi": 75}]
		_, _, result_id = manager.save_result("delete_screener", data)

		success, message = manager.delete_result("delete_screener", result_id)

		assert success
		assert "deleted successfully" in message
		assert (manager._get_results_dir("delete_screener") / f"{result_id}.csv").exists() is False

	def test_delete_nonexistent_result(self, manager):
		"""Test deleting non-existent result."""
		success, message = manager.delete_result("nonexistent", "result123")
		assert not success
		assert "not found" in message

	def test_clear_results(self, manager):
		"""Test clearing all results."""
		config = ScreenerConfig(
			name="clear_screener",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)

		# Save multiple results
		for i in range(3):
			data = [{"ticker": f"TICKER{i}", "rsi": 75}]
			manager.save_result("clear_screener", data)

		results_before = manager.list_results("clear_screener")
		assert len(results_before) == 3

		success, message = manager.clear_results("clear_screener")

		assert success
		results_after = manager.list_results("clear_screener")
		assert len(results_after) == 0

	def test_clear_results_nonexistent(self, manager):
		"""Test clearing results when directory doesn't exist."""
		success, message = manager.clear_results("nonexistent")
		assert success
		assert "No results" in message

	def test_result_id_format(self, manager):
		"""Test result ID follows the expected format."""
		result_id = ScreenerManager._generate_result_id()

		# Format: YYYYmmdd_HHMMSS_8char_uuid
		parts = result_id.split("_")
		assert len(parts) == 3
		assert len(parts[0]) == 8  # Date part
		assert len(parts[1]) == 6  # Time part
		assert len(parts[2]) == 8  # UUID part

	def test_config_persists_to_yaml(self, manager, temp_db_path):
		"""Test that configuration is saved as valid YAML."""
		config = ScreenerConfig(
			name="yaml_test",
			source="cac40",
			indicators=["rsi_14", "macd"],
			formula="rsi_14 > 50 and macd > 0",
			description="YAML test",
			actions={"alert": {"enabled": True}}
		)
		manager.create_screener(config)

		config_file = temp_db_path / "screeners" / "yaml_test" / "screener.yml"
		assert config_file.exists()

		# Verify it's valid YAML
		import yaml
		with open(config_file, "r") as f:
			data = yaml.safe_load(f)
			assert data["name"] == "yaml_test"
			assert data["source"] == "cac40"
			assert data["formula"] == "rsi_14 > 50 and macd > 0"

	def test_result_csv_format(self, manager):
		"""Test that results are saved as valid CSV."""
		config = ScreenerConfig(
			name="csv_test",
			source="cac40",
			indicators=["rsi_14"],
			formula="rsi_14 > 50"
		)
		manager.create_screener(config)

		data = [
			{"ticker": "AAPL", "rsi": "75.5", "signal": "strong_buy"},
			{"ticker": "MSFT", "rsi": "72.0", "signal": "buy"},
		]

		_, _, result_id = manager.save_result("csv_test", data)
		result_file = manager._get_results_dir("csv_test") / f"{result_id}.csv"

		# Verify CSV format
		with open(result_file, "r") as f:
			reader = csv.DictReader(f)
			rows = list(reader)
			assert len(rows) == 2
			assert rows[0]["ticker"] == "AAPL"
			assert rows[1]["signal"] == "buy"
