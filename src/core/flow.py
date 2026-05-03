


class Flow:
    def __init__(self, name: str):
        self.name = name
        self.steps = []
        self.context = AgentContext()  # Shared context for all agents in the flow
        self.context.set("flow_name", name)  # Store flow name in context for reference
        self.context.set("logger", AgentLogger(name))  # Add logger to context for agents to use
        self.logger = self.context.get("logger")  # Flow logger for flow-level logging
        

    def add_step(self, agent_instance: Agent):
        # Implement logic to add an agent step to the flow
        pass

    def process(self):
        # Implement the logic to run the flow using the strategy, data, and market data
        for step in self.steps:
            result = step.run()
            if result.get("status") == "error":
                self.logger.error(f"Step {step.name} failed: {result.get('message')}")
                return {"status": "error", "message": f"Step {step.name} failed: {result.get('message')}"}