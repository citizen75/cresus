"""Watchlist flow for managing stock watchlists.

LangChain-like flow orchestration with step-by-step execution and error handling.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable
from datetime import datetime

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from agents.core.context import AgentContext
from agents.strategy.agent import StrategyAgent
from agents.watchlist.agent import WatchListAgent


class FlowStep:
	"""Represents a single step in a flow."""

	def __init__(
		self,
		name: str,
		agent_class: type,
		agent_name: str,
		error_handler: Optional[Callable] = None,
		required: bool = True,
	):
		"""Initialize a flow step.

		Args:
			name: Step name for identification
			agent_class: Agent class to instantiate
			agent_name: Name for the agent instance
			error_handler: Optional function to handle step errors
			required: Whether step failure should halt the flow
		"""
		self.name = name
		self.agent_class = agent_class
		self.agent_name = agent_name
		self.error_handler = error_handler
		self.required = required
		self.result = None
		self.error = None
		self.start_time = None
		self.end_time = None

	def execute(self, context: AgentContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Execute the step.

		Args:
			context: Shared agent context
			input_data: Input data for this step

		Returns:
			Step result dictionary
		"""
		self.start_time = datetime.now()

		try:
			agent = self.agent_class(self.agent_name, context)
			result = agent.run(input_data)
			self.result = result
			self.error = None

			return {
				"status": result.get("status"),
				"step": self.name,
				"result": result,
			}
		except Exception as e:
			error_msg = str(e)
			self.error = error_msg

			# Call error handler if provided
			if self.error_handler:
				handler_result = self.error_handler(self.name, error_msg, context)
				if handler_result:
					return handler_result

			return {
				"status": "error",
				"step": self.name,
				"message": f"Step '{self.name}' failed: {error_msg}",
				"error": error_msg,
			}
		finally:
			self.end_time = datetime.now()

	def duration_ms(self) -> Optional[float]:
		"""Get step execution duration in milliseconds."""
		if self.start_time and self.end_time:
			delta = self.end_time - self.start_time
			return delta.total_seconds() * 1000
		return None


class WatchlistFlow:
	"""LangChain-like flow for orchestrating multi-agent watchlist workflows.

	Features:
	- Step-by-step execution with visibility
	- Error handling at each step
	- Context sharing between agents
	- Step result tracking
	- Error recovery and fallback options
	- Execution metrics and logging
	"""

	def __init__(self, strategy: str):
		"""Initialize watchlist flow with strategy.

		Args:
			strategy: Strategy name to use for watchlist generation
		"""
		self.strategy_name = strategy
		self.context = AgentContext()
		self.steps: List[FlowStep] = []
		self.execution_history: List[Dict[str, Any]] = []
		self._setup_default_steps()

	def _setup_default_steps(self) -> None:
		"""Set up default steps for watchlist flow."""
		self.add_step(
			name="strategy",
			agent_class=StrategyAgent,
			agent_name=f"StrategyAgent[{self.strategy_name}]",
			required=True,
		)

		self.add_step(
			name="watchlist",
			agent_class=WatchListAgent,
			agent_name="WatchListAgent",
			required=True,
		)

	def add_step(
		self,
		name: str,
		agent_class: type,
		agent_name: str,
		error_handler: Optional[Callable] = None,
		required: bool = True,
	) -> "WatchlistFlow":
		"""Add a step to the flow.

		Args:
			name: Step identifier
			agent_class: Agent class to use
			agent_name: Name for agent instance
			error_handler: Optional error handler function
			required: Whether step failure halts flow

		Returns:
			Self for method chaining
		"""
		step = FlowStep(name, agent_class, agent_name, error_handler, required)
		self.steps.append(step)
		return self

	def _store_strategy_result(self, step_name: str, result: Dict[str, Any]) -> None:
		"""Store strategy result in context for downstream agents.

		Args:
			step_name: Name of the step that produced the result
			result: The step result
		"""
		if step_name == "strategy":
			self.context.set("strategy_result", result.get("result", {}))

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process input data through the flow.

		Executes all steps sequentially with error handling at each step.

		Args:
			input_data: Input dictionary for the flow

		Returns:
			Final flow result with status and watchlist
		"""
		if input_data is None:
			input_data = {}

		self.execution_history = []
		current_input = input_data

		# Execute each step
		for step in self.steps:
			step_result = step.execute(self.context, current_input)
			self.execution_history.append(step_result)

			# Handle step failure
			if step_result.get("status") == "error":
				if step.required:
					return self._handle_flow_error(step_result)
				else:
					# Log error but continue
					self.context.get("logger").warning(
						f"Optional step '{step.name}' failed: {step_result.get('message')}"
					)

			# Store strategy result for watchlist agent
			self._store_strategy_result(step.name, step_result)

			# Update input for next step with step output
			if step_result.get("result"):
				current_input = step_result.get("result", {}).get("output", {})

		# Flow completed successfully
		return self._build_success_response()

	def _handle_flow_error(self, failed_step: Dict[str, Any]) -> Dict[str, Any]:
		"""Handle a required step failure.

		Args:
			failed_step: The failed step result

		Returns:
			Error response with context
		"""
		return {
			"status": "error",
			"strategy": self.strategy_name,
			"failed_step": failed_step.get("step"),
			"message": failed_step.get("message"),
			"error": failed_step.get("error"),
			"execution_history": self.execution_history,
		}

	def _build_success_response(self) -> Dict[str, Any]:
		"""Build a successful flow response.

		Returns:
			Success response with results
		"""
		watchlist = self.context.get("watchlist") or []

		return {
			"status": "success",
			"strategy": self.strategy_name,
			"watchlist": watchlist,
			"steps_completed": len([s for s in self.execution_history if s.get("status") == "success"]),
			"total_steps": len(self.steps),
			"execution_history": self.execution_history,
		}

	def get_step_result(self, step_name: str) -> Optional[Dict[str, Any]]:
		"""Get the result of a specific step.

		Args:
			step_name: Name of the step

		Returns:
			Step result or None if not found
		"""
		for step in self.steps:
			if step.name == step_name:
				return step.result
		return None

	def get_execution_summary(self) -> Dict[str, Any]:
		"""Get a summary of the flow execution.

		Returns:
			Execution summary with metrics
		"""
		total_duration = sum(
			s.duration_ms() for s in self.steps if s.duration_ms() is not None
		)

		return {
			"strategy": self.strategy_name,
			"total_steps": len(self.steps),
			"executed_steps": len(self.execution_history),
			"successful_steps": len([h for h in self.execution_history if h.get("status") == "success"]),
			"failed_steps": len([h for h in self.execution_history if h.get("status") == "error"]),
			"total_duration_ms": total_duration,
			"steps": [
				{
					"name": step.name,
					"status": "success" if not step.error else "error",
					"duration_ms": step.duration_ms(),
					"error": step.error,
				}
				for step in self.steps
			],
		}

	def run(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Alias for process() for LangChain-like interface.

		Args:
			input_data: Input data for the flow

		Returns:
			Flow result
		"""
		return self.process(input_data)

	def reset(self) -> "WatchlistFlow":
		"""Reset flow state for reuse.

		Returns:
			Self for method chaining
		"""
		self.context = AgentContext()
		self.execution_history = []
		for step in self.steps:
			step.result = None
			step.error = None
			step.start_time = None
			step.end_time = None
		return self

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"WatchlistFlow(strategy='{self.strategy_name}', steps={len(self.steps)})"
