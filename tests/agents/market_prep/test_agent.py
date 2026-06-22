"""Tests for MarketPrepAgent."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.market_prep.agent import MarketPrepAgent
from core.context import AgentContext


def _mocked_agent(status="success"):
    """Build a MagicMock standing in for an Agent instance, with .run() succeeding."""
    instance = MagicMock()
    instance.run.return_value = {"status": status, "input": {}, "output": {}}
    instance.agents_executed = []
    return instance


PATCH_TARGETS = [
    "agents.market_prep.agent.StrategyAgent",
    "agents.market_prep.agent.DataAgent",
    "agents.market_prep.agent.WatchlistAlphasAgent",
    "agents.market_prep.agent.WatchListAgent",
    "agents.market_prep.agent.SignalsAgent",
    "agents.market_prep.agent.WatchlistRankingAgent",
    "agents.market_prep.agent.WatchlistScoringAgent",
    "agents.market_prep.agent.WatchlistSortingAgent",
    "agents.market_prep.agent.EntryAgent",
    "agents.market_prep.agent.OrdersEntryAgent",
    "agents.market_prep.agent.OrdersSendingAgent",
    "agents.market_prep.agent.SaveWatchlistAgent",
    "agents.market_prep.agent.OrdersExitAgent",
]


def _patch_all_steps():
    """Patch every agent class MarketPrepAgent constructs, each succeeding immediately."""
    patchers = [patch(target) for target in PATCH_TARGETS]
    mocks = [p.start() for p in patchers]
    for mock_cls in mocks:
        mock_cls.return_value = _mocked_agent()
    return patchers


class TestMarketPrepAgentInitialization:
    """Test MarketPrepAgent initialization."""

    def test_initialization_with_strategy_name(self):
        agent = MarketPrepAgent("test_strategy")
        assert agent.strategy_name == "test_strategy"
        assert agent.context is not None
        assert isinstance(agent.context, AgentContext)

    def test_initialization_with_custom_context(self):
        custom_context = AgentContext()
        agent = MarketPrepAgent("test_strategy", context=custom_context)
        assert agent.context is custom_context

    def test_repr_shows_strategy_name(self):
        agent = MarketPrepAgent("my_strategy")
        repr_str = repr(agent)
        assert "my_strategy" in repr_str
        assert "MarketPrepAgent" in repr_str


class TestMarketPrepAgentProcess:
    """Test MarketPrepAgent.process() with every sub-agent mocked out."""

    def test_process_with_valid_input(self):
        patchers = _patch_all_steps()
        try:
            context = AgentContext()
            agent = MarketPrepAgent("test_strategy", context=context)
            result = agent.process({"date": "2026-01-15"})

            assert isinstance(result, dict)
            assert result["status"] == "success"
            assert result["strategy"] == "test_strategy"
        finally:
            for p in patchers:
                p.stop()

    def test_process_sets_portfolio_name_from_strategy(self):
        patchers = _patch_all_steps()
        try:
            context = AgentContext()
            agent = MarketPrepAgent("momentum_cac", context=context)
            agent.process({})
            assert context.get("portfolio_name") == "momentum_cac"
        finally:
            for p in patchers:
                p.stop()

    def test_process_with_target_date(self):
        patchers = _patch_all_steps()
        try:
            context = AgentContext()
            agent = MarketPrepAgent("test_strategy", context=context)
            target_date = "2026-02-15"
            result = agent.process({"date": target_date})
            assert context.get("target_date") == target_date
            assert result["target_date"] == target_date
        finally:
            for p in patchers:
                p.stop()

    def test_process_saves_ranking_scores(self):
        patchers = _patch_all_steps()
        try:
            context = AgentContext()
            context.set("ranking_scores", {"AAPL.PA": 0.85, "MSFT.PA": 0.75})
            agent = MarketPrepAgent("test_strategy", context=context)
            result = agent.process({})
            assert result["ranking_scores"]["AAPL.PA"] == 0.85
        finally:
            for p in patchers:
                p.stop()

    def test_process_saves_watchlist(self):
        patchers = _patch_all_steps()
        try:
            context = AgentContext()
            context.set("watchlist", [
                {"ticker": "AAPL.PA", "score": 0.85},
                {"ticker": "MSFT.PA", "score": 0.75},
            ])
            agent = MarketPrepAgent("test_strategy", context=context)
            result = agent.process({})
            assert len(result["watchlist"]) == 2
        finally:
            for p in patchers:
                p.stop()

    def test_process_saves_data_history(self):
        patchers = _patch_all_steps()
        try:
            dates = pd.date_range('2026-01-01', periods=10, freq='D')
            test_data = pd.DataFrame({
                'timestamp': dates,
                'close': [100 + i for i in range(10)],
            })
            context = AgentContext()
            context.set("data_history", {"AAPL.PA": test_data})
            agent = MarketPrepAgent("test_strategy", context=context)
            result = agent.process({})
            assert "AAPL.PA" in result["data_history"]
        finally:
            for p in patchers:
                p.stop()

    def test_process_propagates_fatal_step_failure(self):
        """A fatal step (e.g. StrategyAgent) failing should return a status=error result."""
        patchers = _patch_all_steps()
        try:
            with patch("agents.market_prep.agent.StrategyAgent") as mock_strategy:
                mock_strategy.return_value = _mocked_agent(status="error")
                context = AgentContext()
                agent = MarketPrepAgent("test_strategy", context=context)
                result = agent.process({})
                assert result["status"] == "error"
        finally:
            for p in patchers:
                p.stop()

    def test_process_continues_past_non_fatal_step_failure(self):
        """A non-fatal step (e.g. WatchlistRankingAgent) failing should not abort the pipeline."""
        patchers = _patch_all_steps()
        try:
            with patch("agents.market_prep.agent.WatchlistRankingAgent") as mock_ranking:
                mock_ranking.return_value = _mocked_agent(status="error")
                context = AgentContext()
                agent = MarketPrepAgent("test_strategy", context=context)
                result = agent.process({})
                assert result["status"] == "success"
        finally:
            for p in patchers:
                p.stop()


class TestMarketPrepAgentDataSlicing:
    """Test data slicing functionality for specific dates."""

    def test_set_data_history_for_date_slices_data(self):
        context = AgentContext()
        dates = pd.date_range('2026-01-01', periods=100, freq='D')
        test_data = pd.DataFrame({
            'timestamp': dates,
            'close': [100 + i * 0.5 for i in range(len(dates))],
        })
        context.set("data_history", {"AAPL.PA": test_data})

        agent = MarketPrepAgent("test_strategy", context=context)
        target_date = "2026-02-15"
        agent._set_data_history_for_date(context, target_date)

        sliced_data = context.get("data_history")["AAPL.PA"]
        max_date = sliced_data['timestamp'].dt.date.max()
        from datetime import date
        assert max_date <= date.fromisoformat(target_date)

    def test_set_data_history_with_invalid_date_format(self):
        context = AgentContext()
        dates = pd.date_range('2026-01-01', periods=10, freq='D')
        test_data = pd.DataFrame({
            'timestamp': dates,
            'close': [100 + i for i in range(10)],
        })
        context.set("data_history", {"AAPL.PA": test_data})
        agent = MarketPrepAgent("test_strategy", context=context)

        agent._set_data_history_for_date(context, "invalid-date")

        assert len(context.get("data_history")["AAPL.PA"]) == 10


class TestMarketPrepAgentContextCleanup:
    """Test context cleanup functionality."""

    def test_cleanup_removes_intermediate_variables(self):
        context = AgentContext()
        context.set("signals", {"test": "data"})
        context.set("entry_scores", [1, 2, 3])
        context.set("watchlist", [{"ticker": "AAPL.PA"}])
        context.set("data_history", {})

        agent = MarketPrepAgent("test_strategy", context=context)
        agent._cleanup_context()

        assert context.get("signals") is None
        assert context.get("entry_scores") is None
        assert context.get("watchlist") is not None
        assert context.get("data_history") is not None

    def test_cleanup_preserves_essential_variables(self):
        context = AgentContext()
        watchlist = [{"ticker": "AAPL.PA", "score": 0.8}]
        strategy_config = {"name": "test_strategy"}

        context.set("watchlist", watchlist)
        context.set("strategy_config", strategy_config)
        context.set("data_history", {"AAPL.PA": pd.DataFrame()})

        agent = MarketPrepAgent("test_strategy", context=context)
        agent._cleanup_context()

        assert context.get("watchlist") == watchlist
        assert context.get("strategy_config") == strategy_config
        assert context.get("data_history") is not None


class TestMarketPrepAgentIntegration:
    """Integration tests using real test data fixtures."""

    def test_fixtures_available(self, test_data_dir, test_strategy_dir):
        test_parquets = list(test_data_dir.glob("*.parquet"))
        assert len(test_parquets) == 2, f"Expected 2 parquet files, found {len(test_parquets)}"

        strategy_file = test_strategy_dir / "test_premarket_strategy.yml"
        assert strategy_file.exists(), f"Test strategy not found: {strategy_file}"

        with open(strategy_file) as f:
            strategy_config = yaml.safe_load(f)

        assert strategy_config["name"] == "test_premarket"
        assert len(strategy_config["tickers"]) == 2

    def test_process_preserves_output_structure(self):
        patchers = _patch_all_steps()
        try:
            context = AgentContext()
            context.set("watchlist", [{"ticker": "AAPL.PA"}])
            context.set("ranking_scores", {"AAPL.PA": 0.8})
            context.set("ticker_scores", {"AAPL.PA": 0.8})
            context.set("strategy_config", {"indicators": ["rsi_7"]})
            context.set("alpha_names", [])
            context.set("data_history", {})

            agent = MarketPrepAgent("test_strategy", context=context)
            result = agent.process({})

            essential_keys = [
                "strategy",
                "watchlist",
                "ranking_scores",
                "ticker_scores",
                "indicators",
                "data_history",
                "orders",
            ]
            for key in essential_keys:
                assert key in result, f"Missing essential key: {key}"
        finally:
            for p in patchers:
                p.stop()
