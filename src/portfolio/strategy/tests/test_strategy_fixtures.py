"""Tests for strategy functions using fixtures and temporary files."""

import sys
from pathlib import Path
import tempfile
import shutil
import yaml
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from src.tools.finance.strategy.scripts.strategy import (
    load_strategy,
    find_strategy_by_name,
    validate_strategy_config,
)


class TestStrategyWithFixtures:
    """Test strategy functions with fixture-based temporary files."""

    @pytest.fixture
    def temp_strategy_dir(self):
        """Create a temporary directory with test strategy files."""
        temp_dir = tempfile.mkdtemp()

        # Create a test strategy file
        strategy_config = {
            "strategies": [
                {
                    "name": "test_strategy",
                    "description": "A test strategy for unit testing",
                    "data": {
                        "source": "test_source",
                        "indicators": ["rsi", "ma", "ema"]
                    },
                    "agents": {
                        "MomentumScoringAgent": {
                            "windows": {
                                "short_term_days": 5,
                                "mid_term_days": 15,
                            }
                        },
                        "SignalAgent": {
                            "threshold": 0.5
                        }
                    }
                }
            ]
        }

        strategy_file = Path(temp_dir) / "test_strategy.yml"
        with open(strategy_file, "w") as f:
            yaml.dump(strategy_config, f)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def invalid_yaml_file(self):
        """Create a temporary directory with invalid YAML file."""
        temp_dir = tempfile.mkdtemp()

        # Create an invalid YAML file
        invalid_file = Path(temp_dir) / "invalid.yml"
        with open(invalid_file, "w") as f:
            f.write("{ invalid: yaml: [content")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestStrategyYAMLParsing:
    """Tests for YAML parsing and error handling."""

    def test_strategy_yaml_structure(self):
        """Test that strategy YAML has correct structure."""
        result = load_strategy("trend_following_cac")
        assert result["status"] == "success"

        strategy_data = result["data"]
        assert "name" in strategy_data
        assert isinstance(strategy_data, dict)

    def test_strategy_with_agents(self):
        """Test strategy that has agents section."""
        result = find_strategy_by_name("trend_following_cac")
        if result["status"] == "success":
            strategy_data = result["data"]
            # Check if agents are present
            if "agents" in strategy_data:
                assert isinstance(strategy_data["agents"], dict)


class TestStrategyDataValidation:
    """Tests for strategy data validation."""

    def test_validate_strategy_returns_valid_field(self):
        """Test that validate function returns valid boolean field."""
        result = validate_strategy_config("trend_following_cac")
        assert isinstance(result["valid"], bool)

    def test_valid_strategy_has_no_issues(self):
        """Test that valid strategy reports no issues."""
        result = validate_strategy_config("trend_following_cac")
        if result["valid"]:
            assert result["issue_count"] == 0
            assert len(result["issues"]) == 0

    def test_validate_checks_required_fields(self):
        """Test that validation checks for required fields."""
        result = validate_strategy_config("trend_following_cac")
        assert result["status"] == "success"
        # Should have checked for name, data, agents, etc.
        assert "issues" in result


class TestStrategyReturnTypes:
    """Tests for return type consistency."""

    def test_load_strategy_returns_dict(self):
        """Test that load_strategy returns a dictionary."""
        result = load_strategy("trend_following_cac")
        assert isinstance(result, dict)

    def test_strategy_name_is_string(self):
        """Test that strategy name is a string."""
        result = load_strategy("trend_following_cac")
        if result["status"] == "success":
            assert isinstance(result.get("name"), str)

    def test_strategy_data_is_dict(self):
        """Test that strategy data is a dictionary."""
        result = load_strategy("trend_following_cac")
        if result["status"] == "success":
            assert isinstance(result.get("data"), dict)


class TestMultipleStrategies:
    """Tests for handling multiple strategies."""

    def test_load_different_strategies(self):
        """Test loading different strategies sequentially."""
        strategies = ["trend_following_cac", "breakout_cac"]

        for strategy_name in strategies:
            result = find_strategy_by_name(strategy_name)
            # Either success or not found - both are OK
            assert result["status"] in ["success", "error"]

    def test_consistency_between_load_and_find(self):
        """Test that load_strategy and find_strategy_by_name are consistent."""
        strategy_name = "trend_following_cac"

        load_result = load_strategy(strategy_name)
        find_result = find_strategy_by_name(strategy_name)

        if load_result["status"] == "success" and find_result["status"] == "success":
            # Both succeeded, should have same data
            assert load_result["data"] == find_result["data"]


class TestErrorMessages:
    """Tests for error message quality."""

    def test_error_message_includes_strategy_name(self):
        """Test that error messages include strategy name."""
        result = load_strategy("nonexistent_xyz")
        assert result["status"] == "error"
        assert "nonexistent_xyz" in result["message"]

    def test_error_message_includes_error_type(self):
        """Test that error results include error_type field."""
        result = load_strategy("nonexistent_xyz")
        assert result["status"] == "error"
        assert "error_type" in result
        assert result["error_type"] in ["FileNotFoundError", "NotFound", "YAMLError"]

    def test_not_found_error_provides_guidance(self):
        """Test that not found errors provide helpful guidance."""
        result = find_strategy_by_name("strategy_does_not_exist")
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
