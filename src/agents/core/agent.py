"""Agent base class for Cresus."""

from typing import Any, Dict
from .context import AgentContext
from .logger import AgentLogger


class Agent:
	"""Base agent class for processing tasks."""

	def __init__(self, name: str):
		"""Initialize agent with a name.

		Args:
			name: The name identifier for this agent
		"""
		self.name = name
		self.logger = AgentLogger(name)

	def process(self, context: AgentContext, input_data: dict = None) -> dict:
		"""Process input data and return output.

		This method should be overridden by subclasses to implement
		the actual agent logic.

		Args:
			context: AgentContext for accessing shared resources
			input_data: Dictionary of input data

		Returns:
			Dictionary with status, input, and output keys
		"""
		if input_data is None:
			input_data = {}
		return {"status": "success", "input": input_data, "output": {}}

	def run(self, context: AgentContext, input_data: dict = None) -> dict:
		"""Run the agent with error handling.

		This method calls process() and handles any exceptions that occur.

		Args:
			context: AgentContext for accessing shared resources
			input_data: Dictionary of input data

		Returns:
			Dictionary with status and error message if exception occurs
		"""
		if input_data is None:
			input_data = {}

		try:
			return self.process(context, input_data)
		except Exception as e:
			self.logger.log(f"Error in agent {self.name}: {str(e)}")
			return {"status": "error", "message": str(e)}
