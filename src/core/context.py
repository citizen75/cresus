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
    
    def get_agent_metrics(self) -> List[Dict[str, Any]]:
        """Get all recorded agent execution metrics.
        
        Returns:
            List of dicts with structure:
            [
                {"name": "AgentName", "duration_ms": 123.45, "ticker_count": 10},
                ...
            ]
        """
        metadata = self.get("metadata") or {}
        return metadata.get("agent_metrics", [])
    
    def print_agent_metrics(self) -> None:
        """Print a formatted summary of agent execution times and ticker counts."""
        metrics = self.get_agent_metrics()
        if not metrics:
            print("No agent metrics recorded")
            return
        
        print("\n" + "=" * 80)
        print("Agent Execution Times (with Ticker Tracking)")
        print("=" * 80)
        
        total_ms = sum(t["duration_ms"] for t in metrics)
        
        # Sort by duration descending
        sorted_metrics = sorted(metrics, key=lambda x: x["duration_ms"], reverse=True)
        
        for metric in sorted_metrics:
            name = metric["name"]
            duration = metric["duration_ms"]
            pct = (duration / total_ms * 100) if total_ms > 0 else 0
            ticker_count = metric.get("ticker_count", "")
            ticker_str = f"  [{ticker_count} tickers]" if ticker_count else ""
            print(f"  {name:50s} {duration:8.2f}ms ({pct:5.1f}%){ticker_str}")
        
        print("-" * 80)
        print(f"  {'Total':50s} {total_ms:8.2f}ms (100.0%)")
        print("=" * 80 + "\n")
