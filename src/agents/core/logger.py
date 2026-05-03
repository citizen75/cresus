"""Logger for agents."""

try:
	from loguru import logger as loguru_logger
	HAS_LOGURU = True
except ImportError:
	HAS_LOGURU = False


class AgentLogger:
	"""Logger for agents to log messages."""

	def __init__(self, agent_name: str):
		"""Initialize logger with agent name.

		Args:
			agent_name: Name of the agent using this logger
		"""
		self.agent_name = agent_name

	def log(self, message: str):
		"""Log a message.

		Args:
			message: The message to log
		"""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			loguru_logger.info(formatted_msg)
		else:
			print(formatted_msg)

	def info(self, message: str):
		"""Log an info level message."""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			loguru_logger.info(formatted_msg)
		else:
			print(f"INFO: {formatted_msg}")

	def error(self, message: str):
		"""Log an error level message."""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			loguru_logger.error(formatted_msg)
		else:
			print(f"ERROR: {formatted_msg}")

	def debug(self, message: str):
		"""Log a debug level message."""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			loguru_logger.debug(formatted_msg)
		else:
			print(f"DEBUG: {formatted_msg}")

	def warning(self, message: str):
		"""Log a warning level message."""
		formatted_msg = f"[{self.agent_name}] {message}"
		if HAS_LOGURU:
			loguru_logger.warning(formatted_msg)
		else:
			print(f"WARNING: {formatted_msg}")
