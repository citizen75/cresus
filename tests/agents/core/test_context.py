"""Tests for AgentContext class."""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.core.context import AgentContext


class TestAgentContext:
	"""Test cases for AgentContext."""

	def test_context_initialization(self):
		"""Test that AgentContext can be initialized."""
		context = AgentContext()
		assert context is not None

	def test_set_and_get_string_value(self):
		"""Test setting and getting a string value."""
		context = AgentContext()
		context.set("key", "value")
		assert context.get("key") == "value"

	def test_set_and_get_integer_value(self):
		"""Test setting and getting an integer value."""
		context = AgentContext()
		context.set("count", 42)
		assert context.get("count") == 42

	def test_set_and_get_dict_value(self):
		"""Test setting and getting a dictionary value."""
		context = AgentContext()
		test_dict = {"nested": "value", "number": 123}
		context.set("data", test_dict)
		assert context.get("data") == test_dict
		assert context.get("data")["nested"] == "value"

	def test_set_and_get_list_value(self):
		"""Test setting and getting a list value."""
		context = AgentContext()
		test_list = [1, 2, 3, "four"]
		context.set("items", test_list)
		assert context.get("items") == test_list

	def test_get_nonexistent_key_returns_none(self):
		"""Test that getting a non-existent key returns None."""
		context = AgentContext()
		assert context.get("nonexistent") is None

	def test_set_overwrites_existing_value(self):
		"""Test that setting a key overwrites the previous value."""
		context = AgentContext()
		context.set("key", "value1")
		context.set("key", "value2")
		assert context.get("key") == "value2"

	def test_multiple_keys(self):
		"""Test setting and getting multiple keys."""
		context = AgentContext()
		context.set("key1", "value1")
		context.set("key2", "value2")
		context.set("key3", "value3")

		assert context.get("key1") == "value1"
		assert context.get("key2") == "value2"
		assert context.get("key3") == "value3"

	def test_set_none_value(self):
		"""Test setting a None value."""
		context = AgentContext()
		context.set("key", None)
		assert context.get("key") is None

	def test_set_and_get_complex_object(self):
		"""Test setting and getting a complex object."""
		class CustomObj:
			def __init__(self, name):
				self.name = name

		context = AgentContext()
		obj = CustomObj("test")
		context.set("obj", obj)
		retrieved = context.get("obj")
		assert retrieved.name == "test"

	def test_context_isolation(self):
		"""Test that different contexts are isolated."""
		context1 = AgentContext()
		context2 = AgentContext()

		context1.set("key", "value1")
		context2.set("key", "value2")

		assert context1.get("key") == "value1"
		assert context2.get("key") == "value2"

	def test_boolean_values(self):
		"""Test setting and getting boolean values."""
		context = AgentContext()
		context.set("flag_true", True)
		context.set("flag_false", False)

		assert context.get("flag_true") is True
		assert context.get("flag_false") is False

	def test_float_values(self):
		"""Test setting and getting float values."""
		context = AgentContext()
		context.set("pi", 3.14159)
		assert context.get("pi") == 3.14159
