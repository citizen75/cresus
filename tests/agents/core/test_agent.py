"""Tests for Agent class."""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.core.agent import Agent
from agents.core.context import AgentContext


class TestAgent:
	"""Test cases for Agent class."""

	def test_agent_initialization(self):
		"""Test that Agent can be initialized with a name."""
		agent = Agent("test_agent")
		assert agent.name == "test_agent"

	def test_agent_process_returns_dict(self):
		"""Test that process() returns a dictionary."""
		agent = Agent("test_agent")
		context = AgentContext()
		result = agent.process(context)
		assert isinstance(result, dict)

	def test_agent_process_default_response(self):
		"""Test that process() returns default response structure."""
		agent = Agent("test_agent")
		context = AgentContext()
		result = agent.process(context)

		assert "status" in result
		assert result["status"] == "success"
		assert "input" in result
		assert "output" in result

	def test_agent_process_with_input_data(self):
		"""Test that process() handles input data."""
		agent = Agent("test_agent")
		context = AgentContext()
		input_data = {"key": "value", "number": 42}
		result = agent.process(context, input_data)

		assert result["input"] == input_data

	def test_agent_run_calls_process(self):
		"""Test that run() calls process()."""
		agent = Agent("test_agent")
		context = AgentContext()
		input_data = {"test": "data"}
		result = agent.run(context, input_data)

		assert result["status"] == "success"
		assert result["input"] == input_data

	def test_agent_run_with_empty_input(self):
		"""Test that run() works with empty input data."""
		agent = Agent("test_agent")
		context = AgentContext()
		result = agent.run(context)

		assert result["status"] == "success"
		assert result["input"] == {}

	def test_agent_process_empty_output(self):
		"""Test that process() returns empty output by default."""
		agent = Agent("test_agent")
		context = AgentContext()
		result = agent.process(context)

		assert "output" in result
		assert result["output"] == {}

	def test_agent_multiple_instances(self):
		"""Test that multiple Agent instances have separate state."""
		agent1 = Agent("agent1")
		agent2 = Agent("agent2")

		assert agent1.name == "agent1"
		assert agent2.name == "agent2"
		assert agent1.name != agent2.name

	def test_agent_run_handles_exception(self):
		"""Test that run() catches exceptions from process()."""
		class FailingAgent(Agent):
			def process(self, context, input_data={}):
				raise ValueError("Test error")

		agent = FailingAgent("failing_agent")
		context = AgentContext()
		result = agent.run(context)

		assert result["status"] == "error"
		assert "message" in result
		assert "Test error" in result["message"]

	def test_agent_run_with_multiple_exceptions(self):
		"""Test that run() handles different exception types."""
		class FailingAgent(Agent):
			def __init__(self, name, exception_type):
				super().__init__(name)
				self.exception_type = exception_type

			def process(self, context, input_data={}):
				if self.exception_type == "value":
					raise ValueError("Value error")
				elif self.exception_type == "key":
					raise KeyError("Key error")
				elif self.exception_type == "runtime":
					raise RuntimeError("Runtime error")

		context = AgentContext()

		# Test ValueError
		agent1 = FailingAgent("agent1", "value")
		result1 = agent1.run(context)
		assert result1["status"] == "error"
		assert "Value error" in result1["message"]

		# Test KeyError
		agent2 = FailingAgent("agent2", "key")
		result2 = agent2.run(context)
		assert result2["status"] == "error"
		assert "Key error" in result2["message"]

		# Test RuntimeError
		agent3 = FailingAgent("agent3", "runtime")
		result3 = agent3.run(context)
		assert result3["status"] == "error"
		assert "Runtime error" in result3["message"]

	def test_agent_with_context_data(self):
		"""Test that agent can access context data."""
		class ContextAwareAgent(Agent):
			def process(self, context, input_data={}):
				context_value = context.get("shared_data")
				return {
					"status": "success",
					"input": input_data,
					"output": {"context_data": context_value}
				}

		agent = ContextAwareAgent("aware_agent")
		context = AgentContext()
		context.set("shared_data", "test_value")

		result = agent.run(context, {"test": "input"})
		assert result["output"]["context_data"] == "test_value"

	def test_agent_name_types(self):
		"""Test that agent accepts different name types."""
		agent_str = Agent("string_name")
		assert agent_str.name == "string_name"

		# Agent should accept string names
		agent_underscore = Agent("agent_with_underscore")
		assert agent_underscore.name == "agent_with_underscore"

		agent_dash = Agent("agent-with-dash")
		assert agent_dash.name == "agent-with-dash"

	def test_agent_custom_subclass(self):
		"""Test that custom agent subclasses work."""
		class CustomAgent(Agent):
			def process(self, context, input_data={}):
				output = {
					"processed": True,
					"input_keys": list(input_data.keys()),
					"agent_name": self.name
				}
				return {
					"status": "success",
					"input": input_data,
					"output": output
				}

		agent = CustomAgent("custom")
		context = AgentContext()
		result = agent.run(context, {"key1": "value1", "key2": "value2"})

		assert result["output"]["processed"] is True
		assert result["output"]["agent_name"] == "custom"
		assert "key1" in result["output"]["input_keys"]
		assert "key2" in result["output"]["input_keys"]
