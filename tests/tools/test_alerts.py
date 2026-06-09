"""Tests for alert management system."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.tools.alerts import (
    Alert,
    AlertSource,
    AlertNotifyTarget,
    AlertManager,
    AlertEvaluator,
)


class TestAlertModel:
    """Test Alert data model."""

    def test_alert_creation(self):
        """Test creating an alert."""
        alert = Alert(
            name="test_alert",
            source=AlertSource.UNIVERSE,
            source_value="etf_fr",
            formula="rsi_14[0] > 50",
            notify=AlertNotifyTarget.CONVERSATION,
        )

        assert alert.name == "test_alert"
        assert alert.source == AlertSource.UNIVERSE
        assert alert.source_value == "etf_fr"
        assert alert.enabled is True

    def test_alert_to_dict(self):
        """Test converting alert to dict."""
        alert = Alert(
            name="test",
            source=AlertSource.TICKER,
            source_value="AAPL",
            formula="close > 100",
            notify=AlertNotifyTarget.CONVERSATION,
        )

        data = alert.to_dict()
        assert data["name"] == "test"
        assert data["source"] == "ticker"  # Enum converted to value
        assert data["notify"] == "conversation"

    def test_alert_from_dict(self):
        """Test creating alert from dict."""
        data = {
            "name": "test",
            "source": "universe",
            "source_value": "cac40",
            "formula": "rsi_7[0] < 30",
            "notify": "conversation",
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        alert = Alert.from_dict(data)
        assert alert.name == "test"
        assert alert.source == AlertSource.UNIVERSE
        assert alert.notify == AlertNotifyTarget.CONVERSATION


class TestAlertManager:
    """Test AlertManager CRUD operations."""

    @pytest.fixture
    def temp_alerts_dir(self, monkeypatch):
        """Provide temporary alerts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            alerts_dir = Path(tmpdir) / "alerts"
            alerts_dir.mkdir(exist_ok=True)
            monkeypatch.setattr(
                "pathlib.Path.home",
                lambda: Path(tmpdir),
            )
            yield alerts_dir

    def test_create_alert(self, temp_alerts_dir):
        """Test creating an alert."""
        manager = AlertManager()
        # Override alerts_dir for testing
        manager.alerts_dir = temp_alerts_dir

        result = manager.create_alert(
            name="test_alert",
            source="universe",
            source_value="etf_fr",
            formula="rsi_14[0] > 50",
            notify="conversation",
            description="Test alert",
        )

        assert result["status"] == "success"
        assert "created" in result["message"].lower()

        # Verify file was created
        alert_file = temp_alerts_dir / "test_alert.yml"
        assert alert_file.exists()

    def test_create_duplicate_alert(self, temp_alerts_dir):
        """Test creating duplicate alert fails."""
        manager = AlertManager()
        manager.alerts_dir = temp_alerts_dir

        # Create first alert
        manager.create_alert(
            name="dup",
            source="ticker",
            source_value="AAPL",
            formula="close > 100",
        )

        # Try to create duplicate
        result = manager.create_alert(
            name="dup",
            source="ticker",
            source_value="MSFT",
            formula="close > 150",
        )

        assert result["status"] == "error"
        assert "already exists" in result["message"]

    def test_get_alert(self, temp_alerts_dir):
        """Test retrieving an alert."""
        manager = AlertManager()
        manager.alerts_dir = temp_alerts_dir

        # Create alert
        manager.create_alert(
            name="get_test",
            source="portfolio",
            source_value="PEA",
            formula="sha_10_red[0]==1",
        )

        # Retrieve it
        alert = manager.get_alert("get_test")
        assert alert is not None
        assert alert.name == "get_test"
        assert alert.source == AlertSource.PORTFOLIO

    def test_list_alerts(self, temp_alerts_dir):
        """Test listing alerts."""
        manager = AlertManager()
        manager.alerts_dir = temp_alerts_dir

        # Create multiple alerts
        for i in range(3):
            manager.create_alert(
                name=f"alert_{i}",
                source="ticker",
                source_value="AAPL",
                formula=f"close > {100 + i * 10}",
            )

        alerts = manager.list_alerts()
        assert len(alerts) == 3
        assert all(a.name.startswith("alert_") for a in alerts)

    def test_update_alert(self, temp_alerts_dir):
        """Test updating an alert."""
        manager = AlertManager()
        manager.alerts_dir = temp_alerts_dir

        # Create alert
        manager.create_alert(
            name="update_test",
            source="ticker",
            source_value="AAPL",
            formula="close > 100",
        )

        # Update it
        result = manager.update_alert(
            "update_test",
            formula="close > 150",
            enabled=False,
        )

        assert result["status"] == "success"

        # Verify changes
        alert = manager.get_alert("update_test")
        assert alert.formula == "close > 150"
        assert alert.enabled is False

    def test_delete_alert(self, temp_alerts_dir):
        """Test deleting an alert."""
        manager = AlertManager()
        manager.alerts_dir = temp_alerts_dir

        # Create and delete
        manager.create_alert(
            name="delete_test",
            source="ticker",
            source_value="AAPL",
            formula="close > 100",
        )

        result = manager.delete_alert("delete_test")
        assert result["status"] == "success"

        # Verify it's gone
        alert = manager.get_alert("delete_test")
        assert alert is None

    def test_invalid_source(self, temp_alerts_dir):
        """Test invalid source type."""
        manager = AlertManager()
        manager.alerts_dir = temp_alerts_dir

        result = manager.create_alert(
            name="invalid",
            source="invalid_source",
            source_value=None,
            formula="close > 100",
        )

        assert result["status"] == "error"
        assert "invalid source" in result["message"].lower()

    def test_invalid_notify_target(self, temp_alerts_dir):
        """Test invalid notify target."""
        manager = AlertManager()
        manager.alerts_dir = temp_alerts_dir

        result = manager.create_alert(
            name="invalid_notify",
            source="ticker",
            source_value="AAPL",
            formula="close > 100",
            notify="invalid_target",
        )

        assert result["status"] == "error"
        assert "invalid notify" in result["message"].lower()

    def test_update_last_run(self, temp_alerts_dir):
        """Test updating last_run timestamp."""
        manager = AlertManager()
        manager.alerts_dir = temp_alerts_dir

        # Create alert
        manager.create_alert(
            name="run_test",
            source="ticker",
            source_value="AAPL",
            formula="close > 100",
        )

        # Update last_run
        alert_before = manager.get_alert("run_test")
        assert alert_before.last_run is None

        manager.update_last_run("run_test")

        alert_after = manager.get_alert("run_test")
        assert alert_after.last_run is not None


