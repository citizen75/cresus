"""Bot class for automated trading with agent orchestration."""

import json
import time
from datetime import datetime
from typing import Any, Dict, Optional, List
from pathlib import Path
from enum import Enum

from .context import AgentContext
from .logger import AgentLogger

# Response status constants
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"


class BotStatus(str, Enum):
	"""Bot status enumeration."""
	ACTIVE = "active"
	INACTIVE = "inactive"
	ERROR = "error"
	STOPPED = "stopped"


class Bot:
	"""Manages automated trading bots with isolated environments.

	Implements a two-method pattern:
	- run(): Public API with error handling, validation, and instrumentation
	- process(): Override in subclasses for custom logic

	A bot can:
	- Execute trading strategies
	- Maintain isolated portfolio and watchlist
	- Call agents synchronously or asynchronously
	- Track trading performance
	"""

	def __init__(self, name: str, bot_dir: Path, context: Optional[AgentContext] = None):
		"""Initialize a bot.

		Args:
			name: Bot identifier (e.g., 'momentum_cac40')
			bot_dir: Directory to store bot data (created if doesn't exist)
			context: Optional AgentContext. If None, a new context is created
		"""
		if not name or not isinstance(name, str):
			raise ValueError("Bot name must be a non-empty string")
		self.name = name
		self.bot_dir = Path(bot_dir)
		self.bot_dir.mkdir(parents=True, exist_ok=True)

		# Create context
		if context is None:
			context = AgentContext()
		self.context = context

		# Set up logger
		if not self.context.get("logger"):
			self.context.set("logger", AgentLogger(f"bot.{name}"))
		self.logger = self.context.get("logger")

		# Bot metadata
		self.status = BotStatus.INACTIVE
		self.created_at = datetime.now()
		self.activated_at: Optional[datetime] = None
		self.deactivated_at: Optional[datetime] = None
		self.last_run: Optional[datetime] = None
		self.results: Dict[str, Any] = {}
		self.agents_executed: List[str] = []
		self.error_message: Optional[str] = None

	def get_config_path(self) -> Path:
		"""Get path to bot configuration file."""
		return self.bot_dir / "config.yml"

	def get_log_path(self, log_name: str = "bot") -> Path:
		"""Get path to bot log file.

		Args:
			log_name: Name of the log (default: 'bot')

		Returns:
			Path to log file (e.g., bot_dir/bot.log)
		"""
		return self.bot_dir / f"{log_name}.log"

	def activate(self) -> None:
		"""Mark bot as active for trading."""
		self.status = BotStatus.ACTIVE
		self.activated_at = datetime.now()
		self.logger.info(f"Bot '{self.name}' activated")

	def deactivate(self) -> None:
		"""Mark bot as inactive (paused)."""
		self.status = BotStatus.INACTIVE
		self.deactivated_at = datetime.now()
		self.logger.info(f"Bot '{self.name}' deactivated")

	def stop(self) -> None:
		"""Mark bot as stopped."""
		self.status = BotStatus.STOPPED
		self.logger.info(f"Bot '{self.name}' stopped")

	def fail(self, error_message: str) -> None:
		"""Mark bot as failed.

		Args:
			error_message: Error message describing the failure
		"""
		self.status = BotStatus.ERROR
		self.error_message = error_message
		self.logger.error(f"Bot '{self.name}' failed: {error_message}")

	def set_result(self, key: str, value: Any) -> None:
		"""Store a result value.

		Args:
			key: Result key
			value: Result value
		"""
		self.results[key] = value

	def get_result(self, key: str, default: Any = None) -> Any:
		"""Retrieve a stored result.

		Args:
			key: Result key
			default: Default value if key not found

		Returns:
			Result value or default
		"""
		return self.results.get(key, default)

	def to_dict(self) -> Dict[str, Any]:
		"""Convert bot to dictionary representation.

		Returns:
			Dictionary with bot metadata and results
		"""
		return {
			"name": self.name,
			"status": self.status.value,
			"created_at": self.created_at.isoformat(),
			"activated_at": self.activated_at.isoformat() if self.activated_at else None,
			"deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
			"last_run": self.last_run.isoformat() if self.last_run else None,
			"agents_executed": self.agents_executed,
			"results": self.results,
			"error_message": self.error_message,
		}

	def save_metadata(self) -> None:
		"""Save bot metadata to JSON file."""
		metadata_file = self.bot_dir / "metadata.json"
		with open(metadata_file, "w") as f:
			json.dump(self.to_dict(), f, indent=2, default=str)
		self.logger.debug(f"Bot metadata saved to {metadata_file}")

	def load_metadata(self) -> bool:
		"""Load bot metadata from JSON file.

		Returns:
			True if metadata was loaded, False if file doesn't exist
		"""
		metadata_file = self.bot_dir / "metadata.json"
		if not metadata_file.exists():
			return False

		try:
			with open(metadata_file, "r") as f:
				data = json.load(f)

			self.status = BotStatus(data.get("status", BotStatus.INACTIVE.value))
			if data.get("created_at"):
				self.created_at = datetime.fromisoformat(data["created_at"])
			if data.get("activated_at"):
				self.activated_at = datetime.fromisoformat(data["activated_at"])
			if data.get("deactivated_at"):
				self.deactivated_at = datetime.fromisoformat(data["deactivated_at"])
			if data.get("last_run"):
				self.last_run = datetime.fromisoformat(data["last_run"])
			self.agents_executed = data.get("agents_executed", [])
			self.results = data.get("results", {})
			self.error_message = data.get("error_message")

			self.logger.debug(f"Bot metadata loaded from {metadata_file}")
			return True

		except Exception as e:
			self.logger.error(f"Error loading metadata: {e}")
			return False

	def process(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process bot trading logic with custom implementation.

		Override this method in subclasses to implement bot-specific trading logic.
		The base implementation returns a success response with empty output.

		Args:
			params: Optional dictionary of trading parameters

		Returns:
			Response dictionary with keys:
				- status: "success" or "error"
				- params: The normalized params dictionary
				- output: Bot-specific output (empty dict by default)
				- message: Error message (only if status is "error")
		"""
		if params is None:
			params = {}
		return {
			"status": STATUS_SUCCESS,
			"params": params,
			"output": {},
		}

	def run(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Run the bot with error handling, validation, and instrumentation.

		This is the public API method. It validates inputs, calls process(),
		handles results or errors, and persists state.

		Bot can run regardless of state (ACTIVE, INACTIVE, etc).
		The state is used for workflow awareness and UI filtering, not execution control.

		Args:
			params: Optional dictionary of trading parameters

		Returns:
			Response dictionary with keys:
				- status: "success" or "error"
				- params: The normalized params dictionary
				- output: Bot output (empty dict on error)
				- message: Error message only if status is "error"
		"""
		if params is None:
			params = {}
		elif not isinstance(params, dict):
			self.logger.error(f"Invalid params type: {type(params).__name__}, expected dict")
			self.fail(f"Bot params must be a dictionary, got {type(params).__name__}")
			self.save_metadata()
			return {
				"status": STATUS_ERROR,
				"params": {},
				"output": {},
				"message": "Bot params must be a dictionary",
			}

		start_time = time.time()
		response = None

		try:
			self.last_run = datetime.now()
			self.logger.debug(f"Bot '{self.name}' running with params: {list(params.keys())}")

			response = self.process(params)

			if response.get("status") == STATUS_SUCCESS:
				output = response.get("output", {})
				for key, value in output.items():
					self.set_result(key, value)
				self.logger.debug(f"Bot '{self.name}' completed successfully")
			else:
				error_msg = response.get("message", "Process returned error status")
				self.fail(error_msg)
				self.logger.error(f"Bot '{self.name}' failed: {error_msg}")

			self.save_metadata()
			return response

		except Exception as e:
			error_msg = str(e)
			self.logger.error(f"Bot '{self.name}' exception: {error_msg}")
			self.fail(error_msg)
			self.save_metadata()

			response = {
				"status": STATUS_ERROR,
				"params": params,
				"output": {},
				"message": error_msg,
			}
			return response
