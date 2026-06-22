"""Shared alpha factor catalog (init/config/alphas.yml), opt-in per strategy.

A strategy pulls in the catalog by setting `features: {shared_alphas: true}`.
StrategyManager.load_strategy() calls merge_shared_alphas() on every strategy it
loads; it's a no-op unless that flag is set.
"""

from pathlib import Path
from typing import Any, Dict

import yaml

_SHARED_ALPHAS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "init" / "config" / "alphas.yml"


def load_shared_alphas_config() -> Dict[str, Any]:
    """Load init/config/alphas.yml. Returns {"indicators": [], "alphas": {}} if missing."""
    if not _SHARED_ALPHAS_PATH.exists():
        return {"indicators": [], "alphas": {}}
    with open(_SHARED_ALPHAS_PATH) as f:
        return yaml.safe_load(f) or {"indicators": [], "alphas": {}}


def merge_shared_alphas(strategy_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge the shared catalog's indicators/alphas into strategy_config, in place.

    No-op unless strategy_config["features"]["shared_alphas"] is truthy. The
    strategy's own indicators and alpha categories always take precedence - shared
    entries are only added where the strategy doesn't already define them.
    """
    features = strategy_config.get("features") or {}
    if not features.get("shared_alphas"):
        return strategy_config

    shared = load_shared_alphas_config()

    shared_indicators = shared.get("indicators") or []
    current_indicators = strategy_config.get("indicators") or []
    strategy_config["indicators"] = current_indicators + [
        i for i in shared_indicators if i not in current_indicators
    ]

    shared_alpha_categories = shared.get("alphas") or {}
    if shared_alpha_categories:
        alphas = features.setdefault("alphas", {})
        for category, definitions in shared_alpha_categories.items():
            alphas.setdefault(category, definitions)
        strategy_config["features"] = features

    return strategy_config
