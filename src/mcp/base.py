"""Base class for MCP domains."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import httpx
from mcp.types import Tool, Resource, TextContent


class BaseDomain(ABC):
    """Base class for all MCP domains."""

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.name = self.__class__.__name__

    @abstractmethod
    async def get_resources(self) -> List[Resource]:
        """Return list of resources for this domain."""
        pass

    @abstractmethod
    async def get_tools(self) -> List[Tool]:
        """Return list of tools for this domain."""
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict) -> Dict[str, Any]:
        """Execute a tool in this domain."""
        pass
