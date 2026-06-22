"""Integration tests for BacktestAgent: run the real included agents (MarketPrepAgent ->
StrategyAgent/DataAgent/WatchlistAlphasAgent/WatchListAgent/SignalsAgent/WatchlistRankingAgent/
WatchlistScoringAgent/WatchlistSortingAgent/EntryAgent/OrdersEntryAgent/OrdersSendingAgent/
SaveWatchlistAgent/OrdersExitAgent, MarketProcessAgent -> TradingBroker, MarketCloseAgent ->
OrdersAgent) against the init/templates/strategy.yml strategy restricted to the AAPL fixture,
and check the results are internally consistent and deterministic.

Most assertions below share one backtest run (`template_backtest_run`, module-scoped)
since they each just inspect a different facet of the same deterministic result -
re-running the full pipeline per assertion would be redundant. Only the determinism
test needs two independent runs.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from .conftest import cleanup_portfolio_and_backtests, run_backtest  # noqa: F401


class TestBacktestAgentConsistency:
    """Run the real pipeline end-to-end and check result consistency."""

    def test_backtest_completes_successfully(self, template_backtest_run):
        agent, result, name = template_backtest_run

        assert result["status"] == "success", result.get("message")
        assert result["output"]["days_processed"] > 0

    def test_all_premarket_agents_execute(self, template_backtest_run):
        """Every step of MarketPrepAgent's pipeline should run on every simulated day,
        not silently get skipped."""
        agent, result, name = template_backtest_run
        assert result["status"] == "success", result.get("message")

        executed = set(agent.pre_market_flow.agents_executed)
        expected = {
            f"StrategyAgent[{name}]",
            f"DataAgent[{name}]",
            "WatchlistAlphasAgent",
            "WatchListAgent",
            "SignalsAgent",
            "WatchlistRankingAgent",
            "WatchlistScoringAgent",
            "WatchlistSortingAgent",
            "EntryAgent",
            "OrdersEntryAgent",
            "OrdersSendingAgentEntry",
            f"SaveWatchlistAgent[{name}]",
            "OrdersExitAgent",
            "OrdersSendingAgentExit",
        }
        missing = expected - executed
        assert not missing, f"Steps that never ran: {missing}"

    def test_day_count_matches_daily_results(self, template_backtest_run):
        agent, result, name = template_backtest_run
        assert result["status"] == "success", result.get("message")

        output = result["output"]
        assert output["days_processed"] == len(output["daily_results"])
        for day_result in output["daily_results"]:
            assert "date" in day_result

    def test_metrics_and_portfolio_metrics_keys_match(self, template_backtest_run):
        """output['metrics'] and output['portfolio_metrics'] are computed once and shared -
        they must never drift apart."""
        agent, result, name = template_backtest_run
        assert result["status"] == "success", result.get("message")

        output = result["output"]
        assert output.get("metrics")
        assert output.get("portfolio_metrics")
        assert output["metrics"] == output["portfolio_metrics"]

    def test_final_portfolio_and_research_present(self, template_backtest_run):
        agent, result, name = template_backtest_run
        assert result["status"] == "success", result.get("message")

        output = result["output"]
        assert "final_portfolio" in output
        assert "research" in output
        assert "identified_issues" in output["research"]

    def test_at_least_one_trade_occurs(self, template_backtest_run):
        """Sanity check that the AAPL-only template strategy actually trades over this
        date range - a regression turning this to 0 would mean entries silently broke."""
        agent, result, name = template_backtest_run
        assert result["status"] == "success", result.get("message")

        metrics = result["output"].get("portfolio_metrics") or {}
        assert metrics.get("total_trades", 0) >= 1

    def test_final_portfolio_cash_is_non_negative(self, template_backtest_run):
        """Sanity check: the simulated portfolio should never end with negative cash -
        a regression here would indicate position sizing/cash checks are broken."""
        agent, result, name = template_backtest_run
        assert result["status"] == "success", result.get("message")

        from tools.portfolio import PortfolioManager
        pm = PortfolioManager(context=agent.context.__dict__)
        cash = pm.get_portfolio_cash(name)
        assert cash >= 0

    def test_results_are_deterministic_across_runs(self, test_data_dir):
        """Running the identical backtest twice (fresh isolated portfolios) must produce
        identical metrics - no hidden randomness/non-determinism in the pipeline. This
        needs two independent runs, so it can't share `template_backtest_run`."""
        name_a = f"test_backtest_determinism_a_{uuid.uuid4().hex[:8]}"
        name_b = f"test_backtest_determinism_b_{uuid.uuid4().hex[:8]}"
        try:
            _, result_a = run_backtest(test_data_dir, name_a)
            _, result_b = run_backtest(test_data_dir, name_b)

            assert result_a["status"] == "success", result_a.get("message")
            assert result_b["status"] == "success", result_b.get("message")

            output_a = result_a["output"]
            output_b = result_b["output"]

            assert output_a["days_processed"] == output_b["days_processed"]

            metrics_a = {k: v for k, v in output_a["portfolio_metrics"].items() if k not in ("start_date", "end_date")}
            metrics_b = {k: v for k, v in output_b["portfolio_metrics"].items() if k not in ("start_date", "end_date")}
            assert metrics_a == metrics_b
        finally:
            cleanup_portfolio_and_backtests(name_a, name_a)
            cleanup_portfolio_and_backtests(name_b, name_b)
