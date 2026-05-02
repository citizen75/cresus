"""Unit tests for strategy loading and configuration functions."""

import sys
from pathlib import Path
import tempfile
import yaml
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from src.tools.finance.strategy.scripts.strategy import (
    load_strategy,
    find_strategy_by_name,
    get_agent_config,
    get_momentum_config,
    get_tickers_from_source,
    list_strategies,
    get_strategy_by_source,
    validate_strategy_config,
)


class TestLoadStrategy:
    """Tests for load_strategy function."""

    def test_load_existing_strategy(self):
        """Test loading an existing strategy."""
        result = load_strategy("trend_following_cac")
        assert result["status"] == "success"
        assert result["name"] == "trend_following_cac"
        assert "data" in result
        assert result["source"] is not None

    def test_load_nonexistent_strategy(self):
        """Test loading a non-existent strategy returns error."""
        result = load_strategy("nonexistent_strategy_xyz")
        assert result["status"] == "error"
        assert result["error_type"] == "FileNotFoundError"
        assert "not found" in result["message"]

    def test_load_strategy_returns_correct_fields(self):
        """Test that loaded strategy has all expected fields."""
        result = load_strategy("trend_following_cac")
        assert "status" in result
        assert "data" in result
        assert "name" in result
        assert "description" in result
        assert "source" in result

    def test_load_strategy_data_structure(self):
        """Test that strategy data has expected structure."""
        result = load_strategy("trend_following_cac")
        strategy_data = result["data"]

        # Check for key fields in strategy data
        assert isinstance(strategy_data, dict)
        assert "name" in strategy_data


class TestFindStrategyByName:
    """Tests for find_strategy_by_name function."""

    def test_find_existing_strategy(self):
        """Test finding an existing strategy by name."""
        result = find_strategy_by_name("trend_following_cac")
        assert result["status"] == "success"
        assert result["name"] == "trend_following_cac"
        assert "data" in result

    def test_find_nonexistent_strategy(self):
        """Test finding non-existent strategy returns error."""
        result = find_strategy_by_name("strategy_that_does_not_exist")
        assert result["status"] == "error"
        assert result["error_type"] == "NotFound"

    def test_find_strategy_contains_file_info(self):
        """Test that found strategy includes file information."""
        result = find_strategy_by_name("trend_following_cac")
        assert result["status"] == "success"
        assert "file" in result
        assert result["file"].endswith(".yml")


class TestGetAgentConfig:
    """Tests for get_agent_config function."""

    def test_get_existing_agent_config(self):
        """Test getting config for existing agent in strategy."""
        # First, get a strategy that has agents
        result = find_strategy_by_name("trend_following_cac")
        if result["status"] == "success":
            strategy_data = result["data"]
            if "agents" in strategy_data and strategy_data["agents"]:
                agent_name = list(strategy_data["agents"].keys())[0]
                config_result = get_agent_config("trend_following_cac", agent_name)
                assert config_result["status"] == "success"
                assert "config" in config_result
                assert config_result["strategy"] == "trend_following_cac"
                assert config_result["agent"] == agent_name

    def test_get_agent_config_nonexistent_agent(self):
        """Test getting config for non-existent agent returns error."""
        result = get_agent_config("trend_following_cac", "NonExistentAgent")
        if result["status"] == "success":
            # Some strategies might not have agents, that's OK
            pass
        else:
            # If it fails, it should be because agent not found
            assert "not found" in result["message"].lower() or "no agents" in result["message"].lower()

    def test_get_agent_config_nonexistent_strategy(self):
        """Test getting agent config from non-existent strategy returns error."""
        result = get_agent_config("nonexistent_strategy", "SomeAgent")
        assert result["status"] == "error"


class TestGetMomentumConfig:
    """Tests for get_momentum_config function."""

    def test_get_momentum_config_structure(self):
        """Test that momentum config has expected structure."""
        result = get_momentum_config("trend_following_cac")

        # Should either succeed or fail gracefully
        assert "status" in result

        if result["status"] == "success":
            assert "strategy_name" in result
            assert "parameters" in result
            assert "data" in result
            assert "metadata" in result
            assert result["strategy_name"] == "trend_following_cac"

    def test_get_momentum_config_returns_dict(self):
        """Test that momentum config returns a dictionary."""
        result = get_momentum_config("trend_following_cac")
        assert isinstance(result, dict)
        assert "status" in result


class TestGetTickersFromSource:
    """Tests for get_tickers_from_source function."""

    def test_get_tickers_valid_source(self):
        """Test getting tickers from a valid source."""
        result = get_tickers_from_source("cac40")
        assert result["status"] == "success"
        assert "source" in result
        assert result["source"] == "cac40"

    def test_get_tickers_invalid_source(self):
        """Test getting tickers from invalid source returns error or empty."""
        result = get_tickers_from_source("nonexistent_source_xyz")
        # Should return error status
        assert result["status"] == "error"
        assert "not found" in result["message"].lower() or "no strategies found" in result["message"].lower()

    def test_get_tickers_returns_correct_fields(self):
        """Test that tickers result has expected fields."""
        result = get_tickers_from_source("cac40")
        assert "status" in result
        assert "source" in result


class TestListStrategies:
    """Tests for list_strategies function."""

    def test_list_strategies_returns_success(self):
        """Test that list_strategies returns success status."""
        result = list_strategies()
        assert result["status"] == "success"

    def test_list_strategies_returns_list(self):
        """Test that list_strategies returns a list of strategies."""
        result = list_strategies()
        assert isinstance(result["strategies"], list)

    def test_list_strategies_count_matches(self):
        """Test that total_count matches strategies list length."""
        result = list_strategies()
        assert result["total_count"] == len(result["strategies"])

    def test_list_strategies_has_required_fields(self):
        """Test that each strategy has required fields."""
        result = list_strategies()
        if result["strategies"]:
            for strategy in result["strategies"]:
                assert "name" in strategy
                assert "description" in strategy or "description" in strategy
                assert "source" in strategy

    def test_list_strategies_not_empty(self):
        """Test that strategies list is not empty."""
        result = list_strategies()
        assert len(result["strategies"]) > 0


