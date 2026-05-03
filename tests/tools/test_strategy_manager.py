"""Tests for StrategyManager."""

import pytest
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.strategy.strategy import StrategyManager


class TestStrategyManager:
	"""Test cases for StrategyManager class."""

	@pytest.fixture
	def temp_project(self):
		"""Create a temporary project directory."""
		with TemporaryDirectory() as tmpdir:
			project_root = Path(tmpdir)
			(project_root / "db" / "local").mkdir(parents=True, exist_ok=True)
			yield project_root

	@pytest.fixture
	def manager(self, temp_project):
		"""Create a StrategyManager with temporary project."""
		return StrategyManager(project_root=temp_project)

	def test_manager_initialization(self, manager):
		"""Test that StrategyManager initializes correctly."""
		assert manager.strategies_dir.exists()
		assert manager.strategies_dir.name == "strategies"

	def test_manager_creates_directory_on_init(self, temp_project):
		"""Test that StrategyManager creates strategies directory."""
		strategies_dir = temp_project / "db" / "local" / "strategies"
		assert not strategies_dir.exists()

		manager = StrategyManager(project_root=temp_project)

		assert strategies_dir.exists()

	def test_save_strategy(self, manager):
		"""Test saving a strategy."""
		strategy_data = {
			"name": "test_strategy",
			"description": "Test strategy",
			"source": "cac40",
			"agents": {"StrategyAgent": {}},
		}

		result = manager.save_strategy("test_strategy", strategy_data)

		assert result.get("status") == "success"
		assert result.get("file") is not None

	def test_load_strategy(self, manager):
		"""Test loading a saved strategy."""
		strategy_data = {
			"name": "test_strategy",
			"description": "Test strategy",
			"source": "cac40",
			"agents": {"StrategyAgent": {}},
		}

		manager.save_strategy("test_strategy", strategy_data)
		result = manager.load_strategy("test_strategy")

		assert result.get("status") == "success"
		assert result.get("data") == strategy_data
		assert result.get("name") == "test_strategy"

	def test_load_nonexistent_strategy(self, manager):
		"""Test loading a strategy that doesn't exist."""
		result = manager.load_strategy("nonexistent")

		assert result.get("status") == "error"
		assert "not found" in result.get("message", "").lower()

	def test_delete_strategy(self, manager):
		"""Test deleting a strategy."""
		strategy_data = {"name": "to_delete", "source": "test"}

		manager.save_strategy("to_delete", strategy_data)
		result = manager.delete_strategy("to_delete")

		assert result.get("status") == "success"

		# Verify it's actually deleted
		load_result = manager.load_strategy("to_delete")
		assert load_result.get("status") == "error"

	def test_delete_nonexistent_strategy(self, manager):
		"""Test deleting a non-existent strategy."""
		result = manager.delete_strategy("nonexistent")

		assert result.get("status") == "error"

	def test_list_strategies(self, manager):
		"""Test listing all strategies."""
		# Save multiple strategies
		strategies = [
			{"name": "strategy1", "source": "cac40"},
			{"name": "strategy2", "source": "nasdaq"},
			{"name": "strategy3", "source": "cac40"},
		]

		for strategy in strategies:
			manager.save_strategy(strategy["name"], strategy)

		result = manager.list_strategies()

		assert result.get("status") == "success"
		assert result.get("total_count") == 3
		assert len(result.get("strategies", [])) == 3

	def test_list_strategies_empty(self, manager):
		"""Test listing strategies when none exist."""
		result = manager.list_strategies()

		assert result.get("status") == "success"
		assert result.get("total_count") == 0
		assert result.get("strategies") == []

	def test_get_strategy_by_source(self, manager):
		"""Test filtering strategies by source."""
		strategies = [
			{"name": "cac_strategy1", "source": "cac40"},
			{"name": "cac_strategy2", "source": "cac40"},
			{"name": "nasdaq_strategy", "source": "nasdaq"},
		]

		for strategy in strategies:
			manager.save_strategy(strategy["name"], strategy)

		result = manager.get_strategy_by_source("cac40")

		assert result.get("status") == "success"
		assert result.get("total_count") == 2
		assert result.get("source") == "cac40"

	def test_get_strategy_by_source_not_found(self, manager):
		"""Test filtering strategies by source when none match."""
		result = manager.get_strategy_by_source("nonexistent_source")

		assert result.get("status") == "success"
		assert result.get("total_count") == 0

	def test_find_strategy_by_name(self, manager):
		"""Test finding a strategy by name."""
		strategy_data = {"name": "find_me", "source": "test"}

		manager.save_strategy("find_me", strategy_data)
		result = manager.find_strategy_by_name("find_me")

		assert result.get("status") == "success"
		assert result.get("name") == "find_me"

	def test_get_agent_config(self, manager):
		"""Test extracting agent configuration."""
		strategy_data = {
			"name": "strategy_with_agents",
			"source": "test",
			"agents": {
				"Agent1": {"param1": "value1"},
				"Agent2": {"param2": "value2"},
			},
		}

		manager.save_strategy("strategy_with_agents", strategy_data)
		result = manager.get_agent_config("strategy_with_agents", "Agent1")

		assert result.get("status") == "success"
		assert result.get("agent") == "Agent1"
		assert result.get("config") == {"param1": "value1"}

	def test_get_agent_config_not_found(self, manager):
		"""Test getting agent config when agent doesn't exist."""
		strategy_data = {
			"name": "test",
			"source": "test",
			"agents": {"Agent1": {}},
		}

		manager.save_strategy("test", strategy_data)
		result = manager.get_agent_config("test", "NonexistentAgent")

		assert result.get("status") == "error"

	def test_validate_strategy_config_valid(self, manager):
		"""Test validating a valid strategy."""
		strategy_data = {
			"name": "valid_strategy",
			"source": "cac40",
			"agents": {"Agent": {}},
		}

		manager.save_strategy("valid_strategy", strategy_data)
		result = manager.validate_strategy_config("valid_strategy")

		assert result.get("status") == "success"
		assert result.get("valid") is True
		assert result.get("issue_count") == 0

	def test_validate_strategy_config_invalid(self, manager):
		"""Test validating an invalid strategy (missing fields)."""
		strategy_data = {"name": "incomplete_strategy"}

		manager.save_strategy("incomplete_strategy", strategy_data)
		result = manager.validate_strategy_config("incomplete_strategy")

		assert result.get("status") == "success"
		assert result.get("valid") is False
		assert result.get("issue_count") > 0

	def test_save_strategy_adds_name(self, manager):
		"""Test that save_strategy adds name if missing."""
		strategy_data = {"source": "test"}

		manager.save_strategy("my_strategy", strategy_data)
		result = manager.load_strategy("my_strategy")

		assert result.get("data").get("name") == "my_strategy"

	def test_save_strategy_overwrites(self, manager):
		"""Test that saving overwrites existing strategy."""
		strategy_data_v1 = {"name": "test", "version": "1"}
		strategy_data_v2 = {"name": "test", "version": "2"}

		manager.save_strategy("test", strategy_data_v1)
		result1 = manager.load_strategy("test")
		assert result1.get("data").get("version") == "1"

		manager.save_strategy("test", strategy_data_v2)
		result2 = manager.load_strategy("test")
		assert result2.get("data").get("version") == "2"

	def test_strategy_file_format_is_json(self, manager):
		"""Test that strategies are stored as JSON."""
		strategy_data = {"name": "json_test", "source": "test"}

		manager.save_strategy("json_test", strategy_data)

		strategy_file = manager._get_strategy_file("json_test")
		with open(strategy_file, "r") as f:
			content = json.load(f)

		assert content == strategy_data

	def test_list_strategies_includes_metadata(self, manager):
		"""Test that list_strategies includes metadata."""
		strategy_data = {
			"name": "meta_test",
			"description": "Test description",
			"source": "cac40",
		}

		manager.save_strategy("meta_test", strategy_data)
		result = manager.list_strategies()

		strategy_item = result.get("strategies")[0]
		assert strategy_item.get("name") == "meta_test"
		assert strategy_item.get("description") == "Test description"
		assert strategy_item.get("source") == "cac40"
		assert "file" in strategy_item
		assert "modified" in strategy_item

	def test_multiple_strategies_isolation(self, manager):
		"""Test that multiple strategies don't interfere."""
		s1 = {"name": "s1", "data": "value1"}
		s2 = {"name": "s2", "data": "value2"}

		manager.save_strategy("s1", s1)
		manager.save_strategy("s2", s2)

		r1 = manager.load_strategy("s1")
		r2 = manager.load_strategy("s2")

		assert r1.get("data").get("data") == "value1"
		assert r2.get("data").get("data") == "value2"

	def test_strategies_dir_attribute(self, manager):
		"""Test that strategies_dir attribute is correct."""
		assert manager.strategies_dir.name == "strategies"
		assert "db" in manager.strategies_dir.parts
		assert "local" in manager.strategies_dir.parts

	def test_save_complex_strategy(self, manager):
		"""Test saving a complex nested strategy."""
		strategy_data = {
			"name": "complex",
			"source": "nasdaq",
			"description": "Complex strategy",
			"agents": {
				"Agent1": {
					"config": {
						"nested": {
							"deep": {
								"value": "test",
								"list": [1, 2, 3],
							}
						}
					}
				}
			},
			"parameters": {
				"thresholds": [10, 20, 30],
				"mapping": {"a": 1, "b": 2},
			},
		}

		manager.save_strategy("complex", strategy_data)
		result = manager.load_strategy("complex")

		assert result.get("status") == "success"
		assert result.get("data") == strategy_data

	def test_get_strategy_by_source_multiple_results(self, manager):
		"""Test get_strategy_by_source with multiple matching strategies."""
		strategies = [
			{"name": "s1", "source": "test_source", "version": 1},
			{"name": "s2", "source": "test_source", "version": 2},
			{"name": "s3", "source": "test_source", "version": 3},
			{"name": "s4", "source": "other_source"},
		]

		for s in strategies:
			manager.save_strategy(s["name"], s)

		result = manager.get_strategy_by_source("test_source")

		assert result.get("total_count") == 3
		names = [s["name"] for s in result.get("strategies", [])]
		assert "s1" in names
		assert "s2" in names
		assert "s3" in names
		assert "s4" not in names
