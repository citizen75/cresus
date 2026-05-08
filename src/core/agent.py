"""Agent base class for Cresus."""

import time
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

	def __init__(self, name: str, context: Optional[AgentContext] = None):
		"""Initialize agent with a name and optional context.

		Args:
			name: The name identifier for this agent
			context: Optional AgentContext. If None, a new context is created
		"""
		if not name or not isinstance(name, str):
			raise ValueError("Agent name must be a non-empty string")
		self.name = name
		if context is None:
			context = AgentContext()
		self.context = context
		# Ensure logger is set in context
		if not self.context.get("logger"):
			self.context.set("logger", AgentLogger(name))
		self.logger = self.context.get("logger")


	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process input data and return output.

		Override this method in subclasses to implement agent-specific logic.
		The base implementation returns a success response with empty output.

		Args:
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

	def run(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Run the agent with error handling, validation, timing instrumentation, and ticker tracking.

		This is the public API method. It validates inputs, calls process(),
		and handles any exceptions that occur during execution. Context is
		accessed via self.context.

		Execution time is recorded in context metadata:
		- context.metadata: Dict with structure:
			{
				"agent_metrics": [
					{"name": "AgentName", "duration_ms": 123.45, "ticker_count": 10},
					...
				]
			}

		Args:
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

		start_time = time.time()
		response = None
		try:
			self.logger.debug(f"Starting {self.name} with input keys: {list(input_data.keys())}")
			response = self.process(input_data)
			self.logger.debug(f"Completed {self.name} with status: {response.get('status')}")
			return response
		except Exception as e:
			error_msg = str(e)
			self.logger.error(f"Failed {self.name}: {error_msg}")
			response = {
				"status": STATUS_ERROR,
				"input": input_data,
				"output": {},
				"message": error_msg,
			}
			return response
		finally:
			# Record execution time in context metadata
			duration_ms = (time.time() - start_time) * 1000
			
			# Ensure metadata dict exists
			if not self.context.get("metadata"):
				self.context.set("metadata", {})
			
			metadata = self.context.get("metadata")
			
			# Count tickers being processed at this step:
			# Priority: watchlist (filtered list) > tickers (current list) > data_history (all loaded)
			ticker_count = 0
			
			# First check watchlist (filtered tickers that made it through filters)
			watchlist = self.context.get("watchlist")
			if isinstance(watchlist, list) and len(watchlist) > 0:
				ticker_count = len(watchlist)
			else:
				# Fall back to current tickers in context
				tickers = self.context.get("tickers")
				if isinstance(tickers, list) and len(tickers) > 0:
					ticker_count = len(tickers)
				else:
					# Fall back to data_history (all loaded tickers)
					if "data_history" in input_data and isinstance(input_data["data_history"], dict):
						ticker_count = len(input_data["data_history"])
					elif self.context.get("data_history"):
						context_data_history = self.context.get("data_history")
						if isinstance(context_data_history, dict):
							ticker_count = len(context_data_history)
			
			# Ensure agent_metrics list exists
			if "agent_metrics" not in metadata:
				metadata["agent_metrics"] = []
			
			# Append this agent's metrics
			metric_entry = {
				"name": self.name,
				"duration_ms": round(duration_ms, 2)
			}
			if ticker_count > 0:
				metric_entry["ticker_count"] = ticker_count
			metadata["agent_metrics"].append(metric_entry)
