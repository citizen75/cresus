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
    
    def get_agent_timings(self) -> List[Dict[str, Any]]:
        """Get all recorded agent execution timings.
        
        Returns:
            List of dicts with structure:
            [
                {"name": "AgentName", "duration_ms": 123.45},
                ...
            ]
        """
        metadata = self.get("metadata") or {}
        return metadata.get("agent_timings", [])
    
    def print_agent_timings(self) -> None:
        """Print a formatted summary of agent execution times."""
        timings = self.get_agent_timings()
        if not timings:
            print("No agent timings recorded")
            return
        
        print("\n" + "=" * 80)
        print("Agent Execution Times")
        print("=" * 80)
        
        total_ms = sum(t["duration_ms"] for t in timings)
        
        # Sort by duration descending
        sorted_timings = sorted(timings, key=lambda x: x["duration_ms"], reverse=True)
        
        for timing in sorted_timings:
            name = timing["name"]
            duration = timing["duration_ms"]
            pct = (duration / total_ms * 100) if total_ms > 0 else 0
            print(f"  {name:50s} {duration:8.2f}ms ({pct:5.1f}%)")
        
        print("-" * 80)
        print(f"  {'Total':50s} {total_ms:8.2f}ms (100.0%)")
        print("=" * 80 + "\n")
