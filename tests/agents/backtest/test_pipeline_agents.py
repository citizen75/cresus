"""Per-agent tests for the agents BacktestAgent actually invokes.

BacktestAgent.process() calls, in order:
1. StrategyAgent, DataAgent, WatchlistAlphasAgent - directly, once, before the day loop.
2. Per simulated day: MarketPrepAgent (pre_market_flow), MarketProcessAgent (market_flow),
   MarketCloseAgent (post_market_flow).
3. PortfolioMetrics and ResearchAgent - directly, once, after the day loop.

Tests 1-3 and the post-loop agents share one real backtest run (`template_backtest_run`,
see conftest.py) since they only inspect different facets of the same deterministic
output. MarketProcessAgent/MarketCloseAgent are exercised in isolation instead, with a
synthetic pending order, because the day loop's chosen dates may not always produce a
fill/expiration to assert against - a direct call makes that deterministic.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from .conftest import build_backtest_context, cleanup_portfolio_and_backtests  # noqa: F401


class TestStrategyAgentInBacktest:
    """StrategyAgent: loads strategy_config and resolves tickers into context."""

    def test_tickers_resolved_to_aapl_only(self, template_backtest_run):
        agent, result, name = template_backtest_run
        assert agent.context.get("tickers") == ["AAPL"]

    def test_strategy_config_loaded(self, template_backtest_run):
        agent, result, name = template_backtest_run
        strategy_config = agent.context.get("strategy_config")
        assert strategy_config is not None
        assert strategy_config["name"] == "cac_top_5"
        assert "ema_20_chgpct_5" in strategy_config["indicators"]


class TestDataAgentInBacktest:
    """DataAgent: loads/holds OHLCV history and computes every configured indicator."""

    def test_aapl_history_has_all_configured_indicators(self, template_backtest_run):
        agent, result, name = template_backtest_run
        data_history = agent.context.get("data_history") or {}
        assert "AAPL" in data_history

        strategy_config = agent.context.get("strategy_config")
        df = data_history["AAPL"]
        for indicator in strategy_config["indicators"]:
            # macd_12_26 is a composite indicator: calculate() decomposes it into
            # macd_line/macd_signal/macd_histogram rather than a literal "macd_12_26"
            # column.
            if indicator == "macd_12_26":
                assert "macd_line" in df.columns
                continue
            assert indicator in df.columns, f"Missing indicator column: {indicator}"

    def test_data_history_sorted_descending(self, template_backtest_run):
        agent, result, name = template_backtest_run
        df = (agent.context.get("data_history") or {})["AAPL"]
        timestamps = df["timestamp"].tolist()
        assert timestamps == sorted(timestamps, reverse=True)


class TestWatchlistAlphasAgentInBacktest:
    """WatchlistAlphasAgent: calculates alpha factor columns from strategy_config["features"]."""

    def test_alpha_names_recorded(self, template_backtest_run):
        agent, result, name = template_backtest_run
        alpha_names = agent.context.get("alpha_names") or []
        assert len(alpha_names) > 0

    def test_alpha_columns_added_to_data_history(self, template_backtest_run):
        agent, result, name = template_backtest_run
        df = (agent.context.get("data_history") or {})["AAPL"]
        alpha_names = agent.context.get("alpha_names") or []
        present = [name_ for name_ in alpha_names if name_ in df.columns]
        assert present, "No alpha columns made it into data_history"


class TestMarketPrepAgentInBacktest:
    """MarketPrepAgent: BacktestAgent's pre-market phase, auto-wired when not injected."""

    def test_auto_wired_as_premarket_phase(self, template_backtest_run):
        from agents.market_prep.agent import MarketPrepAgent
        agent, result, name = template_backtest_run
        assert isinstance(agent.pre_market_flow, MarketPrepAgent)

    def test_runs_every_substep_without_fatal_error(self, template_backtest_run):
        agent, result, name = template_backtest_run
        assert result["status"] == "success", result.get("message")
        # agents_executed is reset at the top of every .process() call (so it only
        # reflects the *last* simulated day, not an accumulation across the whole day
        # loop) - a successful backtest means the last day's 14 substeps all ran.
        assert len(agent.pre_market_flow.agents_executed) == 14


