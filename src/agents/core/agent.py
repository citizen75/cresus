"""Agent base class for Cresus."""

from typing import Any, Dict, Optional
from .context import AgentContext
from .logger import AgentLogger

# Response status constants
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"


class Agent:
	"""Base agent class for processing tasks.

	Implements a two-method pattern:
	- run(): Public API with error handling and validation
	- process(): Override in subclasses for custom logic
	"""

	def __init__(self, name: str):
		"""Initialize agent with a name.

		Args:
			name: The name identifier for this agent
		"""
		if not name or not isinstance(name, str):
			raise ValueError("Agent name must be a non-empty string")
		self.name = name
		self.logger = AgentLogger(name)

	def process(self, context: AgentContext, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process input data and return output.

		Override this method in subclasses to implement agent-specific logic.
		The base implementation returns a success response with empty output.

		Args:
			context: AgentContext for accessing shared resources
			input_data: Optional dictionary of input data (normalized to {} if None)

		Returns:
			Response dictionary with keys:
				- status: "success" or "error"
				- input: The normalized input data dict
				- output: Agent-specific output (empty dict by default)
				- message: Error message (only if status is "error")
		"""
		if input_data is None:
			input_data = {}
		return {
			"status": STATUS_SUCCESS,
			"input": input_data,
			"output": {},
		}

	def run(self, context: AgentContext, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Run the agent with error handling and validation.

		This is the public API method. It validates inputs, calls process(),
		and handles any exceptions that occur during execution.

		Args:
			context: AgentContext for accessing shared resources
			input_data: Optional dictionary of input data

		Returns:
			Response dictionary with keys:
				- status: "success" or "error"
				- input: The normalized input data dict (empty dict on error)
				- output: Agent output (empty dict on error)
				- message: Error message only if status is "error"

		Raises:
			Logs exceptions but does not raise - always returns a response dict
		"""
		if not isinstance(context, AgentContext):
			self.logger.error(f"Invalid context type: {type(context).__name__}")
			return {
				"status": STATUS_ERROR,
				"input": {},
				"output": {},
				"message": "Invalid agent context",
			}

		if input_data is None:
			input_data = {}
		elif not isinstance(input_data, dict):
			self.logger.error(f"Invalid input type: {type(input_data).__name__}, expected dict")
			return {
				"status": STATUS_ERROR,
				"input": {},
				"output": {},
				"message": "Input data must be a dictionary",
			}

		try:
			self.logger.debug(f"Starting {self.name} with input keys: {list(input_data.keys())}")
			response = self.process(context, input_data)
			self.logger.debug(f"Completed {self.name} with status: {response.get('status')}")
			return response
		except Exception as e:
			error_msg = str(e)
			self.logger.error(f"Failed {self.name}: {error_msg}")
			return {
				"status": STATUS_ERROR,
				"input": input_data,
				"output": {},
				"message": error_msg,
			}
