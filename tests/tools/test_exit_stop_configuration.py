"""Tests for consolidated exit.stop configuration."""

import pytest
import yaml
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.strategy.strategy import StrategyManager
from tools.strategy.validator import StrategyValidator


class TestExitStopConfiguration:
	"""Test exit.stop consolidated configuration."""

	@pytest.fixture
	def temp_project(self):
		"""Create a temporary project directory."""
		with TemporaryDirectory() as tmpdir:
			project_root = Path(tmpdir)
			(project_root / "db" / "local").mkdir(parents=True, exist_ok=True)

			# Create template directory
			template_dir = project_root / "init" / "templates"
			template_dir.mkdir(parents=True, exist_ok=True)

			template_data = {
				"name": "template_name",
				"universe": "cac40",
				"description": "Strategy description",
				"engine": "TaModel",
				"indicators": ["ema_10", "ema_20"],
				"watchlist": {"enabled": True, "parameters": {}},
				"signals": {"enabled": True, "weights": {}, "parameters": {}},
				"entry": {
					"enabled": True,
					"parameters": {
						"position_size": {"formula": "1000"},
						"entry_filter": {"formula": "close[0] > ema_20[0]", "description": "Entry filter"},
						"order_type": {"formula": "market", "description": "Order type"}
					}
				},
				"order": {"enabled": True, "parameters": {"position_sizing": {"formula": "1000"}}},
				"exit": {
					"enabled": True, 
					"parameters": {
						"stop": {"type": "fix", "formula": "close[0] * 0.95", "description": "Stop loss"},
						"take_profit": {"formula": "close[0] * 1.05", "description": "Take profit"},
						"holding_period": {"formula": "10"}
					}
				},
				"backtest": {"initial_capital": 10000},
			}

			template_file = template_dir / "strategy.yml"
			with open(template_file, "w") as f:
				yaml.dump(template_data, f)

			yield project_root

	@pytest.fixture
	def manager(self, temp_project):
		"""Create StrategyManager with temporary project."""
		return StrategyManager(project_root=temp_project)

	@pytest.fixture
	def validator(self):
		"""Create StrategyValidator."""
		return StrategyValidator()

	def test_exit_stop_fix_type_validation(self, validator):
		"""Test validation of exit.stop with type: fix."""
		strategy_data = {
			"name": "test_fix_stop",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["ema_20"],
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {"formula": "close[0] > ema_20[0]"},
					"order_type": {"formula": "market"}
				}
			},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop": {"type": "fix", "formula": "close[0] * 0.95"},
					"take_profit": {"formula": "close[0] * 1.05"},
					"holding_period": {"formula": "10"}
				}
			}
		}

		is_valid, errors = validator.validate(strategy_data)
		assert is_valid, f"Strategy should be valid, errors: {errors}"

	def test_exit_stop_trailing_type_validation(self, validator):
		"""Test validation of exit.stop with type: trailing."""
		strategy_data = {
			"name": "test_trailing_stop",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["ema_20"],
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {"formula": "close[0] > ema_20[0]"},
					"order_type": {"formula": "market"}
				}
			},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop": {"type": "trailing", "formula": "close[0] * 0.97"},
					"take_profit": {"formula": "close[0] * 1.08"},
					"holding_period": {"formula": "10"}
				}
			}
		}

		is_valid, errors = validator.validate(strategy_data)
		assert is_valid, f"Strategy should be valid, errors: {errors}"

	def test_exit_stop_missing_type_error(self, validator):
		"""Test validation fails when stop type is missing."""
		strategy_data = {
			"name": "test_missing_type",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["ema_20"],
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {"formula": "close[0] > ema_20[0]"},
					"order_type": {"formula": "market"}
				}
			},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop": {"formula": "close[0] * 0.95"},  # Missing type
					"take_profit": {"formula": "close[0] * 1.05"},
					"holding_period": {"formula": "10"}
				}
			}
		}

		is_valid, errors = validator.validate(strategy_data)
		assert not is_valid
		assert any("type" in err for err in errors)

	def test_fix_strategy_adds_missing_stop(self, manager):
		"""Test fix_strategy adds missing stop parameter."""
		strategy_data = {
			"name": "missing_stop_strategy",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["ema_20"],
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {"formula": "close[0] > ema_20[0]"},
					"order_type": {"formula": "market"}
				}
			},
			"exit": {
				"enabled": True,
				"parameters": {
					"take_profit": {"formula": "close[0] * 1.05"},
					"holding_period": {"formula": "10"}
					# Missing: stop
				}
			}
		}

		manager.save_strategy("missing_stop_strategy", strategy_data)
		
		# Dry run fix to see what would be added
		result = manager.fix_strategy("missing_stop_strategy", dry_run=True)
		
		assert result["status"] == "success"
		assert any("stop" in change.lower() for change in result["changes"])

	def test_entry_filter_with_sha_signals(self, validator):
		"""Test validation of strategy with sha signal entry filter."""
		strategy_data = {
			"name": "test_sha_entry",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["sha_10", "sha_10_green", "sha_10_red", "adx_14"],
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {
						"formula": "sha_10_green[0] == 1 and sha_10_green[-1] == 1 and sha_10_red[-2] == 1 and adx_14[0] > 25"
					},
					"order_type": {"formula": "market"}
				}
			},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop": {"type": "trailing", "formula": "close[0] * 0.97"},
					"take_profit": {"formula": "close[0] * 1.08"},
					"holding_period": {"formula": "60"}
				}
			}
		}

		is_valid, errors = validator.validate(strategy_data)
		assert is_valid, f"Strategy should be valid, errors: {errors}"

	def test_stop_loss_vs_stop_old_format_rejected(self, validator):
		"""Test that old stop_loss format is rejected."""
		strategy_data = {
			"name": "test_old_format",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["ema_20"],
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					"entry_filter": {"formula": "close[0] > ema_20[0]"},
					"order_type": {"formula": "market"}
				}
			},
			"exit": {
				"enabled": True,
				"parameters": {
					"stop_loss": {"formula": "close[0] * 0.95"},  # Old format
					"take_profit": {"formula": "close[0] * 1.05"},
					"holding_period": {"formula": "10"}
				}
			}
		}

		is_valid, errors = validator.validate(strategy_data)
		assert not is_valid
		assert any("stop" in err for err in errors)

	def test_fix_strategy_actually_saves_changes(self, manager):
		"""Test that fix_strategy actually saves the fixed strategy (reproduces --fix issue)."""
		strategy_data = {
			"name": "fix_test_strategy",
			"universe": "cac40",
			"description": "Test",
			"engine": "TaModel",
			"indicators": ["ema_20"],
			"entry": {
				"enabled": True,
				"parameters": {
					"position_size": {"formula": "1000"},
					# Missing: entry_filter
					"order_type": {"formula": "market"}
				}
			},
			"exit": {
				"enabled": True,
				"parameters": {
					# Missing: stop
					"take_profit": {"formula": "close[0] * 1.05"},
					"holding_period": {"formula": "10"}
				}
			}
		}

		manager.save_strategy("fix_test_strategy", strategy_data)

		# Actual fix (not dry run) - this is where the issue occurred
		result = manager.fix_strategy("fix_test_strategy", dry_run=False)

		# Should not return "Unknown error"
		assert result["status"] == "success", f"Fix failed with: {result.get('message', result)}"
		assert "entry_filter" in str(result.get("changes", [])).lower()
		assert "stop" in str(result.get("changes", [])).lower()

		# Verify the fixed strategy can be loaded and validated
		loaded = manager.load_strategy("fix_test_strategy")
		assert loaded["status"] == "success"

		fixed_data = loaded["data"]
		assert "entry_filter" in fixed_data.get("entry", {}).get("parameters", {})
		assert "stop" in fixed_data.get("exit", {}).get("parameters", {})

if __name__ == "__main__":
	pytest.main([__file__, "-v"])
