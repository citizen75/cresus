"""Orders sending agent — persists pending orders and optionally notifies."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.agent import Agent
from tools.conversation import ConversationManager
from tools.portfolio.orders import Orders


class OrdersSendingAgent(Agent):
    """Persist executable orders and send a notification based on strategy config.

    Responsibilities:
      1. Save orders to orders.csv (controlled by ``save`` flag; skipped when
         PaperBroker already persisted them via the ``orders_executed`` context key).
      2. Send a notification to the portfolio conversation feed when
         ``order.parameters.notify.enabled`` is true in strategy config.

    Args:
        orders_key: Context key to read orders from.  Use ``"executable_orders"``
            for BUY entry orders (default) or ``"exit_orders"`` for SELL exit orders.
        save: Whether to write orders to orders.csv.

    Strategy config example::

        order:
          parameters:
            notify:
              enabled: true
    """

    def __init__(
        self,
        name: str = "OrdersSendingAgent",
        context: Optional[Any] = None,
        *,
        orders_key: str = "executable_orders",
        save: bool = True,
    ) -> None:
        super().__init__(name, context)
        self.orders_key = orders_key
        self.save = save

    def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if input_data is None:
            input_data = {}

        orders = self.context.get(self.orders_key) or []
        if not orders:
            return {
                "status": "success",
                "input": input_data,
                "output": {"saved": 0, "notified": False},
                "message": "No orders to process",
            }

        portfolio_name = self.context.get("portfolio_name") or "default"
        strategy_name = self.context.get("strategy_name") or portfolio_name

        # Save to orders.csv unless disabled or PaperBroker already persisted them
        saved = 0
        if self.save and not self.context.get("orders_executed"):
            if self.orders_key == "exit_orders":
                saved = self._save_exit_orders(orders, portfolio_name)
            else:
                saved = self._save_orders(orders, portfolio_name)
            self.logger.info(f"[ORDERS-SENDING] Saved {saved} order(s) → {portfolio_name}")

        # Notify if configured
        notified = False
        notify_cfg = (
            (self.context.get("strategy_config") or {})
            .get("order", {})
            .get("parameters", {})
            .get("notify", {})
        )
        if notify_cfg.get("enabled", False):
            self._send_notification(orders, portfolio_name, strategy_name)
            notified = True
            self.logger.info(
                f"[ORDERS-SENDING] Notification sent for {len(orders)} orders → {portfolio_name}"
            )

        return {
            "status": "success",
            "input": input_data,
            "output": {"saved": saved, "notified": notified, "count": len(orders)},
            "message": f"Processed {len(orders)} order(s): saved={saved}, notified={notified}",
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _order_key(operation: str, ticker: str, price) -> tuple:
        try:
            price_key = round(float(price), 2) if price is not None else None
        except (ValueError, TypeError):
            price_key = price
        return (operation.upper(), ticker.upper(), price_key)

    def _save_orders(self, orders: list, portfolio_name: str) -> int:
        orders_mgr = Orders(portfolio_name, context=self.context.__dict__)

        # Build dedup set from existing pending orders
        existing_df = orders_mgr.load_df()
        seen: set = set()
        if not existing_df.empty and "status" in existing_df.columns:
            pending = existing_df[existing_df["status"].str.lower() == "pending"]
            for _, row in pending.iterrows():
                seen.add(self._order_key(
                    str(row.get("operation", "BUY")),
                    str(row.get("ticker", "")),
                    row.get("entry_price"),
                ))

        context_date = self.context.get("date")
        created_at = None
        if context_date:
            date_str = (
                context_date if isinstance(context_date, str) else context_date.isoformat()
            )
            created_at = f"{date_str}T09:00:00.000000"

        saved = 0
        for order in orders:
            ticker = (order.get("ticker") or "").upper()
            entry_price = order.get("entry_price")
            operation = "BUY"
            key = self._order_key(operation, ticker, entry_price)
            if key in seen:
                self.logger.debug(
                    f"[ORDERS-SENDING] Skipping duplicate: {operation} {ticker} @ {entry_price}"
                )
                continue

            metadata = dict(order.get("metadata", {}))
            if order.get("limit_price_formula"):
                metadata["limit_price_formula"] = order["limit_price_formula"]
            for k, v in self._extract_market_metadata(ticker).items():
                if k not in metadata:
                    metadata[k] = v

            orders_mgr.add_order(
                ticker=ticker,
                quantity=order.get("shares"),
                entry_price=entry_price,
                stop_loss=order.get("stop_loss"),
                take_profit=order.get("take_profit"),
                limit_price=order.get("limit_price"),
                trailing_stop_distance=order.get("trailing_stop_distance"),
                trailing_stop_pct=order.get("trailing_stop_pct"),
                execution_method=order.get("execution_method", "market"),
                scale_count=order.get("scale_count", 1),
                risk_amount=order.get("risk_amount"),
                risk_reward=order.get("risk_reward"),
                metadata=metadata,
                created_at=created_at,
            )
            seen.add(key)
            saved += 1

        if saved:
            orders_mgr.flush()
        return saved

    def _save_exit_orders(self, orders: list, portfolio_name: str) -> int:
        """Persist SELL exit orders with dedup on (SELL, ticker, exit_price)."""
        orders_mgr = Orders(portfolio_name, context=self.context.__dict__)

        existing_df = orders_mgr.load_df()
        seen: set = set()
        if not existing_df.empty and "status" in existing_df.columns:
            pending = existing_df[existing_df["status"].str.lower() == "pending"]
            for _, row in pending.iterrows():
                seen.add(self._order_key(
                    str(row.get("operation", "SELL")),
                    str(row.get("ticker", "")),
                    row.get("entry_price"),
                ))

        context_date = self.context.get("date")
        created_at = None
        if context_date:
            date_str = (
                context_date if isinstance(context_date, str) else context_date.isoformat()
            )
            created_at = f"{date_str}T14:00:00.000000"

        saved = 0
        for order in orders:
            ticker = (order.get("ticker") or "").upper()
            exit_price = order.get("exit_price")
            quantity = order.get("quantity")

            if not ticker or exit_price is None or quantity is None:
                self.logger.warning(f"[ORDERS-SENDING] Incomplete exit order skipped: {order}")
                continue

            key = self._order_key("SELL", ticker, exit_price)
            if key in seen:
                self.logger.debug(f"[ORDERS-SENDING] Skipping duplicate: SELL {ticker} @ {exit_price}")
                continue

            metadata = {
                "exit_type": order.get("exit_type", "condition"),
                "formula": order.get("metadata", {}).get("formula", ""),
                "reason": order.get("metadata", {}).get("reason", "exit_condition_met"),
            }
            orders_mgr.add_order(
                ticker=ticker,
                quantity=int(quantity),
                entry_price=float(exit_price),
                execution_method=order.get("execution_method", "market"),
                operation="SELL",
                metadata=metadata,
                created_at=created_at,
                replace_same_day=False,
            )
            seen.add(key)
            saved += 1
            self.logger.info(
                f"[ORDERS-SENDING] SELL {int(quantity)} {ticker} @ {float(exit_price):.2f}"
                f" ({order.get('exit_type', 'condition')})"
            )

        if saved:
            orders_mgr.flush()
        return saved

    def _extract_market_metadata(self, ticker: str) -> dict:
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
            self.logger.debug(f"[ORDERS-SENDING] Market metadata error for {ticker}: {e}")
        return result

    def _send_notification(
        self, orders: List[Dict[str, Any]], portfolio_name: str, strategy_name: str
    ) -> None:
        if self.orders_key == "exit_orders":
            message = self._format_exit_message(orders, strategy_name)
        else:
            message = self._format_message(orders, strategy_name)
        ConversationManager(portfolio_name).add_notification(message)

    def _format_exit_message(
        self, orders: List[Dict[str, Any]], strategy_name: str
    ) -> str:
        timestamp = (self.context.get("timestamp") or "")[:10]
        header = f"**Exit Orders — {strategy_name}**"
        if timestamp:
            header += f" ({timestamp})"

        lines = [header, ""]
        for order in orders:
            ticker = order.get("ticker", "?")
            quantity = order.get("quantity", 0)
            exit_price = order.get("exit_price")
            exit_type = order.get("exit_type", "condition")
            method = order.get("execution_method", "market")

            price_str = f"{exit_price:.2f}" if exit_price is not None else "—"
            lines.append(f"• **{ticker}** {quantity}× @ {price_str} | *{exit_type}* | {method}")

        return "\n".join(lines)

    def _format_message(
        self, orders: List[Dict[str, Any]], strategy_name: str
    ) -> str:
        timestamp = (self.context.get("timestamp") or "")[:10]
        header = f"**New Orders — {strategy_name}**"
        if timestamp:
            header += f" ({timestamp})"

        lines = [header, ""]
        for order in orders:
            ticker = order.get("ticker", "?")
            shares = order.get("shares", 0)
            entry = order.get("entry_price")
            stop = order.get("stop_loss")
            target = order.get("take_profit")
            method = order.get("execution_method", "market")
            rr = order.get("risk_reward")

            entry_str = f"{entry:.2f}" if entry is not None else "—"
            stop_str = f"{stop:.2f}" if stop is not None else "—"
            target_str = f"{target:.2f}" if target is not None else "—"
            rr_str = f" (RR {rr:.1f}x)" if rr is not None else ""

            lines.append(
                f"• **{ticker}** {shares}× @ {entry_str}"
                f" | stop {stop_str} | target {target_str}"
                f" | *{method}*{rr_str}"
            )

        return "\n".join(lines)
