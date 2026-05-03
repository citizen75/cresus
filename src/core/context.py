from typing import Any, Callable, Dict, List, Optional, Union


class AgentContext:
    """Context for agents to access shared resources."""
    def __init__(self):
        pass

    def set(self, key: str, value: Any) -> None:
        """Set a value in the context."""
        setattr(self, key, value)

    def get(self, key: str) -> Any:
        """Get a value from the context."""
        return getattr(self, key, None)
