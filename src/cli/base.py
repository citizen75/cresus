"""Base command class for all CLI commands."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rich.console import Console


@dataclass
class CommandResult:
	"""Result of command execution."""

	success: bool
	message: str
	data: Optional[Dict[str, Any]] = None
	error_type: Optional[str] = None

	def __bool__(self) -> bool:
		"""Allow using result in boolean context."""
		return self.success


class ValidationError(Exception):
	"""Raised when command arguments are invalid."""

	pass


class BaseCommand(ABC):
	"""Base class for all CLI commands.

	Subclasses should implement:
	- handle(args: str) -> CommandResult
	"""

	def __init__(self):
		"""Initialize command."""
		self.console = Console()

	@abstractmethod
	def handle(self, args: str) -> CommandResult:
		"""Handle command with arguments.

		Args:
			args: Raw argument string

		Returns:
			CommandResult with success/message/data
		"""
		pass

	def _success(self, message: str, data: Optional[Dict[str, Any]] = None) -> CommandResult:
		"""Create successful result."""
		return CommandResult(success=True, message=message, data=data)

	def _error(
		self,
		message: str,
		error_type: str = "error",
		data: Optional[Dict[str, Any]] = None
	) -> CommandResult:
		"""Create error result."""
		return CommandResult(
			success=False,
			message=message,
			data=data,
			error_type=error_type
		)

	def _validate_required_args(self, args: Dict[str, Any], required: List[str]) -> Optional[CommandResult]:
		"""Validate that required arguments are present.

		Args:
			args: Parsed arguments dict
			required: List of required argument names

		Returns:
			Error result if validation fails, None if all required args present
		"""
		missing = [arg for arg in required if not args.get(arg)]
		if missing:
			return self._error(
				f"Missing required arguments: {', '.join(missing)}",
				error_type="validation"
			)
		return None