class TestMarketProcessAgentInBacktest:
    """MarketProcessAgent: executes pending orders via TradingBroker for a given date."""

    def test_market_order_gets_filled(self, test_data_dir):
        from tools.portfolio.orders import Orders
        from agents.market_process.agent import MarketProcessAgent

        name = f"test_backtest_marketprocess_{uuid.uuid4().hex[:8]}"
        try:
            context = build_backtest_context(test_data_dir, name)
            df = context.get("data_history")["AAPL"].sort_values("timestamp")
            row = df.iloc[-50]
            trading_date = row["timestamp"].date()

            orders_mgr = Orders(name, context=context.__dict__)
            orders_mgr.add_order(
                ticker="AAPL", quantity=1, entry_price=float(row["close"]),
                execution_method="market", operation="BUY",
            )
            context.set("day_data", {"AAPL": row})

            agent = MarketProcessAgent(context=context)
            result = agent.process({
                "date": trading_date.isoformat(),
                "portfolio_name": name,
                "strategy_name": name,
            })

            assert result["status"] == "success", result.get("message")
            assert result["output"]["total_executed"] >= 1
            assert result["output"]["buy_executed"] >= 1
        finally:
            cleanup_portfolio_and_backtests(name, name)

    def test_requires_date(self, test_data_dir):
        from agents.market_process.agent import MarketProcessAgent

        name = f"test_backtest_marketprocess_{uuid.uuid4().hex[:8]}"
        try:
            context = build_backtest_context(test_data_dir, name)
            agent = MarketProcessAgent(context=context)
            result = agent.process({"portfolio_name": name})
            assert result["status"] == "error"
        finally:
            cleanup_portfolio_and_backtests(name, name)


class TestMarketCloseAgentInBacktest:
    """MarketCloseAgent: expires pending orders past their expiration_date via OrdersAgent."""

    def test_pending_order_past_expiration_gets_expired(self, test_data_dir):
        from tools.portfolio.orders import Orders
        from agents.market_close.agent import MarketCloseAgent

        name = f"test_backtest_marketclose_{uuid.uuid4().hex[:8]}"
        try:
            context = build_backtest_context(test_data_dir, name)
            orders_mgr = Orders(name, context=context.__dict__)
            order_id = orders_mgr.add_order(
                ticker="AAPL", quantity=1, entry_price=100.0, execution_method="limit",
                limit_price=50.0, operation="BUY",
                created_at="2026-04-01T09:00:00", expiration_date="2026-04-02T09:00:00",
            )

            agent = MarketCloseAgent(name, context=context)
            result = agent.process({"date": "2026-04-08", "portfolio_name": name, "strategy_name": name})

            assert result["status"] == "success", result.get("message")
            assert result["output"]["expired_count"] == 1

            df = orders_mgr.load_df()
            assert df.loc[df["id"] == order_id, "status"].iloc[0] == "expired"
        finally:
            cleanup_portfolio_and_backtests(name, name)

    def test_pending_order_not_yet_expired_stays_pending(self, test_data_dir):
        from tools.portfolio.orders import Orders
        from agents.market_close.agent import MarketCloseAgent

        name = f"test_backtest_marketclose_{uuid.uuid4().hex[:8]}"
        try:
            context = build_backtest_context(test_data_dir, name)
            orders_mgr = Orders(name, context=context.__dict__)
            order_id = orders_mgr.add_order(
                ticker="AAPL", quantity=1, entry_price=100.0, execution_method="limit",
                limit_price=50.0, operation="BUY",
                created_at="2026-04-01T09:00:00", expiration_date="2026-04-10T09:00:00",
            )

            agent = MarketCloseAgent(name, context=context)
            result = agent.process({"date": "2026-04-08", "portfolio_name": name, "strategy_name": name})

            assert result["status"] == "success", result.get("message")
            assert result["output"]["expired_count"] == 0

            df = orders_mgr.load_df()
            assert df.loc[df["id"] == order_id, "status"].iloc[0] == "pending"
        finally:
            cleanup_portfolio_and_backtests(name, name)


class TestPortfolioMetricsInBacktest:
    """PortfolioMetrics: computed once after the day loop and saved as metrics/portfolio_metrics."""

    def test_expected_metric_keys_present(self, template_backtest_run):
        agent, result, name = template_backtest_run
        metrics = result["output"]["portfolio_metrics"]
        for key in (
            "total_trades", "closed_trades", "win_rate_pct", "max_drawdown_pct",
            "sharpe_ratio", "total_return_pct", "start_value", "end_value",
        ):
            assert key in metrics, f"Missing metrics key: {key}"

    def test_win_rate_is_a_valid_percentage(self, template_backtest_run):
        agent, result, name = template_backtest_run
        win_rate = result["output"]["portfolio_metrics"]["win_rate_pct"]
        assert 0.0 <= win_rate <= 100.0


class TestResearchAgentInBacktest:
    """ResearchAgent: analyzes the resulting journal/orders for issues after the day loop."""

    def test_research_output_structure(self, template_backtest_run):
        agent, result, name = template_backtest_run
        research = result["output"]["research"]
        assert "journal_analysis" in research
        assert "order_analysis" in research
        assert "identified_issues" in research
        assert "severity_level" in research
        assert "issue_count" in research
        assert research["issue_count"] == len(research["identified_issues"])