class TestAlertEvaluator:
    """Test AlertEvaluator formula evaluation."""

    def test_evaluator_init(self):
        """Test evaluator initialization."""
        evaluator = AlertEvaluator()
        assert evaluator is not None

    def test_extract_indicators(self):
        """Test extracting indicators from formula."""
        evaluator = AlertEvaluator()

        indicators = evaluator._extract_indicators(
            "rsi_14[0] > 50 && sha_10_red[0]==1 && ema_20[-1] < close[0]"
        )

        assert "rsi_14" in indicators
        assert "sha_10_red" in indicators
        assert "ema_20" in indicators
        assert "close" in indicators

    def test_get_tickers_for_ticker(self):
        """Test getting tickers for ticker source."""
        evaluator = AlertEvaluator()

        alert = Alert(
            name="test",
            source=AlertSource.TICKER,
            source_value="AAPL",
            formula="close > 100",
            notify=AlertNotifyTarget.CONVERSATION,
        )

        tickers = evaluator._get_tickers(alert)
        assert tickers == ["AAPL"]

    def test_get_tickers_for_multiple(self):
        """Test getting multiple tickers."""
        evaluator = AlertEvaluator()

        alert = Alert(
            name="test",
            source=AlertSource.TICKERS,
            source_value="AAPL,MSFT,GOOGL",
            formula="close > 100",
            notify=AlertNotifyTarget.CONVERSATION,
        )

        tickers = evaluator._get_tickers(alert)
        assert len(tickers) == 3
        assert "AAPL" in tickers
        assert "MSFT" in tickers

    def test_get_tickers_empty_universe(self):
        """Test getting tickers from non-existent universe."""
        evaluator = AlertEvaluator()

        alert = Alert(
            name="test",
            source=AlertSource.UNIVERSE,
            source_value="nonexistent_universe",
            formula="close > 100",
            notify=AlertNotifyTarget.CONVERSATION,
        )

        tickers = evaluator._get_tickers(alert)
        assert tickers == []


class TestAlertIntegration:
    """Integration tests for alert system."""

    @pytest.fixture
    def temp_alerts_dir(self, monkeypatch):
        """Provide temporary alerts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            alerts_dir = Path(tmpdir) / "alerts"
            alerts_dir.mkdir(exist_ok=True)
            monkeypatch.setattr(
                "pathlib.Path.home",
                lambda: Path(tmpdir),
            )
            yield alerts_dir

    def test_full_workflow(self, temp_alerts_dir):
        """Test complete alert workflow."""
        manager = AlertManager()
        manager.alerts_dir = temp_alerts_dir
        evaluator = AlertEvaluator()

        # Create alert
        result = manager.create_alert(
            name="workflow_test",
            source="all_portfolios",
            source_value=None,
            formula="rsi_14[0] < 30",
            notify="conversation",
            description="Test workflow alert",
            tags=["test", "rsi"],
        )

        assert result["status"] == "success"

        # Retrieve and verify
        alert = manager.get_alert("workflow_test")
        assert alert.name == "workflow_test"
        assert alert.source == AlertSource.ALL_PORTFOLIOS
        assert "test" in alert.tags

        # Update
        manager.update_alert("workflow_test", enabled=False)
        alert = manager.get_alert("workflow_test")
        assert alert.enabled is False

        # Re-enable
        manager.update_alert("workflow_test", enabled=True)
        alert = manager.get_alert("workflow_test")
        assert alert.enabled is True

        # Cleanup
        result = manager.delete_alert("workflow_test")
        assert result["status"] == "success"
        assert manager.get_alert("workflow_test") is None
