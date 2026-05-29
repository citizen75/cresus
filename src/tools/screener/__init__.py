"""Screener manager for managing screener configurations and results."""

import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ScreenerConfig:
	"""Represents a screener configuration."""

	def __init__(
		self,
		name: str,
		source: Optional[str] = None,
		tickers: Optional[List[str]] = None,
		indicators: Optional[List[str]] = None,
		formula: Optional[str] = None,
		actions: Optional[Dict[str, Any]] = None,
		description: str = ""
	):
		"""Initialize screener configuration.

		Args:
			name: Screener name
			source: Universe/source name (e.g., 'cac40', 'nasdaq_100')
			tickers: List of specific tickers (alternative to source)
			indicators: List of required indicators
			formula: Filter formula for screening
			actions: Actions to trigger (alert, notification, etc.)
			description: Screener description
		"""
		self.name = name
		self.source = source
		self.tickers = tickers or []
		self.indicators = indicators or []
		self.formula = formula
		self.actions = actions or {}
		self.description = description

	def to_dict(self) -> Dict[str, Any]:
		"""Convert configuration to dictionary."""
		return {
			"name": self.name,
			"source": self.source,
			"tickers": self.tickers,
			"indicators": self.indicators,
			"formula": self.formula,
			"actions": self.actions,
			"description": self.description,
		}

	@classmethod
	def from_dict(cls, data: Dict[str, Any]) -> "ScreenerConfig":
		"""Create configuration from dictionary."""
		return cls(
			name=data.get("name", ""),
			source=data.get("source"),
			tickers=data.get("tickers"),
			indicators=data.get("indicators"),
			formula=data.get("formula"),
			actions=data.get("actions"),
			description=data.get("description", ""),
		)

	def validate(self) -> tuple[bool, str]:
		"""Validate screener configuration.

		Returns:
			Tuple of (is_valid, error_message)
		"""
		if not self.name:
			return False, "Screener name is required"

		if not self.source and not self.tickers:
			return False, "Either source or tickers must be specified"

		if not self.indicators:
			return False, "At least one indicator is required"

		if not self.formula:
			return False, "Formula is required"

		return True, ""


class ScreenerResult:
	"""Represents a screener result."""

	def __init__(
		self,
		screener_name: str,
		result_id: str,
		timestamp: datetime,
		data: List[Dict[str, Any]],
		metadata: Optional[Dict[str, Any]] = None
	):
		"""Initialize screener result.

		Args:
			screener_name: Name of the screener
			result_id: Unique result identifier
			timestamp: When the screening was run
			data: List of result rows
			metadata: Additional metadata
		"""
		self.screener_name = screener_name
		self.result_id = result_id
		self.timestamp = timestamp
		self.data = data
		self.metadata = metadata or {}

	def get_filename(self) -> str:
		"""Get result filename."""
		return f"{self.result_id}.csv"


