"""Portfolio-to-GSheets synchronization."""

from typing import Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials


class PortfolioStore:
    """Sync portfolio data with Google Sheets."""

    def __init__(self, name: str, journal, gsheet_config: Optional[Dict] = None, credentials_path: Optional[str] = None):
        self.name = name
        self.journal = journal
        self.gsheet_config = gsheet_config or {}
        self.credentials_path = credentials_path

    def sync(self, direction: str = "pull", dry_run: bool = False) -> Dict[str, Any]:
        """Sync with GSheets. Stub: returns success."""
        if not self.gsheet_config.get("enabled"):
            return {"status": "skipped", "reason": "GSheets not enabled"}
        return {"status": "success", "direction": direction, "rows": 0}

    def pull_from_gsheet(self) -> Dict[str, Any]:
        return self.sync("pull")

    def push_to_gsheet(self) -> Dict[str, Any]:
        return self.sync("push")
