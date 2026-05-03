"""Agent base class for Cresus."""

from typing import Any, Dict
from .context import AgentContext


class Agent:
    def __init__(self, name: str):
        self.name = name

    def process(self, context: AgentContext, input_data: dict={}) -> dict:
        """Process input data and return output."""



        return {"status": "success", "input": input_data, "output": {}}


    def run(self, context: AgentContext, input_data: dict={}) -> dict:
        """Run the agent with the given context and input data."""
        try:
            return self.process(context, input_data)
        except Exception as e:
            return {"status": "error", "message": str(e)}