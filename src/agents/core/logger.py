"""Logger for agents."""

from loguru import logger


class AgentLogger:
	"""Logger for agent operations."""

	def __init__(self, name: str):
		self.name = name
		self.logger = logger

	def info(self, message: str):
		"""Log info message."""
		self.logger.info(f"[{self.name}] {message}")

	def error(self, message: str):
		"""Log error message."""
		self.logger.error(f"[{self.name}] {message}")

	def debug(self, message: str):
		"""Log debug message."""
		self.logger.debug(f"[{self.name}] {message}")

	def warning(self, message: str):
		"""Log warning message."""
		self.logger.warning(f"[{self.name}] {message}")
