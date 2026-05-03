"""Tests for Flow class."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.flow import Flow
from agents.core.context import AgentContext
from agents.core.agent import Agent


class TestFlowInitialization:
	"""Test cases for Flow initialization."""

	def test_flow_initialization(self):
		"""Test that Flow can be initialized with a name."""
		flow = Flow("test_flow")
		assert flow.name == "test_flow"
		assert flow.context is not None
		assert isinstance(flow.context, AgentContext)

	def test_flow_initialization_with_empty_name(self):
		"""Test that Flow raises error with empty name."""
		with pytest.raises(ValueError):
			Flow("")

	def test_flow_initialization_with_non_string_name(self):
		"""Test that Flow raises error with non-string name."""
		with pytest.raises(ValueError):
			Flow(123)

	def test_flow_has_logger(self):
		"""Test that Flow has a logger instance."""
		flow = Flow("test_flow")
		assert flow.logger is not None

	def test_flow_context_has_flow_name(self):
		"""Test that context stores flow name."""
		flow = Flow("my_flow")
		assert flow.context.get("flow_name") == "my_flow"

	def test_flow_has_empty_steps_initially(self):
		"""Test that Flow starts with no steps."""
		flow = Flow("test_flow")
		assert len(flow.steps) == 0

	def test_flow_has_empty_execution_history(self):
		"""Test that Flow starts with no execution history."""
		flow = Flow("test_flow")
		assert flow.execution_history == []


class TestFlowAddStep:
	"""Test cases for adding steps to Flow."""

	def test_add_step_with_agent(self):
		"""Test adding an agent step to flow."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")

		result = flow.add_step(agent)

		assert len(flow.steps) == 1
		assert flow.steps[0]["agent"] is agent
		assert result is flow  # Check method chaining

	def test_add_step_with_custom_name(self):
		"""Test adding a step with custom name."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")

		flow.add_step(agent, step_name="custom_step")

		assert flow.steps[0]["name"] == "custom_step"

	def test_add_step_defaults_to_agent_name(self):
		"""Test that step defaults to agent name."""
		flow = Flow("test_flow")
		agent = Agent("my_agent")

		flow.add_step(agent)

		assert flow.steps[0]["name"] == "my_agent"

	def test_add_step_required_flag(self):
		"""Test required flag for steps."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")

		flow.add_step(agent, required=False)

		assert flow.steps[0]["required"] is False

	def test_add_step_default_required(self):
		"""Test that steps are required by default."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")

		flow.add_step(agent)

		assert flow.steps[0]["required"] is True

	def test_add_step_with_non_agent(self):
		"""Test that adding non-agent raises TypeError."""
		flow = Flow("test_flow")

		with pytest.raises(TypeError):
			flow.add_step("not_an_agent")

	def test_add_multiple_steps(self):
		"""Test adding multiple steps."""
		flow = Flow("test_flow")
		agent1 = Agent("agent1")
		agent2 = Agent("agent2")

		flow.add_step(agent1).add_step(agent2)

		assert len(flow.steps) == 2

	def test_method_chaining(self):
		"""Test method chaining for add_step."""
		flow = Flow("test_flow")
		agent1 = Agent("agent1")
		agent2 = Agent("agent2")
		agent3 = Agent("agent3")

		result = flow.add_step(agent1).add_step(agent2).add_step(agent3)

		assert result is flow
		assert len(flow.steps) == 3


class TestFlowProcess:
	"""Test cases for flow processing."""

	def test_process_single_step(self):
		"""Test processing with single step."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		result = flow.process({"test": "data"})

		assert result.get("status") == "success"
		assert result.get("flow") == "test_flow"

	def test_process_with_none_input(self):
		"""Test processing with None input."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		result = flow.process(None)

		assert result.get("status") == "success"

	def test_process_multiple_steps(self):
		"""Test processing with multiple steps."""
		flow = Flow("test_flow")
		agent1 = Agent("agent1")
		agent2 = Agent("agent2")

		flow.add_step(agent1).add_step(agent2)
		result = flow.process({"test": "data"})

		assert result.get("status") == "success"
		assert result.get("steps_completed") == 2

	def test_process_returns_execution_history(self):
		"""Test that process returns execution history."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		result = flow.process({})

		assert "execution_history" in result
		assert len(result["execution_history"]) > 0

	def test_process_tracks_step_status(self):
		"""Test that execution history tracks step status."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		result = flow.process({})

		history = result.get("execution_history", [])
		assert history[0].get("status") == "success"

	def test_process_with_failing_required_step(self):
		"""Test flow stops on failing required step."""
		flow = Flow("test_flow")

		class FailingAgent(Agent):
			def process(self, input_data=None):
				return {"status": "error", "message": "Agent failed"}

		agent = FailingAgent("failing_agent")
		flow.add_step(agent, required=True)

		result = flow.process({})

		assert result.get("status") == "error"
		assert result.get("failed_step") == "failing_agent"

	def test_process_continues_on_optional_step_failure(self):
		"""Test flow continues on optional step failure."""
		flow = Flow("test_flow")

		class FailingAgent(Agent):
			def process(self, input_data=None):
				return {"status": "error", "message": "Agent failed"}

		class SuccessAgent(Agent):
			def process(self, input_data=None):
				return {"status": "success", "input": input_data, "output": {}}

		failing_agent = FailingAgent("failing_agent")
		success_agent = SuccessAgent("success_agent")

		flow.add_step(failing_agent, required=False)
		flow.add_step(success_agent, required=True)

		result = flow.process({})

		assert result.get("status") == "success"

	def test_process_sets_start_and_end_time(self):
		"""Test that process sets timing information."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		assert flow.start_time is None
		flow.process({})
		assert flow.start_time is not None
		assert flow.end_time is not None

	def test_process_duration_calculation(self):
		"""Test that duration is calculated correctly."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		result = flow.process({})

		assert "duration_ms" in result
		assert result["duration_ms"] >= 0


class TestFlowGetters:
	"""Test cases for getter methods."""

	def test_get_step_by_name(self):
		"""Test getting a step by name."""
		flow = Flow("test_flow")
		agent = Agent("my_agent")
		flow.add_step(agent, step_name="custom_step")

		step = flow.get_step("custom_step")

		assert step is not None
		assert step["name"] == "custom_step"

	def test_get_step_not_found(self):
		"""Test getting non-existent step returns None."""
		flow = Flow("test_flow")

		step = flow.get_step("nonexistent")

		assert step is None

	def test_get_step_result(self):
		"""Test getting step result."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		flow.process({})
		result = flow.get_step_result("test_agent")

		assert result is not None
		assert result.get("status") == "success"

	def test_get_step_result_not_executed(self):
		"""Test getting result of non-executed step."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		result = flow.get_step_result("test_agent")

		assert result is None


class TestFlowReset:
	"""Test cases for reset functionality."""

	def test_reset_clears_execution_history(self):
		"""Test that reset clears execution history."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		flow.process({})
		assert len(flow.execution_history) > 0

		flow.reset()
		assert len(flow.execution_history) == 0

	def test_reset_clears_timing(self):
		"""Test that reset clears timing information."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		flow.process({})
		assert flow.start_time is not None

		flow.reset()
		assert flow.start_time is None
		assert flow.end_time is None

	def test_reset_clears_step_results(self):
		"""Test that reset clears step results."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		flow.process({})
		assert flow.steps[0]["result"] is not None

		flow.reset()
		assert flow.steps[0]["result"] is None

	def test_reset_returns_self(self):
		"""Test that reset returns self for chaining."""
		flow = Flow("test_flow")

		result = flow.reset()

		assert result is flow


