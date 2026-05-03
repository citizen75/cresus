
"""Base Flow class for orchestrating multi-agent workflows."""

import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime

# Ensure agents module is in path
agents_path = Path(__file__).parent.parent / "agents"
if str(agents_path) not in sys.path:
	sys.path.insert(0, str(agents_path))

from .context import AgentContext
from .logger import AgentLogger
from .agent import Agent


class Flow:
	"""Base class for orchestrating multi-agent workflows.

	Manages a sequence of agents that execute in order, sharing context
	and handling errors at each step.
	"""

	def __init__(self, name: str, context: Optional[AgentContext] = None):
		"""Initialize a flow.

		Args:
			name: Name of the flow
			context: Optional existing AgentContext. If None, a new context is created
		"""
		if not name or not isinstance(name, str):
			raise ValueError("Flow name must be a non-empty string")

		self.name = name
		self.steps: List[Dict[str, Any]] = []

		# Use provided context or create new one
		if context is None:
			self.context = AgentContext()
		else:
			self.context = context

		self.context.set("flow_name", name)
		# Only set logger if not already present
		if not self.context.get("logger"):
			self.context.set("logger", AgentLogger(name))
		self.logger = self.context.get("logger")
		self.execution_history: List[Dict[str, Any]] = []
		self.start_time: Optional[datetime] = None
		self.end_time: Optional[datetime] = None

	def add_step(self, agent: Agent, step_name: Optional[str] = None, required: bool = True) -> "Flow":
		"""Add an agent step to the flow.

		Args:
			agent: Agent instance to add
			step_name: Optional name for the step. If not provided, derives from agent's class name
			required: Whether step failure halts the flow

		Returns:
			Self for method chaining
		"""
		if not isinstance(agent, Agent):
			raise TypeError("step must be an Agent instance")

		# Derive step name from class name if not provided
		if step_name is None:
			class_name = agent.__class__.__name__
			# Convert CamelCase to snake_case
			snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
			# Remove 'agent' suffix if present
			if snake_case.endswith('_agent'):
				step_name = snake_case[:-6]  # Remove '_agent'
			else:
				step_name = snake_case

		step = {
			"name": step_name,
			"agent": agent,
			"required": required,
			"result": None,
			"error": None,
			"start_time": None,
			"end_time": None,
		}

		self.steps.append(step)
		self.logger.debug(f"Added step '{step['name']}' to flow '{self.name}'")
		return self

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute the flow.

		Runs all steps sequentially, sharing context between agents.
		Stops on first required step failure.

		Args:
			input_data: Initial input data for the flow

		Returns:
			Flow result with status and execution history
		"""
		if input_data is None:
			input_data = {}

		self.start_time = datetime.now()
		self.execution_history = []
		current_input = input_data

		# Store execution history in context so agents can access it
		self.context.set("execution_history", [])

		self.logger.info(f"Starting flow '{self.name}' with {len(self.steps)} steps")

		for step in self.steps:
			step["start_time"] = datetime.now()

			try:
				self.logger.debug(f"Executing step '{step['name']}'")
				agent = step["agent"]
				# Inject Flow's context into agent for execution
				agent.context = self.context
				result = agent.run(current_input)
				step["result"] = result
				step["error"] = None

				# Build execution history entry
				history_entry = {
					"step": step["name"],
					"status": result.get("status"),
					"output": result.get("output"),
				}

				# Include nested execution history if present (from sub-flows)
				if "execution_history" in result and result["execution_history"]:
					history_entry["substeps"] = result["execution_history"]

				self.execution_history.append(history_entry)

				# Update execution history in context so agents can access it
				current_history = self.context.get("execution_history") or []
				current_history.append(history_entry)
				self.context.set("execution_history", current_history)

				# Check for step failure
				if result.get("status") == "error":
					self.logger.error(f"Step '{step['name']}' failed: {result.get('message')}")

					if step["required"]:
						self.end_time = datetime.now()
						return self._build_error_response(step, result)
					else:
						self.logger.warning(f"Optional step '{step['name']}' failed, continuing")

				# Update input for next step
				current_input = result.get("output", {})

			except Exception as e:
				error_msg = str(e)
				step["error"] = error_msg
				self.logger.exception(f"Step '{step['name']}' raised exception: {error_msg}")

				if step["required"]:
					self.end_time = datetime.now()
					return {
						"status": "error",
						"flow": self.name,
						"failed_step": step["name"],
						"message": f"Step '{step['name']}' failed: {error_msg}",
						"error": error_msg,
						"execution_history": self.execution_history,
					}

			finally:
				step["end_time"] = datetime.now()

		self.end_time = datetime.now()
		return self._build_success_response()

	def _build_error_response(self, failed_step: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
		"""Build error response when a step fails.

		Args:
			failed_step: The step that failed
			result: The step result

		Returns:
			Error response dictionary
		"""
		return {
			"status": "error",
			"flow": self.name,
			"failed_step": failed_step["name"],
			"message": result.get("message", "Step failed"),
			"error": result.get("message"),
			"execution_history": self.execution_history,
		}

	def _build_success_response(self) -> Dict[str, Any]:
		"""Build success response when all steps complete.

		Returns:
			Success response dictionary
		"""
		return {
			"status": "success",
			"flow": self.name,
			"steps_completed": len([s for s in self.steps if s.get("result") is not None]),
			"total_steps": len(self.steps),
			"duration_ms": self._get_duration_ms(),
			"execution_history": self.execution_history,
		}

	def _get_duration_ms(self) -> Optional[float]:
		"""Get flow execution duration in milliseconds.

		Returns:
			Duration in milliseconds or None
		"""
		if self.start_time and self.end_time:
			delta = self.end_time - self.start_time
			return delta.total_seconds() * 1000
		return None

	def get_step(self, step_name: str) -> Optional[Dict[str, Any]]:
		"""Get a step by name.

		Args:
			step_name: Name of the step

		Returns:
			Step dictionary or None if not found
		"""
		for step in self.steps:
			if step["name"] == step_name:
				return step
		return None

	def get_step_result(self, step_name: str) -> Optional[Dict[str, Any]]:
		"""Get the result of a specific step.

		Args:
			step_name: Name of the step

		Returns:
			Step result or None
		"""
		step = self.get_step(step_name)
		return step.get("result") if step else None

	def run(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Alias for process() for backward compatibility.

		Args:
			input_data: Input data for the flow

		Returns:
			Flow result
		"""
		return self.process(input_data)

	def reset(self) -> "Flow":
		"""Reset flow state for reuse.

		Returns:
			Self for method chaining
		"""
		self.execution_history = []
		self.start_time = None
		self.end_time = None

		for step in self.steps:
			step["result"] = None
			step["error"] = None
			step["start_time"] = None
			step["end_time"] = None

		return self

	def format_execution_history(self) -> str:
		"""Format execution history as indented tree.

		Returns:
			Formatted string showing step hierarchy with statuses
		"""
		lines = []
		for entry in self.execution_history:
			step_name = entry.get("step", "unknown")
			status = entry.get("status", "unknown")
			lines.append(f"{step_name:<20} │ {status}")

			# Add substeps if present
			if "substeps" in entry:
				for substep in entry["substeps"]:
					substep_name = substep.get("step", "unknown")
					substep_status = substep.get("status", "unknown")
					lines.append(f"  - {substep_name:<16} │ {substep_status}")

		return "\n".join(lines)

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"Flow(name='{self.name}', steps={len(self.steps)})"