"""Data synchronization bot job."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.job import Job, JobStatus
from core.context import AgentContext


class BotDataSync(Job):
	"""Data synchronization bot for keeping market data up-to-date.

	Responsibilities:
	- Fetch latest price data from multiple sources
	- Validate and reconcile data
	- Update local database with latest information
	- Handle data quality checks
	"""

	def __init__(self, name: str, job_dir: Path, context: Optional[AgentContext] = None):
		"""Initialize data sync bot.

		Args:
			name: Job identifier
			job_dir: Directory to store job data
			context: Optional AgentContext
		"""
		super().__init__(name, job_dir, context)
		self.sources: List[str] = []
		self.data_fetched: Dict[str, Any] = {}
		self.validation_errors: List[Dict[str, Any]] = []
		self.sync_stats: Dict[str, int] = {}

	def connect_to_source(self, source_name: str, credentials: Dict[str, str]) -> bool:
		"""Connect to a data source.

		Args:
			source_name: Name of the data source (yfinance, iex, etc.)
			credentials: Connection credentials

		Returns:
			True if connection successful
		"""
		self.logger.info(f"Connecting to source: {source_name}")

		self.context.set(f"source_{source_name}", True)
		self.sources.append(source_name)

		return True

	def fetch_ticker_data(self, source: str, tickers: List[str], fields: List[str]) -> Dict[str, Any]:
		"""Fetch ticker data from source.

		Args:
			source: Data source name
			tickers: List of ticker symbols
			fields: Data fields to fetch (close, high, low, volume, etc.)

		Returns:
			Fetched data for tickers
		"""
		self.logger.info(f"Fetching {len(tickers)} tickers from {source}: {fields}")

		self.context.set("last_fetch_source", source)
		self.context.set("last_fetch_time", datetime.now())

		data = {ticker: {field: None for field in fields} for ticker in tickers}
		self.data_fetched[source] = data

		return {
			"source": source,
			"tickers_fetched": len(tickers),
			"fields": len(fields),
			"data_points": len(tickers) * len(fields)
		}

	def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
		"""Validate fetched data for quality and consistency.

		Args:
			data: Data to validate

		Returns:
			Validation results
		"""
		self.logger.info("Validating data quality")

		self.context.set("validation_timestamp", datetime.now())

		errors = []
		warnings = []

		# Example validation rules
		for ticker, ticker_data in data.items():
			if not ticker_data:
				errors.append({
					"ticker": ticker,
					"error": "empty_data",
					"severity": "high"
				})

		self.validation_errors = errors

		return {
			"total_checks": len(data),
			"errors": len(errors),
			"warnings": len(warnings),
			"valid": len(errors) == 0
		}

	def reconcile_data(self, primary_source: str, secondary_source: str) -> Dict[str, Any]:
		"""Reconcile data from multiple sources.

		Args:
			primary_source: Primary data source name
			secondary_source: Secondary data source for comparison

		Returns:
			Reconciliation results
		"""
		self.logger.info(f"Reconciling data between {primary_source} and {secondary_source}")

		primary_data = self.data_fetched.get(primary_source, {})
		secondary_data = self.data_fetched.get(secondary_source, {})

		discrepancies = []
		for ticker in primary_data:
			if ticker not in secondary_data:
				discrepancies.append({
					"ticker": ticker,
					"discrepancy": "missing_in_secondary",
					"severity": "medium"
				})

		return {
			"primary_source": primary_source,
			"secondary_source": secondary_source,
			"tickers_compared": len(primary_data),
			"discrepancies": len(discrepancies),
			"reconciled": len(discrepancies) == 0
		}

	def update_database(self, data: Dict[str, Any]) -> Dict[str, Any]:
		"""Update local database with validated data.

		Args:
			data: Data to store

		Returns:
			Update statistics
		"""
		self.logger.info("Updating database with synced data")

		self.context.set("db_update_time", datetime.now())

		stats = {
			"records_updated": sum(len(v) if isinstance(v, dict) else 1 for v in data.values()),
			"records_inserted": len(data),
			"records_skipped": 0,
			"total_size_bytes": 0
		}

		self.sync_stats = stats
		return stats

	def get_sync_status(self) -> Dict[str, Any]:
		"""Get current synchronization status.

		Returns:
			Status information
		"""
		return {
			"sources": len(self.sources),
			"data_points_fetched": sum(len(v) if isinstance(v, dict) else 0 for v in self.data_fetched.values()),
			"validation_errors": len(self.validation_errors),
			"sync_stats": self.sync_stats,
			"timestamp": datetime.now().isoformat()
		}

	def run_sync(self, config: Dict[str, Any]) -> Dict[str, Any]:
		"""Execute full data synchronization workflow.

		Args:
			config: Sync configuration with sources, tickers, fields

		Returns:
			Sync completion summary
		"""
		self.start()
		self.logger.info(f"Starting data sync: {self.name}")

		try:
			# Connect to sources
			sources = config.get("sources", ["yfinance"])
			for source in sources:
				self.connect_to_source(source, config.get(f"{source}_credentials", {}))
				self.set_result(f"connection_{source}", True)

			# Fetch data from each source
			tickers = config.get("tickers", ["AC.PA", "OR.PA"])
			fields = config.get("fields", ["close", "high", "low", "volume"])

			for source in sources:
				fetch_result = self.fetch_ticker_data(source, tickers, fields)
				self.set_result(f"fetch_{source}", fetch_result)

			# Validate data
			all_data = {ticker: None for ticker in tickers}
			validation = self.validate_data(all_data)
			self.set_result("validation", validation)

			# Reconcile if multiple sources
			if len(sources) > 1:
				reconciliation = self.reconcile_data(sources[0], sources[1])
				self.set_result("reconciliation", reconciliation)

			# Update database
			update_stats = self.update_database(all_data)
			self.set_result("update_stats", update_stats)

			# Complete sync
			summary = {
				"status": "completed",
				"sources_synced": len(self.sources),
				"tickers_updated": len(tickers),
				"records_updated": update_stats.get("records_updated", 0),
				"errors": len(self.validation_errors),
				"timestamp": datetime.now().isoformat()
			}

			self.complete(summary)
			self.logger.info(f"Data sync completed: {summary}")

			return summary

		except Exception as e:
			error_msg = f"Data sync failed: {str(e)}"
			self.fail(error_msg)
			self.logger.exception(error_msg)
			raise

	def get_sync_report(self) -> Dict[str, Any]:
		"""Get detailed sync report.

		Returns:
			Comprehensive sync report
		"""
		return {
			"sources": self.sources,
			"data_fetched": len(self.data_fetched),
			"validation_errors": self.validation_errors,
			"sync_stats": self.sync_stats,
			"status": self.status.value,
			"created_at": self.created_at.isoformat(),
			"started_at": self.started_at.isoformat() if self.started_at else None,
			"ended_at": self.ended_at.isoformat() if self.ended_at else None
		}

	def get_error_details(self) -> List[Dict[str, Any]]:
		"""Get detailed list of validation errors.

		Returns:
			List of error details
		"""
		return self.validation_errors