class ScreenerManager:
	"""Manages screener configurations and results."""

	def __init__(self, db_path: Optional[Path] = None):
		"""Initialize screener manager.

		Args:
			db_path: Base database path (defaults to ~/.cresus/db)
		"""
		if db_path is None:
			db_path = Path.home() / ".cresus" / "db"

		self.base_path = Path(db_path)
		self.screeners_path = self.base_path / "screeners"

	def _get_screener_dir(self, screener_name: str) -> Path:
		"""Get directory for a screener."""
		return self.screeners_path / screener_name

	def _get_config_file(self, screener_name: str) -> Path:
		"""Get configuration file path for a screener."""
		return self._get_screener_dir(screener_name) / "screener.yml"

	def _get_results_dir(self, screener_name: str) -> Path:
		"""Get results directory for a screener."""
		return self._get_screener_dir(screener_name) / "results"

	def create_screener(self, config: ScreenerConfig) -> tuple[bool, str]:
		"""Create a new screener.

		Args:
			config: Screener configuration

		Returns:
			Tuple of (success, message)
		"""
		is_valid, error = config.validate()
		if not is_valid:
			return False, error

		screener_dir = self._get_screener_dir(config.name)
		if screener_dir.exists():
			return False, f"Screener '{config.name}' already exists"

		screener_dir.mkdir(parents=True, exist_ok=True)
		self._save_config(config)

		return True, f"Screener '{config.name}' created successfully"

	def get_screener(self, screener_name: str) -> Optional[ScreenerConfig]:
		"""Get a screener configuration.

		Args:
			screener_name: Name of the screener

		Returns:
			ScreenerConfig or None if not found
		"""
		config_file = self._get_config_file(screener_name)
		if not config_file.exists():
			return None

		try:
			with open(config_file, "r") as f:
				data = yaml.safe_load(f)
				return ScreenerConfig.from_dict(data)
		except Exception as e:
			print(f"Error loading screener: {e}")
			return None

	def list_screeners(self) -> List[str]:
		"""List all screeners.

		Returns:
			List of screener names
		"""
		if not self.screeners_path.exists():
			return []

		screeners = []
		for item in self.screeners_path.iterdir():
			if item.is_dir() and (item / "screener.yml").exists():
				screeners.append(item.name)

		return sorted(screeners)

	def delete_screener(self, screener_name: str) -> tuple[bool, str]:
		"""Delete a screener and its results.

		Args:
			screener_name: Name of the screener

		Returns:
			Tuple of (success, message)
		"""
		screener_dir = self._get_screener_dir(screener_name)
		if not screener_dir.exists():
			return False, f"Screener '{screener_name}' not found"

		try:
			import shutil
			shutil.rmtree(screener_dir)
			return True, f"Screener '{screener_name}' deleted successfully"
		except Exception as e:
			return False, f"Error deleting screener: {e}"

	def update_screener(self, config: ScreenerConfig) -> tuple[bool, str]:
		"""Update a screener configuration.

		Args:
			config: Updated screener configuration

		Returns:
			Tuple of (success, message)
		"""
		is_valid, error = config.validate()
		if not is_valid:
			return False, error

		screener_dir = self._get_screener_dir(config.name)
		if not screener_dir.exists():
			return False, f"Screener '{config.name}' not found"

		self._save_config(config)
		return True, f"Screener '{config.name}' updated successfully"

	def _save_config(self, config: ScreenerConfig) -> None:
		"""Save screener configuration to file."""
		config_file = self._get_config_file(config.name)
		config_file.parent.mkdir(parents=True, exist_ok=True)

		with open(config_file, "w") as f:
			yaml.safe_dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

	def save_result(
		self,
		screener_name: str,
		data: List[Dict[str, Any]],
		metadata: Optional[Dict[str, Any]] = None
	) -> tuple[bool, str, Optional[str]]:
		"""Save screening results.

		Args:
			screener_name: Name of the screener
			data: List of result rows
			metadata: Optional metadata

		Returns:
			Tuple of (success, message, result_id)
		"""
		screener_dir = self._get_screener_dir(screener_name)
		if not screener_dir.exists():
			return False, f"Screener '{screener_name}' not found", None

		# Generate unique result ID
		result_id = self._generate_result_id()

		results_dir = self._get_results_dir(screener_name)
		results_dir.mkdir(parents=True, exist_ok=True)

		result_file = results_dir / f"{result_id}.csv"

		try:
			if not data:
				# Create empty CSV with headers
				with open(result_file, "w", newline="") as f:
					writer = csv.writer(f)
					writer.writerow(["timestamp", "screener_name"])
				return True, f"Result saved (0 matches)", result_id

			# Write results to CSV
			fieldnames = list(data[0].keys())
			with open(result_file, "w", newline="") as f:
				writer = csv.DictWriter(f, fieldnames=fieldnames)
				writer.writeheader()
				writer.writerows(data)

			return True, f"Result saved ({len(data)} matches)", result_id
		except Exception as e:
			return False, f"Error saving result: {e}", None

	def get_result(self, screener_name: str, result_id: str) -> Optional[List[Dict[str, Any]]]:
		"""Get screening result data.

		Args:
			screener_name: Name of the screener
			result_id: Result identifier

		Returns:
			List of result rows or None if not found
		"""
		result_file = self._get_results_dir(screener_name) / f"{result_id}.csv"
		if not result_file.exists():
			return None

		try:
			with open(result_file, "r") as f:
				reader = csv.DictReader(f)
				return list(reader)
		except Exception as e:
			print(f"Error reading result: {e}")
			return None

	def list_results(self, screener_name: str) -> List[tuple[str, datetime]]:
		"""List all results for a screener.

		Args:
			screener_name: Name of the screener

		Returns:
			List of (result_id, timestamp) tuples
		"""
		results_dir = self._get_results_dir(screener_name)
		if not results_dir.exists():
			return []

		results = []
		for file in results_dir.glob("*.csv"):
			result_id = file.stem
			# Extract timestamp from result_id (format: YYYYmmdd_HHMMSS_uuid)
			try:
				timestamp_str = result_id.split("_")[0] + "_" + result_id.split("_")[1]
				timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
				results.append((result_id, timestamp))
			except (ValueError, IndexError):
				continue

		return sorted(results, key=lambda x: x[1], reverse=True)

	def delete_result(self, screener_name: str, result_id: str) -> tuple[bool, str]:
		"""Delete a screening result.

		Args:
			screener_name: Name of the screener
			result_id: Result identifier

		Returns:
			Tuple of (success, message)
		"""
		result_file = self._get_results_dir(screener_name) / f"{result_id}.csv"
		if not result_file.exists():
			return False, f"Result '{result_id}' not found"

		try:
			result_file.unlink()
			return True, f"Result '{result_id}' deleted successfully"
		except Exception as e:
			return False, f"Error deleting result: {e}"

	def clear_results(self, screener_name: str) -> tuple[bool, str]:
		"""Clear all results for a screener.

		Args:
			screener_name: Name of the screener

		Returns:
			Tuple of (success, message)
		"""
		results_dir = self._get_results_dir(screener_name)
		if not results_dir.exists():
			return True, "No results to clear"

		try:
			import shutil
			shutil.rmtree(results_dir)
			return True, "All results cleared successfully"
		except Exception as e:
			return False, f"Error clearing results: {e}"

	@staticmethod
	def _generate_result_id() -> str:
		"""Generate unique result ID."""
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		unique_id = str(uuid.uuid4())[:8]
		return f"{timestamp}_{unique_id}"
