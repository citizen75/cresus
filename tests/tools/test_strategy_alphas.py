"""Tests for the shared alpha catalog opt-in merge (tools/strategy/alphas.py)."""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.strategy import alphas as alphas_module
from tools.strategy.alphas import load_shared_alphas_config, merge_shared_alphas


@pytest.fixture
def fake_shared_catalog(tmp_path, monkeypatch):
    """Point the module at a small, isolated catalog instead of the real
    init/config/alphas.yml, so these tests don't depend on its exact contents."""
    catalog = {
        "indicators": ["atr_14", "ema_20"],
        "alphas": {
            "trend": [{"name": "trend_adx14", "formula": "adx_14", "description": "ADX"}],
            "volume": [{"name": "vol_obv", "formula": "obv", "description": "OBV"}],
        },
    }
    catalog_file = tmp_path / "alphas.yml"
    with open(catalog_file, "w") as f:
        yaml.dump(catalog, f)

    monkeypatch.setattr(alphas_module, "_SHARED_ALPHAS_PATH", catalog_file)
    return catalog


class TestLoadSharedAlphasConfig:
    def test_loads_catalog_file(self, fake_shared_catalog):
        loaded = load_shared_alphas_config()
        assert loaded == fake_shared_catalog

    def test_missing_file_returns_empty_catalog(self, tmp_path, monkeypatch):
        monkeypatch.setattr(alphas_module, "_SHARED_ALPHAS_PATH", tmp_path / "does_not_exist.yml")
        assert load_shared_alphas_config() == {"indicators": [], "alphas": {}}


class TestMergeSharedAlphas:
    def test_noop_without_features_key(self, fake_shared_catalog):
        strategy_config = {"name": "s1", "indicators": ["rsi_14"]}
        merged = merge_shared_alphas(strategy_config)
        assert merged["indicators"] == ["rsi_14"]
        assert "features" not in merged or "alphas" not in merged.get("features", {})

    def test_noop_when_shared_alphas_false(self, fake_shared_catalog):
        strategy_config = {"name": "s1", "indicators": ["rsi_14"], "features": {"shared_alphas": False}}
        merged = merge_shared_alphas(strategy_config)
        assert merged["indicators"] == ["rsi_14"]
        assert "alphas" not in merged["features"]

    def test_merges_indicators_when_opted_in(self, fake_shared_catalog):
        strategy_config = {"name": "s1", "indicators": ["rsi_14"], "features": {"shared_alphas": True}}
        merged = merge_shared_alphas(strategy_config)
        assert merged["indicators"] == ["rsi_14", "atr_14", "ema_20"]

    def test_strategy_indicators_take_precedence_no_duplicates(self, fake_shared_catalog):
        strategy_config = {"name": "s1", "indicators": ["ema_20", "rsi_14"], "features": {"shared_alphas": True}}
        merged = merge_shared_alphas(strategy_config)
        # ema_20 already present - not duplicated, original order preserved, then new ones appended
        assert merged["indicators"] == ["ema_20", "rsi_14", "atr_14"]

    def test_merges_alpha_categories_when_opted_in(self, fake_shared_catalog):
        strategy_config = {"name": "s1", "features": {"shared_alphas": True}}
        merged = merge_shared_alphas(strategy_config)
        assert merged["features"]["alphas"]["trend"] == fake_shared_catalog["alphas"]["trend"]
        assert merged["features"]["alphas"]["volume"] == fake_shared_catalog["alphas"]["volume"]

    def test_strategy_own_alpha_category_not_overridden(self, fake_shared_catalog):
        strategy_config = {
            "name": "s1",
            "features": {
                "shared_alphas": True,
                "alphas": {"trend": [{"name": "my_trend", "formula": "ema_10", "description": "custom"}]},
            },
        }
        merged = merge_shared_alphas(strategy_config)
        # strategy's own "trend" category wins; shared "volume" category still gets added
        assert merged["features"]["alphas"]["trend"] == [{"name": "my_trend", "formula": "ema_10", "description": "custom"}]
        assert merged["features"]["alphas"]["volume"] == fake_shared_catalog["alphas"]["volume"]

    def test_no_indicators_key_defaults_to_empty_list(self, fake_shared_catalog):
        strategy_config = {"name": "s1", "features": {"shared_alphas": True}}
        merged = merge_shared_alphas(strategy_config)
        assert merged["indicators"] == ["atr_14", "ema_20"]
