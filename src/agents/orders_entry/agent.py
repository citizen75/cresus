"""Entry order agent for converting entry signals to executable orders."""

import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.agent import Agent
from agents.orders_entry.sub_agents import (
    CheckCashAgent,
    PositionSizingAgent,
    EntryTimingAgent,
    RiskGuardAgent,
    OrderConstructionAgent,
)
from tools.portfolio import PortfolioManager
from tools.portfolio.broker import PaperBroker
from tools.portfolio.journal import Journal


class OrdersEntryAgent(Agent):
    """Agent for converting entry opportunities to executable orders.

    Orchestrates five sub-agents to bridge entry analysis and order execution:
    1. Check Cash      — abort if insufficient cash (exit signal, not an error)
    2. Position Sizing — calculate shares based on portfolio metrics
    3. Entry Timing    — determine execution method and timing
    4. Risk Guard      — validate portfolio-level constraints
    5. Order Construction — assemble final executable orders
    """

    def __init__(
        self,
        name: str = "OrdersEntryAgent",
        context: Optional[Any] = None,
        sizing_method: str = "fractional",
        risk_percent: float = 2.0,
        execute: bool = False,
    ):
        super().__init__(name, context)
        self.sizing_method = sizing_method
        self.risk_percent = risk_percent
        self.execute = execute

    def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if input_data is None:
            input_data = {}

        entries = self.context.get("entries") or {}
        if not entries:
            return {
                "status": "success",
                "input": input_data,
                "output": {"orders": [], "orders_count": 0},
                "message": "No entry tickers to convert to orders",
            }

        portfolio_name = (
            input_data.get("portfolio_name")
            or self.context.get("portfolio_name")
            or "default"
        )
        self.context.set("portfolio_name", portfolio_name)
        self.context.set(
            "risk_constraints",
            input_data.get("risk_constraints") or self.context.get("risk_constraints") or {},
        )
        self.context.set(
            "entry_recommendations",
            [{**data, "ticker": ticker} for ticker, data in entries.items()],
        )

        # Cash gate — "exit" means stop cleanly (not enough cash), not a pipeline error.
        cash_resp = self._run_sub_agent(CheckCashAgent("CheckCashStep"), fatal=False)
        if cash_resp.get("status") != "success":
            self.logger.info(f"[ENTRY-ORDER] {cash_resp.get('message')}")
            return {
                "status": "success",
                "input": input_data,
                "output": {
                    "orders": [],
                    "orders_count": 0,
                    "message": cash_resp.get("message"),
                },
                "message": cash_resp.get("message"),
            }

        try:
            self._run_sub_agent(
                PositionSizingAgent(
                    "PositionSizingStep",
                    sizing_method=self.sizing_method,
                    risk_percent=self.risk_percent,
                )
            )
            self._run_sub_agent(EntryTimingAgent("EntryTimingStep"))
            self._run_sub_agent(RiskGuardAgent("RiskGuardStep"))
            self._run_sub_agent(OrderConstructionAgent("OrderConstructionStep"))
        except RuntimeError as e:
            return {"status": "error", "input": input_data, "output": {}, "message": str(e)}

        executable_orders = self._apply_max_daily_orders(
            self.context.get("executable_orders") or []
        )
        self.context.set("executable_orders", executable_orders)

        execution_results: List[Dict[str, Any]] = []
        if executable_orders and self.execute:
            pm = PortfolioManager(context=self.context.__dict__)
            portfolio_config = self._get_portfolio_config(pm, portfolio_name)
            if (portfolio_config or {}).get("type", "paper") == "paper":
                execution_results = self._execute_through_paper_broker(
                    executable_orders, portfolio_name, pm
                )
            self.context.set("orders_executed", True)

        return {
            "status": "success",
            "input": input_data,
            "output": {
                "orders": executable_orders,
                "count": len(executable_orders),
                "executed": len([r for r in execution_results if r.get("status") == "filled"]),
                "execution_methods": self._count_execution_methods(executable_orders),
                "total_order_value": sum(o["shares"] * o["entry_price"] for o in executable_orders),
                "total_risk": sum(o.get("risk_amount", 0) for o in executable_orders),
                "execution_results": execution_results or None,
            },
            "agents_executed": self.agents_executed,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply_max_daily_orders(self, orders: list) -> list:
        if not orders:
            return orders
        strategy_config = self.context.get("strategy_config") or {}
        max_param = (
            strategy_config.get("order", {}).get("parameters", {}).get("max_daily_orders")
        )
        if not max_param:
            return orders
        try:
            max_daily = int(
                max_param.get("formula", 999) if isinstance(max_param, dict) else max_param
            )
        except (ValueError, TypeError) as e:
            self.logger.warning(f"[ENTRY-ORDER] Could not parse max_daily_orders: {e}")
            return orders
        if len(orders) <= max_daily:
            return orders
        orders = sorted(
            orders,
            key=lambda o: o.get("metadata", {}).get("entry_score", 0),
            reverse=True,
        )
        self.logger.info(
            f"[ENTRY-ORDER] max_daily_orders={max_daily}: kept {max_daily}/{len(orders)}"
        )
        return orders[:max_daily]

    def _extract_market_metadata(self, ticker: str) -> dict:
        """Return a float-coerced copy of the latest market row for ticker."""
        day_data = self.context.get("day_data") or {}
        row = day_data.get(ticker)
        if row is None or not hasattr(row, "items"):
            return {}
        result: dict = {}
        try:
            for key, value in row.items():
                try:
                    result[key] = float(value) if value is not None else None
                except (ValueError, TypeError):
                    result[key] = value
        except Exception as e:
            self.logger.debug(f"Error extracting market metadata for {ticker}: {e}")
        return result

    def _count_execution_methods(self, orders: list) -> Dict[str, int]:
        counts = {"market": 0, "limit": 0, "scale_in": 0}
        for order in orders:
            method = order.get("execution_method", "market")
            if method in counts:
                counts[method] += 1
        return counts

    def _get_portfolio_config(
        self, pm: PortfolioManager, portfolio_name: str
    ) -> Optional[Dict[str, Any]]:
        try:
            config_path = pm.config_path
            if not config_path.exists():
                return None
            config = yaml.safe_load(config_path.read_text())
            for portfolio in config.get("portfolios", []):
                if portfolio.get("name") == portfolio_name:
                    return portfolio
            return None
        except Exception as e:
            self.logger.error(f"Error loading portfolio config: {e}")
            return None

    def _execute_through_paper_broker(
        self, orders: list, portfolio_name: str, pm: PortfolioManager
    ) -> list:
        execution_results: list = []
        broker = PaperBroker()
        orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
        journal = Journal(portfolio_name, context=self.context.__dict__)

        context_date = self.context.get("date")
        created_at_filled = None
        if context_date:
            date_str = (
                context_date if isinstance(context_date, str) else context_date.isoformat()
            )
            created_at_filled = f"{date_str}T14:00:00.000000"

        try:
            for order in orders:
                ticker = order.get("ticker")
                metadata = dict(order.get("metadata", {}))
                market_meta = self._extract_market_metadata(ticker)
                for key, value in market_meta.items():
                    if key not in metadata:
                        metadata[key] = value

                order_id = orders_mgr.add_order(
                    ticker=ticker,
                    quantity=order.get("shares"),
                    entry_price=order.get("entry_price"),
                    stop_loss=order.get("stop_loss"),
                    take_profit=order.get("take_profit"),
                    execution_method=order.get("execution_method", "market"),
                    scale_count=order.get("scale_count", 1),
                    risk_amount=order.get("risk_amount"),
                    risk_reward=order.get("risk_reward"),
                    metadata=metadata,
                )

                broker_order = {
                    "ticker": ticker,
                    "quantity": order.get("shares"),
                    "action": "BUY",
                    "price": order.get("entry_price"),
                    "stop_loss": order.get("stop_loss"),
                    "target_price": order.get("take_profit"),
                    "strategy_id": metadata.get("strategy", "unknown"),
                }
                result = broker.execute_order(broker_order)

                execution_results.append({
                    "order_id": order_id,
                    "ticker": ticker,
                    "shares": order.get("shares"),
                    "entry_price": order.get("entry_price"),
                    "status": result.status,
                    "filled_price": result.filled_price,
                    "filled_quantity": result.filled_quantity,
                    "reason": result.reason,
                })

                if result.status == "filled":
                    orders_mgr.update_order_status(order_id, "executed")
                    journal.add_transaction(
                        operation="BUY",
                        ticker=ticker,
                        quantity=result.filled_quantity,
                        price=result.filled_price,
                        fees=0,
                        stop_loss=order.get("stop_loss"),
                        notes=f"Order {order_id}: {metadata.get('strategy', 'unknown')}",
                        take_profit=order.get("take_profit"),
                        trailing_stop_distance=order.get("trailing_stop_distance"),
                        trailing_stop_pct=order.get("trailing_stop_pct"),
                        highest_price=result.filled_price,
                        created_at=created_at_filled,
                        metadata=market_meta or None,
                    )
                    self.logger.info(
                        f"Executed {result.filled_quantity} {ticker} @ ${result.filled_price:.2f}"
                    )
                else:
                    orders_mgr.update_order_status(order_id, "rejected")
                    self.logger.warning(f"Order rejected: {result.reason}")

            orders_mgr.flush()
            pm.update_portfolio_cache(portfolio_name)

        except Exception as e:
            self.logger.error(f"Error executing orders through PaperBroker: {e}")

        return execution_results
