"""Pytest configuration and fixtures for strategy tests."""

from pathlib import Path
import tempfile
import shutil
import yaml


def create_test_strategy_file(directory, name, source="test_source"):
    """Create a test strategy file."""
    strategy_config = {
        "strategies": [
            {
                "name": name,
                "description": f"Test strategy {name}",
                "data": {
                    "source": source,
                    "indicators": ["rsi", "ma"]
                },
                "agents": {
                    "MomentumScoringAgent": {
                        "windows": {
                            "short_term_days": 5,
                            "mid_term_days": 15,
                        },
                        "weights": {
                            "short_term": 0.4,
                            "mid_term": 0.6,
                        }
                    }
                }
            }
        ]
    }

    strategy_file = Path(directory) / f"{name}.yml"
    with open(strategy_file, "w") as f:
        yaml.dump(strategy_config, f)

    return strategy_file


def pytest_configure(config):
    """Configure pytest."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )


# Fixtures can be added here for common test setup
