"""Tests for StrategyManager."""

import pytest
import json
import yaml
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
		"""Create a temporary project directory with template."""
		with TemporaryDirectory() as tmpdir:
			project_root = Path(tmpdir)
			(project_root / "db" / "local").mkdir(parents=True, exist_ok=True)

			# Create template directory and file
			template_dir = project_root / "init" / "templates"
			template_dir.mkdir(parents=True, exist_ok=True)

			template_data = {
				"name": "template_name",
				"universe": "cac40",
				"description": "Strategy description",
				"engine": "TaModel",
				"indicators": [],
				"watchlist": {"enabled": True, "parameters": {}},
				"signals": {"enabled": True, "weights": {}, "parameters": {}},
				"entry": {
					"enabled": True,
					"parameters": {
						"position_size": {"formula": "1000"},
						"entry_filter": {"formula": "close[0] > ema_10[0]", "description": "Entry filter"},
					}
				},
				"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
				"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
				"backtest": {"initial_capital": 10000},
			}

			template_file = template_dir / "strategy.yml"
			with open(template_file, "w") as f:
				yaml.dump(template_data, f)

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
			"universe": "cac40",
			"description": "Test strategy",
			"engine": "TaModel",
			"indicators": ["ema_20"],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": True, "weights": {}, "parameters": {}},
			"entry": {"enabled": True, "parameters": {"position_size": {"formula": "1000"}}},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
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

	def test_strategy_file_format_is_yaml(self, manager):
		"""Test that strategies are stored as YAML."""
		strategy_data = {"name": "yaml_test", "source": "test"}

		manager.save_strategy("yaml_test", strategy_data)

		strategy_file = manager._get_strategy_file("yaml_test")
		with open(strategy_file, "r") as f:
			content = yaml.safe_load(f)

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

	def test_load_template_returns_structure(self, manager):
		"""Test that _load_template returns complete structure."""
		template = manager._load_template()

		# Check all required top-level keys exist
		assert "name" in template
		assert "universe" in template
		assert "description" in template
		assert "engine" in template
		assert "indicators" in template

		# Check all required sections exist
		assert "watchlist" in template
		assert "signals" in template
		assert "entry" in template
		assert "order" in template
		assert "exit" in template
		assert "backtest" in template

	def test_load_template_signals_has_weights_and_parameters(self, manager):
		"""Test that signals section in template has weights and parameters."""
		template = manager._load_template()
		signals = template.get("signals", {})

		assert "weights" in signals
		assert "parameters" in signals

	def test_load_template_order_has_position_sizing(self, manager):
		"""Test that order section in template has position_sizing parameter."""
		template = manager._load_template()
		order = template.get("order", {})

		assert "parameters" in order
		assert "position_sizing" in order.get("parameters", {})

	def test_check_strategy_valid(self, manager):
		"""Test check_strategy on a valid strategy."""
		strategy_data = {
			"name": "valid_strategy",
			"universe": "cac40",
			"description": "Test strategy",
			"engine": "TaModel",
			"indicators": ["ema_20"],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": True, "weights": {}, "parameters": {}},
			"entry": {"enabled": True, "parameters": {"position_size": {"formula": "1000"}}},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("valid_strategy", strategy_data)
		result = manager.check_strategy("valid_strategy")

		assert result.get("valid") is True
		assert result.get("issues") == []
		assert result.get("issue_count") == 0

	def test_check_strategy_missing_sections(self, manager):
		"""Test check_strategy detects missing sections."""
		strategy_data = {
			"name": "incomplete_strategy",
			"universe": "cac40",
			"description": "Incomplete",
			"engine": "TaModel",
			"indicators": [],
		}

		manager.save_strategy("incomplete_strategy", strategy_data)
		result = manager.check_strategy("incomplete_strategy")

		assert result.get("valid") is False
		assert result.get("issue_count") > 0
		issues = result.get("issues", [])
		assert any("watchlist" in issue for issue in issues)
		assert any("order" in issue for issue in issues)

	def test_check_strategy_missing_sub_fields(self, manager):
		"""Test check_strategy detects missing sub-fields."""
		strategy_data = {
			"name": "missing_fields",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": [],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": False},  # Missing weights and parameters
			"entry": {"enabled": True, "parameters": {}},  # Missing position_size
			"order": {"enabled": True, "parameters": {}},
			"exit": {"enabled": True, "parameters": {}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("missing_fields", strategy_data)
		result = manager.check_strategy("missing_fields")

		assert result.get("valid") is False
		issues = result.get("issues", [])
		assert any("signals.weights" in issue for issue in issues)
		assert any("signals.parameters" in issue for issue in issues)
		assert any("entry.parameters.position_size" in issue for issue in issues)

	def test_fix_strategy_adds_missing_sections(self, manager):
		"""Test fix_strategy adds missing sections."""
		strategy_data = {
			"name": "incomplete",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": [],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": False},
			"entry": {"enabled": True, "parameters": {"position_size": {"formula": "1000"}}},
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("incomplete", strategy_data)
		result = manager.fix_strategy("incomplete")

		assert result.get("status") == "success"
		assert len(result.get("changes", [])) > 0

		# Verify the fix actually saved
		loaded = manager.load_strategy("incomplete")
		loaded_data = loaded.get("data", {})
		assert "order" in loaded_data
		assert "weights" in loaded_data.get("signals", {})
		assert "parameters" in loaded_data.get("signals", {})

	def test_fix_strategy_adds_missing_sub_parameters(self, manager):
		"""Test fix_strategy adds missing sub-parameters."""
		strategy_data = {
			"name": "missing_params",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": [],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": False},
			"entry": {"enabled": True, "parameters": {"position_size": {"formula": "1000"}}},
			"order": {"enabled": True, "parameters": {}},  # Empty, should be populated
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("missing_params", strategy_data)
		result = manager.fix_strategy("missing_params")

		assert result.get("status") == "success"

		# Verify order.parameters was populated
		loaded = manager.load_strategy("missing_params")
		order_params = loaded.get("data", {}).get("order", {}).get("parameters", {})
		assert "position_sizing" in order_params

	def test_fix_strategy_dry_run(self, manager):
		"""Test fix_strategy with dry_run doesn't save."""
		strategy_data = {
			"name": "dry_run_test",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": [],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": False},
			"entry": {"enabled": True, "parameters": {"position_size": {"formula": "1000"}}},
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("dry_run_test", strategy_data)
		result = manager.fix_strategy("dry_run_test", dry_run=True)

		assert result.get("status") == "success"
		assert result.get("dry_run") is True

		# Verify the fix was NOT saved
		loaded = manager.load_strategy("dry_run_test")
		assert "order" not in loaded.get("data", {})  # Should not have been added

	def test_fix_strategy_reports_changes(self, manager):
		"""Test fix_strategy reports changes made."""
		strategy_data = {
			"name": "report_test",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": [],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": False},
			"entry": {"enabled": True, "parameters": {"position_size": {"formula": "1000"}}},
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("report_test", strategy_data)
		result = manager.fix_strategy("report_test")

		changes = result.get("changes", [])
		assert len(changes) > 0
		assert any("signals.weights" in c for c in changes)
		assert any("signals.parameters" in c for c in changes)
		assert any("order" in c for c in changes)

	def test_validate_strategy_requires_top_level_fields(self, manager):
		"""Test validate_strategy_config requires top-level fields."""
		strategy_data = {"name": "incomplete"}

		manager.save_strategy("incomplete", strategy_data)
		result = manager.validate_strategy_config("incomplete")

		assert result.get("valid") is False
		issues = result.get("issues", [])
		assert any("universe" in issue for issue in issues)
		assert any("engine" in issue for issue in issues)

	def test_validate_strategy_requires_sections(self, manager):
		"""Test validate_strategy_config requires all sections."""
		strategy_data = {
			"name": "test",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": [],
		}

		manager.save_strategy("test", strategy_data)
		result = manager.validate_strategy_config("test")

		assert result.get("valid") is False
		issues = result.get("issues", [])
		assert any("watchlist" in issue for issue in issues)
		assert any("entry" in issue for issue in issues)
		assert any("order" in issue for issue in issues)
		assert any("exit" in issue for issue in issues)

	def test_validate_strategy_checks_formula_syntax(self, manager):
		"""Test that formula syntax errors are detected."""
		strategy_data = {
			"name": "formula_test",
			"universe": "cac40",
			"description": "Test formulas",
			"engine": "TaModel",
			"indicators": ["ema_20"],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": True, "weights": {}, "parameters": {}},
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {"formula": "ema_20[0] > close[0 and rsi[0]"}  # Unmatched bracket
				}
			},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop_loss": {"formula": "close[0] - 10"},
					"holding_period": {"formula": "10"}
				}
			},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("formula_test", strategy_data)
		result = manager.validate_strategy_config("formula_test")

		assert result.get("valid") is False
		issues = result.get("issues", [])
		formula_issues = [i for i in issues if "formula" in i.lower()]
		assert any("bracket" in issue.lower() or "closed" in issue.lower() or "syntax" in issue.lower() for issue in formula_issues)

	def test_validate_strategy_checks_undefined_indicators(self, manager):
		"""Test that undefined indicators in formulas are detected."""
		strategy_data = {
			"name": "undefined_ind_test",
			"universe": "cac40",
			"description": "Test undefined indicators",
			"engine": "TaModel",
			"indicators": ["ema_20"],  # rsi_9 not defined
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": True, "weights": {}, "parameters": {}},
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {"formula": "rsi_9[0] > 50"}  # rsi_9 not in indicators
				}
			},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop_loss": {"formula": "close[0] - atr_14[0]"},  # atr_14 not defined
					"holding_period": {"formula": "10"}
				}
			},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("undefined_ind_test", strategy_data)
		result = manager.validate_strategy_config("undefined_ind_test")

		assert result.get("valid") is False
		issues = result.get("issues", [])
		issue_str = " ".join(issues)
		assert "rsi_9" in issue_str
		assert "atr_14" in issue_str

	def test_validate_strategy_allows_valid_formulas(self, manager):
		"""Test that valid formulas pass validation."""
		strategy_data = {
			"name": "valid_formula_test",
			"universe": "cac40",
			"description": "Test valid formulas",
			"engine": "TaModel",
			"indicators": ["ema_20", "rsi_9"],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": True, "weights": {}, "parameters": {}},
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000 / close[0]"},
					"entry_filter": {"formula": "ema_20[0] > close[0] && rsi_9[0] < 70"}
				}
			},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "2000 / close[0]"}}},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop_loss": {"formula": "close[0] - ema_20[0] * 0.02"},
					"holding_period": {"formula": "10"}
				}
			},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("valid_formula_test", strategy_data)
		result = manager.validate_strategy_config("valid_formula_test")

		# Should only have no formula-related issues (other issues may exist)
		issues = result.get("issues", [])
		formula_issues = [i for i in issues if "formula" in i.lower()]
		assert len(formula_issues) == 0

	def test_validate_strategy_checks_undefined_columns(self, manager):
		"""Test that undefined data columns in formulas are detected."""
		strategy_data = {
			"name": "undefined_col_test",
			"universe": "cac40",
			"description": "Test undefined columns",
			"engine": "TaModel",
			"indicators": [],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": True, "weights": {}, "parameters": {}},
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {"formula": "data[\"invalid_col\"] > 100"}  # invalid_col not a valid column
				}
			},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop_loss": {"formula": "close[0]"},
					"holding_period": {"formula": "10"}
				}
			},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("undefined_col_test", strategy_data)
		result = manager.validate_strategy_config("undefined_col_test")

		assert result.get("valid") is False
		issues = result.get("issues", [])
		assert any("invalid_col" in issue for issue in issues)

	def test_fix_strategy_preserves_existing_values(self, manager):
		"""Test fix_strategy never overwrites existing user values."""
		strategy_data = {
			"name": "preserve_test",
			"universe": "nasdaq",  # Different from template cac40
			"description": "Custom description",  # Different from template
			"engine": "LightGbmModel",  # Different from template TaModel
			"indicators": ["rsi_14"],  # Different from template
			"watchlist": {"enabled": False, "parameters": {}},
			"signals": {
				"enabled": True,
				"weights": {"custom_signal": 0.8},  # Custom weights
				"parameters": {}
			},
			"entry": {
				"enabled": True,
				"parameters": {"position_size": {"formula": "2000"}}  # Custom value
			},
			"order": {
				"enabled": True,
				"parameters": {"position_sizing": {"formula": "custom_formula"}}  # Custom value
			},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop_loss": {"formula": "0.90"},  # Different from template
					"holding_period": {"formula": "5"}  # Different from template
				}
			},
			"backtest": {"initial_capital": 20000},  # Different from template
		}

		manager.save_strategy("preserve_test", strategy_data)
		manager.fix_strategy("preserve_test")

		# Load fixed strategy and verify existing values weren't replaced
		loaded = manager.load_strategy("preserve_test")
		fixed = loaded.get("data", {})

		# Verify all custom values preserved
		assert fixed.get("universe") == "nasdaq"
		assert fixed.get("description") == "Custom description"
		assert fixed.get("engine") == "LightGbmModel"
		# Note: ema_10 is added because it's referenced in the template's entry_filter formula
		assert "rsi_14" in fixed.get("indicators", [])
		assert "ema_10" in fixed.get("indicators", [])  # Added from formula reference
		assert fixed.get("signals", {}).get("weights") == {"custom_signal": 0.8}
		assert fixed.get("order", {}).get("parameters", {}).get("position_sizing", {}).get("formula") == "custom_formula"
		assert fixed.get("exit", {}).get("parameters", {}).get("stop_loss", {}).get("formula") == "0.90"
		assert fixed.get("backtest", {}).get("initial_capital") == 20000

	def test_fix_strategy_only_adds_missing_not_duplicates(self, manager):
		"""Test fix_strategy doesn't duplicate existing parameters."""
		strategy_data = {
			"name": "no_dupes_test",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": [],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {
				"enabled": True,
				"weights": {"existing": 0.5},  # Has existing weights
				"parameters": {}  # Has existing parameters (empty)
			},
			"entry": {"enabled": True, "parameters": {"position_size": {"formula": "1000"}}},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("no_dupes_test", strategy_data)
		manager.fix_strategy("no_dupes_test")

		loaded = manager.load_strategy("no_dupes_test")
		fixed = loaded.get("data", {})

		# Verify weights wasn't replaced (should still have only existing weights)
		weights = fixed.get("signals", {}).get("weights", {})
		assert "existing" in weights
		# Template wouldn't add new weights if they don't exist in strategy

	def test_fix_strategy_comments_invalid_nested_keys(self, manager):
		"""Test fix_strategy comments out invalid nested keys in parameters."""
		strategy_data = {
			"name": "invalid_nested_test",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": [],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {
				"enabled": True,
				"weights": {"custom_weight": 0.5},  # Custom weights allowed
				"parameters": {}
			},
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"invalid_param": {"formula": "bad"}
				}
			},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop_loss": {"formula": "0.95"},
					"holding_period": {"formula": "10"},
					"invalid_exit": {"formula": "bad"}
				}
			},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("invalid_nested_test", strategy_data)
		result = manager.fix_strategy("invalid_nested_test")

		# Verify invalid nested keys were reported as changes
		changes = result.get("changes", [])
		assert any("invalid" in c.lower() for c in changes)

		# Load fixed strategy and verify invalid keys were removed from data
		loaded = manager.load_strategy("invalid_nested_test")
		fixed = loaded.get("data", {})

		assert "invalid_param" not in fixed.get("entry", {}).get("parameters", {})
		assert "invalid_exit" not in fixed.get("exit", {}).get("parameters", {})

		# Verify they were commented in the file
		strategy_file = manager._get_strategy_file("invalid_nested_test")
		with open(strategy_file, 'r') as f:
			file_content = f.read()

		assert "# [entry.parameters]" in file_content
		assert "# [exit.parameters]" in file_content
		assert "# invalid_param:" in file_content or "#     invalid_param:" in file_content
		assert "# invalid_exit:" in file_content or "#     invalid_exit:" in file_content

	def test_validate_strategy_checks_indicator_validity(self, manager):
		"""Test that validation checks if declared indicators are valid."""
		strategy_data = {
			"name": "test_strategy",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["atr_14", "invalid_indicator_99", "ema_20"],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": True, "weights": {}, "parameters": {}},
			"entry": {"enabled": True, "parameters": {"position_size": {"formula": "1000"}}},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("invalid_indicator_test", strategy_data)
		result = manager.check_strategy("invalid_indicator_test")

		assert not result["valid"]
		issues = result.get("issues", [])
		assert any("invalid_indicator" in issue.lower() for issue in issues)

	def test_validate_strategy_allows_valid_indicators(self, manager):
		"""Test that validation allows known base indicators with parameters."""
		strategy_data = {
			"name": "test_strategy",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["atr_14", "rsi_9", "ema_10", "ema_20", "macd_12_26"],
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {"enabled": True, "weights": {}, "parameters": {}},
			"entry": {"enabled": True, "parameters": {"position_size": {"formula": "1000"}}},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("valid_indicators_test", strategy_data)
		result = manager.check_strategy("valid_indicators_test")

		# Should not have indicator validation issues (may have other issues but not indicator ones)
		issues = result.get("issues", [])
		indicator_issues = [i for i in issues if "invalid indicator" in i.lower() or "not a supported indicator" in i.lower()]
		assert len(indicator_issues) == 0

	def test_fix_strategy_adds_missing_indicators_from_formulas(self, manager):
		"""Test that fix_strategy adds indicators referenced in formulas."""
		strategy_data = {
			"name": "test_strategy",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["ema_20"],  # Missing other indicators referenced in formulas
			"watchlist": {"enabled": True, "parameters": {}},
			"signals": {
				"enabled": True,
				"weights": {},
				"parameters": {
					"momentum": {"formula": "macd_12_26[0] > 0.5", "description": "Test"}
				}
			},
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {"formula": "close[0] > ema_10[0] and adx_20[0] > 20", "description": "Test"}
				}
			},
			"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
			"exit": {"enabled": True, "parameters": {"stop_loss": {"formula": "0.95"}, "holding_period": {"formula": "10"}}},
			"backtest": {"initial_capital": 10000},
		}

		manager.save_strategy("missing_indicators_test", strategy_data)
		result = manager.fix_strategy("missing_indicators_test")

		# Should have added missing indicators
		assert any("indicator" in change.lower() for change in result.get("changes", []))

		# Load fixed strategy and verify indicators were added
		loaded = manager.load_strategy("missing_indicators_test")
		indicators = loaded.get("data", {}).get("indicators", [])

		# Should have original + macd_12_26, ema_10, adx_20
		assert "ema_20" in indicators  # Original
		assert "macd_12_26" in indicators  # Referenced in momentum formula
		assert "ema_10" in indicators  # Referenced in entry_filter formula
		assert "adx_20" in indicators  # Referenced in entry_filter formula
