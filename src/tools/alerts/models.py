"""Alert data models and validation."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class AlertSource(Enum):
    """Alert trigger source types."""
    TICKER = "ticker"
    TICKERS = "tickers"
    UNIVERSE = "universe"
    PORTFOLIO = "portfolio"
    ALL_PORTFOLIOS = "all_portfolios"


class AlertNotifyTarget(Enum):
    """Alert notification target."""
    CONVERSATION = "conversation"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """Alert configuration and metadata."""
    name: str
    source: AlertSource
    source_value: Optional[str]  # ticker, universe name, portfolio name, or None for all
    formula: str
    notify: AlertNotifyTarget
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        data = asdict(self)
        data['source'] = self.source.value
        data['notify'] = self.notify.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create from dictionary (YAML deserialization)."""
        data_copy = data.copy()
        data_copy['source'] = AlertSource(data_copy['source'])
        data_copy['notify'] = AlertNotifyTarget(data_copy['notify'])
        return cls(**data_copy)


@dataclass
class AlertResult:
    """Result of alert evaluation."""
    alert_name: str
    matched: bool
    matches: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tickers_checked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