class TestFlowRun:
	"""Test cases for run method."""

	def test_run_alias_for_process(self):
		"""Test that run is an alias for process."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		result = flow.run({"test": "data"})

		assert result.get("status") == "success"
		assert result.get("flow") == "test_flow"


class TestFlowSpecialMethods:
	"""Test cases for special methods."""

	def test_flow_repr(self):
		"""Test string representation of flow."""
		flow = Flow("my_flow")
		agent1 = Agent("agent1")
		agent2 = Agent("agent2")

		flow.add_step(agent1).add_step(agent2)

		repr_str = repr(flow)

		assert "my_flow" in repr_str
		assert "2" in repr_str


class TestFlowContextSharing:
	"""Test cases for context sharing between agents."""

	def test_agents_share_context(self):
		"""Test that agents in flow share context."""
		flow = Flow("test_flow")

		class ContextWriteAgent(Agent):
			def process(self, input_data=None):
				self.context.set("shared_key", "shared_value")
				return {"status": "success", "input": input_data, "output": {}}

		class ContextReadAgent(Agent):
			def process(self, input_data=None):
				value = self.context.get("shared_key")
				return {
					"status": "success",
					"input": input_data,
					"output": {"read_value": value},
				}

		write_agent = ContextWriteAgent("writer")
		read_agent = ContextReadAgent("reader")

		flow.add_step(write_agent).add_step(read_agent)
		result = flow.process({})

		assert result.get("status") == "success"


class TestFlowErrorHandling:
	"""Test cases for error handling."""

	def test_flow_handles_agent_exception(self):
		"""Test that flow handles agent exceptions."""
		flow = Flow("test_flow")

		class ExceptionAgent(Agent):
			def process(self, input_data=None):
				raise ValueError("Test error")

		agent = ExceptionAgent("failing_agent")
		flow.add_step(agent)

		result = flow.process({})

		assert result.get("status") == "error"
		assert "Test error" in result.get("message", "")

	def test_error_response_includes_failed_step(self):
		"""Test that error response identifies failed step."""
		flow = Flow("test_flow")

		class FailingAgent(Agent):
			def process(self, input_data=None):
				return {"status": "error", "message": "Step error"}

		agent = FailingAgent("failing_agent")
		flow.add_step(agent)

		result = flow.process({})

		assert result.get("failed_step") == "failing_agent"


class TestFlowStateManagement:
	"""Test cases for state management."""

	def test_multiple_flows_isolated(self):
		"""Test that multiple flows have isolated state."""
		flow1 = Flow("flow1")
		flow2 = Flow("flow2")

		agent1 = Agent("agent1")
		agent2 = Agent("agent2")

		flow1.add_step(agent1)
		flow2.add_step(agent2)

		assert flow1.context is not flow2.context
		assert flow1.steps is not flow2.steps

	def test_flow_reusability(self):
		"""Test that flow can be reused after reset."""
		flow = Flow("test_flow")
		agent = Agent("test_agent")
		flow.add_step(agent)

		result1 = flow.process({"data": "first"})
		assert result1.get("status") == "success"

		flow.reset()

		result2 = flow.process({"data": "second"})
		assert result2.get("status") == "success"


class TestFlowDataFlow:
	"""Test cases for data flow between steps."""

	def test_step_output_becomes_next_input(self):
		"""Test that step output becomes next step input."""
		flow = Flow("test_flow")

		class DataProducerAgent(Agent):
			def process(self, input_data=None):
				return {
					"status": "success",
					"input": input_data,
					"output": {"produced": "data"},
				}

		class DataConsumerAgent(Agent):
			def process(self, input_data=None):
				return {
					"status": "success",
					"input": input_data,
					"output": {"consumed": input_data.get("produced")},
				}

		producer = DataProducerAgent("producer")
		consumer = DataConsumerAgent("consumer")

		flow.add_step(producer).add_step(consumer)
		result = flow.process({})

		assert result.get("status") == "success"


class TestFlowMetrics:
	"""Test cases for flow metrics."""

	def test_flow_tracks_total_steps(self):
		"""Test that flow tracks total steps count."""
		flow = Flow("test_flow")
		flow.add_step(Agent("agent1"))
		flow.add_step(Agent("agent2"))
		flow.add_step(Agent("agent3"))

		result = flow.process({})

		assert result.get("total_steps") == 3

	def test_flow_tracks_completed_steps(self):
		"""Test that flow tracks completed steps count."""
		flow = Flow("test_flow")
		flow.add_step(Agent("agent1"))
		flow.add_step(Agent("agent2"))

		result = flow.process({})

		assert result.get("steps_completed") == 2
