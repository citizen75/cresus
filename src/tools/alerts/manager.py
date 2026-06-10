"""Alert manager for CRUD operations and persistence."""

from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import yaml
import logging
import json

from .models import Alert, AlertSource, AlertNotifyTarget, AlertResult

logger = logging.getLogger(__name__)


class AlertManager:
    """Manage alerts: CRUD operations, persistence, and evaluation."""

    def __init__(self):
        """Initialize alert manager with storage directory."""
        self.alerts_dir = Path.home() / ".cresus" / "db" / "alerts"
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger

    def _get_alert_path(self, alert_name: str) -> Path:
        """Get file path for alert."""
        return self.alerts_dir / f"{alert_name}.yml"

    def create_alert(
        self,
        name: str,
        source: str,  # "ticker", "tickers", "universe", "portfolio", "all_portfolios"
        source_value: Optional[str],
        formula: str,
        notify: str = "conversation",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create new alert.

        Args:
            name: Alert name (must be unique)
            source: Source type
            source_value: Ticker, universe name, portfolio name, or comma-separated tickers
            formula: DSL formula to evaluate
            notify: Notification target (conversation, email, webhook)
            description: Optional description
            tags: Optional tags for grouping

        Returns:
            Status dict with created alert
        """
        alert_path = self._get_alert_path(name)

        if alert_path.exists():
            return {
                "status": "error",
                "message": f"Alert '{name}' already exists",
            }

        try:
            # Validate source
            try:
                alert_source = AlertSource(source)
            except ValueError:
                return {
                    "status": "error",
                    "message": f"Invalid source: {source}. Must be one of: {', '.join([s.value for s in AlertSource])}",
                }

            try:
                notify_target = AlertNotifyTarget(notify)
            except ValueError:
                return {
                    "status": "error",
                    "message": f"Invalid notify target: {notify}. Must be one of: {', '.join([t.value for t in AlertNotifyTarget])}",
                }

            alert = Alert(
                name=name,
                source=alert_source,
                source_value=source_value,
                formula=formula,
                notify=notify_target,
                description=description,
                tags=tags or [],
            )

            self._save_alert(alert)
            self.logger.info(f"Created alert: {name}")

            return {
                "status": "success",
                "message": f"Alert '{name}' created",
                "alert": alert.to_dict(),
            }

        except Exception as e:
            self.logger.error(f"Error creating alert {name}: {e}")
            return {
                "status": "error",
                "message": f"Failed to create alert: {str(e)}",
            }

    def get_alert(self, alert_name: str) -> Optional[Alert]:
        """Get alert by name."""
        alert_path = self._get_alert_path(alert_name)

        if not alert_path.exists():
            return None

        try:
            with open(alert_path, 'r') as f:
                data = yaml.safe_load(f)
                return Alert.from_dict(data)
        except Exception as e:
            self.logger.error(f"Error loading alert {alert_name}: {e}")
            return None

    def list_alerts(self, enabled_only: bool = False) -> List[Alert]:
        """List all alerts."""
        alerts = []

        for alert_file in self.alerts_dir.glob("*.yml"):
            try:
                with open(alert_file, 'r') as f:
                    data = yaml.safe_load(f)
                    alert = Alert.from_dict(data)
                    if not enabled_only or alert.enabled:
                        alerts.append(alert)
            except Exception as e:
                self.logger.error(f"Error loading {alert_file.name}: {e}")

        return sorted(alerts, key=lambda a: a.name)

    def update_alert(self, alert_name: str, **kwargs) -> Dict[str, Any]:
        """Update alert fields."""
        alert = self.get_alert(alert_name)

        if not alert:
            return {
                "status": "error",
                "message": f"Alert '{alert_name}' not found",
            }

        try:
            # Update allowed fields
            for key in ['formula', 'enabled', 'description', 'tags', 'notify', 'source', 'source_value']:
                if key in kwargs:
                    if key == 'notify' and isinstance(kwargs[key], str):
                        setattr(alert, key, AlertNotifyTarget(kwargs[key]))
                    else:
                        setattr(alert, key, kwargs[key])

            alert.updated_at = datetime.now().isoformat()
            self._save_alert(alert)

            return {
                "status": "success",
                "message": f"Alert '{alert_name}' updated",
                "alert": alert.to_dict(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to update alert: {str(e)}",
            }

    def delete_alert(self, alert_name: str) -> Dict[str, Any]:
        """Delete alert."""
        alert_path = self._get_alert_path(alert_name)

        if not alert_path.exists():
            return {
                "status": "error",
                "message": f"Alert '{alert_name}' not found",
            }

        try:
            alert_path.unlink()
            self.logger.info(f"Deleted alert: {alert_name}")
            return {
                "status": "success",
                "message": f"Alert '{alert_name}' deleted",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete alert: {str(e)}",
            }

    def _save_alert(self, alert: Alert) -> None:
        """Save alert to YAML file."""
        alert_path = self._get_alert_path(alert.name)

        with open(alert_path, 'w') as f:
            yaml.dump(alert.to_dict(), f, default_flow_style=False, sort_keys=False)

    def update_last_run(self, alert_name: str) -> None:
        """Update last_run timestamp for alert."""
        alert = self.get_alert(alert_name)
        if alert:
            alert.last_run = datetime.now().isoformat()
            self._save_alert(alert)

    def save_alert_result(self, alert_name: str, result: AlertResult) -> Dict[str, Any]:
        """Save alert evaluation result to disk.

        Args:
            alert_name: Name of the alert
            result: AlertResult object with matches and metadata

        Returns:
            Status dict
        """
        try:
            # Create alert results directory: ~/.cresus/db/alerts/{alert_name}/
            results_dir = self.alerts_dir / alert_name / "results"
            results_dir.mkdir(parents=True, exist_ok=True)

            # Save result with timestamp
            timestamp = datetime.fromisoformat(result.evaluated_at).strftime("%Y%m%d_%H%M%S")
            result_file = results_dir / f"result_{timestamp}.json"

            # Convert result to dict with proper serialization
            result_data = {
                "alert_name": result.alert_name,
                "matched": result.matched,
                "matches": result.matches,
                "error": result.error,
                "evaluated_at": result.evaluated_at,
                "tickers_checked": result.tickers_checked,
            }

            with open(result_file, 'w') as f:
                json.dump(result_data, f, indent=2, default=str)

            self.logger.info(f"Saved alert result for '{alert_name}' to {result_file}")
            return {"status": "success", "path": str(result_file)}

        except Exception as e:
            self.logger.error(f"Error saving alert result for '{alert_name}': {e}")
            return {"status": "error", "message": str(e)}

    def get_alert_results(self, alert_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get saved alert results.

        Args:
            alert_name: Name of the alert
            limit: Maximum number of results to return

        Returns:
            List of result dicts, sorted by most recent first
        """
        try:
            results_dir = self.alerts_dir / alert_name / "results"
            if not results_dir.exists():
                return []

            # Find all result files
            result_files = sorted(results_dir.glob("result_*.json"), reverse=True)[:limit]
            results = []

            for result_file in result_files:
                try:
                    with open(result_file, 'r') as f:
                        result_data = json.load(f)
                        results.append(result_data)
                except Exception as e:
                    self.logger.error(f"Error loading result from {result_file}: {e}")
                    continue

            return results

        except Exception as e:
            self.logger.error(f"Error getting alert results for '{alert_name}': {e}")
            return []

    def delete_alert_result(self, alert_name: str, result_id: str) -> Dict[str, Any]:
        """Delete a specific alert result.

        Args:
            alert_name: Name of the alert
            result_id: Result ID (timestamp format: YYYYmmdd_HHMMSS)

        Returns:
            Status dict
        """
        try:
            results_dir = self.alerts_dir / alert_name / "results"
            result_file = results_dir / f"result_{result_id}.json"

            if not result_file.exists():
                return {"status": "error", "message": f"Result not found: {result_id}"}

            result_file.unlink()
            self.logger.info(f"Deleted alert result: {alert_name}/{result_id}")
            return {"status": "success", "message": f"Deleted result {result_id}"}

        except Exception as e:
            self.logger.error(f"Error deleting alert result '{alert_name}/{result_id}': {e}")
            return {"status": "error", "message": str(e)}
