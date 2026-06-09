"""Alert notification system for sending alert matches to conversations."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from tools.conversation import ConversationManager
from tools.portfolio.manager import PortfolioManager
from .models import Alert, AlertResult, AlertNotifyTarget

logger = logging.getLogger(__name__)


class AlertNotifier:
    """Send alert notifications to configured targets."""

    def __init__(self):
        """Initialize notifier."""
        self.logger = logger

    def send_alert(self, alert: Alert, result: AlertResult) -> None:
        """Send alert notification based on alert configuration.

        Args:
            alert: Alert configuration
            result: Alert evaluation result with matches
        """
        if not result.matched or not result.matches:
            # No matches, nothing to notify
            return

        if alert.notify == AlertNotifyTarget.CONVERSATION:
            self._send_conversation_alert(alert, result)
        elif alert.notify == AlertNotifyTarget.EMAIL:
            self._send_email_alert(alert, result)
        elif alert.notify == AlertNotifyTarget.WEBHOOK:
            self._send_webhook_alert(alert, result)

    def _send_conversation_alert(self, alert: Alert, result: AlertResult) -> None:
        """Send alert to conversation(s).

        Args:
            alert: Alert configuration
            result: Alert evaluation result
        """
        try:
            portfolios = self._get_target_portfolios(alert)

            if not portfolios:
                self.logger.warning(f"No target portfolios for alert: {alert.name}")
                return

            # Format alert message
            message = self._format_alert_message(alert, result)

            # Send to each portfolio's conversation
            for portfolio_name in portfolios:
                try:
                    manager = ConversationManager(portfolio_name)
                    manager.add_alert(message)
                    self.logger.info(
                        f"Sent alert '{alert.name}' to portfolio '{portfolio_name}': "
                        f"{len(result.matches)} match(es)"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error sending alert to portfolio '{portfolio_name}': {e}"
                    )

        except Exception as e:
            self.logger.error(f"Error in conversation alert notification: {e}")

    def _send_email_alert(self, alert: Alert, result: AlertResult) -> None:
        """Send alert via email. (Not yet implemented)

        Args:
            alert: Alert configuration
            result: Alert evaluation result
        """
        self.logger.info(
            f"Email notification for alert '{alert.name}' not yet implemented"
        )

    def _send_webhook_alert(self, alert: Alert, result: AlertResult) -> None:
        """Send alert via webhook. (Not yet implemented)

        Args:
            alert: Alert configuration
            result: Alert evaluation result
        """
        self.logger.info(
            f"Webhook notification for alert '{alert.name}' not yet implemented"
        )

    def _get_target_portfolios(self, alert: Alert) -> List[str]:
        """Determine which portfolios should receive the alert.

        Args:
            alert: Alert configuration

        Returns:
            List of portfolio names to notify
        """
        from .models import AlertSource

        if alert.source == AlertSource.PORTFOLIO:
            # Alert for specific portfolio
            return [alert.source_value] if alert.source_value else []

        elif alert.source == AlertSource.ALL_PORTFOLIOS:
            # Alert for all real portfolios
            pm = PortfolioManager()
            portfolios = pm.list_portfolios()
            return [p.get('name') for p in portfolios if p.get('type') == 'real']

        else:
            # For ticker, tickers, and universe sources, send to all real portfolios
            # This way users get notified regardless of which portfolio(s) they trade
            pm = PortfolioManager()
            portfolios = pm.list_portfolios()
            return [p.get('name') for p in portfolios if p.get('type') == 'real']

    def _format_alert_message(self, alert: Alert, result: AlertResult) -> str:
        """Format alert message for conversation.

        Args:
            alert: Alert configuration
            result: Alert evaluation result

        Returns:
            Formatted alert message
        """
        timestamp = datetime.fromisoformat(result.evaluated_at) if result.evaluated_at else datetime.now()
        time_str = timestamp.strftime('%H:%M:%S')

        # Count matches by ticker
        ticker_counts: Dict[str, int] = {}
        for match in result.matches:
            ticker = match.get('ticker', '?')
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        # Build message
        lines = [
            f"⚠️ **{alert.name}** 🚨",
            f"",
            f"**Formula:** `{alert.formula}`",
            f"**Source:** {alert.source.value}",
            f"**Matches:** {len(result.matches)} result(s)",
            f"**Time:** {time_str}",
        ]

        if alert.description:
            lines.append(f"**Note:** {alert.description}")

        # Show top tickers
        if ticker_counts:
            lines.append("")
            lines.append("**Top matches:**")
            for ticker, count in sorted(ticker_counts.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"  • {ticker}: {count} match(es)")

        if len(ticker_counts) > 5:
            lines.append(f"  ... and {len(ticker_counts) - 5} more")

        return "\n".join(lines)