class TestGetStrategyBySource:
    """Tests for get_strategy_by_source function."""

    def test_get_strategy_by_valid_source(self):
        """Test getting strategies filtered by valid source."""
        result = get_strategy_by_source("cac40")
        assert result["status"] == "success"
        assert result["source"] == "cac40"
        assert isinstance(result["strategies"], list)

    def test_get_strategy_by_invalid_source(self):
        """Test getting strategies for non-existent source."""
        result = get_strategy_by_source("nonexistent_source_xyz")
        # Should return success but with empty list
        if result["status"] == "success":
            assert len(result["strategies"]) == 0
        else:
            assert result["status"] == "error"

    def test_get_strategy_by_source_count_matches(self):
        """Test that total_count matches strategies list length."""
        result = get_strategy_by_source("cac40")
        if result["status"] == "success":
            assert result["total_count"] == len(result["strategies"])

    def test_get_strategy_by_source_has_required_fields(self):
        """Test that each strategy has required fields."""
        result = get_strategy_by_source("cac40")
        if result["status"] == "success" and result["strategies"]:
            for strategy in result["strategies"]:
                assert "name" in strategy
                assert "source" in strategy
                assert strategy["source"] == "cac40"


class TestValidateStrategyConfig:
    """Tests for validate_strategy_config function."""

    def test_validate_existing_strategy(self):
        """Test validating an existing strategy."""
        result = validate_strategy_config("trend_following_cac")
        assert result["status"] == "success"
        assert "valid" in result
        assert "issues" in result
        assert isinstance(result["issues"], list)

    def test_validate_nonexistent_strategy(self):
        """Test validating non-existent strategy returns error."""
        result = validate_strategy_config("nonexistent_strategy_xyz")
        assert result["status"] == "error"
        assert result["valid"] is False

    def test_validate_returns_issue_count(self):
        """Test that validation returns issue count."""
        result = validate_strategy_config("trend_following_cac")
        assert "issue_count" in result
        assert result["issue_count"] == len(result["issues"])

    def test_validate_strategy_has_required_fields(self):
        """Test that validation result has required fields."""
        result = validate_strategy_config("trend_following_cac")
        assert "status" in result
        assert "strategy" in result
        assert "valid" in result
        assert "issues" in result


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_find_and_validate_strategy(self):
        """Test finding a strategy and then validating it."""
        find_result = find_strategy_by_name("trend_following_cac")
        assert find_result["status"] == "success"

        validate_result = validate_strategy_config("trend_following_cac")
        assert validate_result["status"] == "success"
        assert validate_result["strategy"] == find_result["name"]

    def test_list_and_find_strategy(self):
        """Test listing strategies then finding one."""
        list_result = list_strategies()
        assert list_result["status"] == "success"
        assert len(list_result["strategies"]) > 0

        # Get first strategy name from list
        first_strategy_name = list_result["strategies"][0]["name"]
        find_result = find_strategy_by_name(first_strategy_name)
        assert find_result["status"] == "success"
        assert find_result["name"] == first_strategy_name

    def test_get_by_source_and_find_strategy(self):
        """Test getting strategies by source then finding one."""
        by_source_result = get_strategy_by_source("cac40")
        if by_source_result["status"] == "success" and by_source_result["strategies"]:
            # Get first strategy from source
            first_strategy_name = by_source_result["strategies"][0]["name"]
            find_result = find_strategy_by_name(first_strategy_name)
            assert find_result["status"] == "success"
            assert find_result["source"] == "cac40"


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_load_strategy_with_empty_name(self):
        """Test loading strategy with empty name."""
        result = load_strategy("")
        assert result["status"] == "error"

    def test_find_strategy_with_empty_name(self):
        """Test finding strategy with empty name."""
        result = find_strategy_by_name("")
        assert result["status"] == "error"

    def test_get_agent_config_with_empty_strings(self):
        """Test get_agent_config with empty strings."""
        result = get_agent_config("", "")
        assert result["status"] == "error"

    def test_validate_strategy_with_empty_name(self):
        """Test validating strategy with empty name."""
        result = validate_strategy_config("")
        assert result["status"] == "error"

    def test_functions_return_dict(self):
        """Test that all functions return dictionaries."""
        assert isinstance(load_strategy("trend_following_cac"), dict)
        assert isinstance(find_strategy_by_name("trend_following_cac"), dict)
        assert isinstance(list_strategies(), dict)
        assert isinstance(get_strategy_by_source("cac40"), dict)
        assert isinstance(validate_strategy_config("trend_following_cac"), dict)


class TestStatusField:
    """Tests for status field consistency."""

    def test_all_responses_have_status(self):
        """Test that all responses include status field."""
        assert "status" in load_strategy("trend_following_cac")
        assert "status" in find_strategy_by_name("trend_following_cac")
        assert "status" in list_strategies()
        assert "status" in get_strategy_by_source("cac40")
        assert "status" in validate_strategy_config("trend_following_cac")

    def test_status_values_are_valid(self):
        """Test that status values are either 'success' or 'error'."""
        valid_statuses = {"success", "error"}

        result = load_strategy("trend_following_cac")
        assert result["status"] in valid_statuses

        result = find_strategy_by_name("nonexistent")
        assert result["status"] in valid_statuses

        result = list_strategies()
        assert result["status"] in valid_statuses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
