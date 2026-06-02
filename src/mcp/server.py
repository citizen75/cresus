"""MCP server for Cresus APIs."""

import asyncio
import json
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx
from loguru import logger

from .domains import PortfolioDomain


class CresusMCPServer:
    """MCP server exposing Cresus APIs."""

    def __init__(self, api_base_url: str = None):
        self.api_base_url = api_base_url or os.getenv(
            "CRESUS_API_URL", "http://localhost:8000/api/v1"
        )
        self.api_key = os.getenv("CRESUS_API_KEY")
        self.server = Server("cresus-api")
        self.client = None
        self.domains = {}
        self._register_handlers()

    async def _init_client(self):
        """Initialize HTTP client."""
        if self.client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self.client = httpx.AsyncClient(
                base_url=self.api_base_url,
                headers=headers,
                timeout=30.0,
            )
            logger.info(f"Connected to Cresus API at {self.api_base_url}")

    async def _register_domains(self):
        """Register all domains."""
        await self._init_client()

        # Register Portfolio domain
        self.domains["portfolio"] = PortfolioDomain(self.client)

        logger.info(f"Registered {len(self.domains)} domain(s)")

    def _register_handlers(self):
        """Register MCP handlers."""

        @self.server.list_resources()
        async def list_resources():
            await self._register_domains()
            resources = []
            for domain in self.domains.values():
                resources.extend(await domain.get_resources())
            return resources

        @self.server.read_resource()
        async def read_resource(uri: str):
            await self._register_domains()
            for domain in self.domains.values():
                resources = await domain.get_resources()
                for resource in resources:
                    if resource.uri == uri:
                        return resource.contents
            return None

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            await self._register_domains()
            tools = []
            for domain in self.domains.values():
                tools.extend(await domain.get_tools())
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            await self._register_domains()

            # Find which domain has this tool
            for domain in self.domains.values():
                domain_tools = await domain.get_tools()
                tool_names = [t.name for t in domain_tools]
                if name in tool_names:
                    result = await domain.call_tool(name, arguments)
                    return [
                        TextContent(type="text", text=json.dumps(result, default=str))
                    ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"}, default=str),
                )
            ]

    async def run_async(self):
        """Run MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)

    def run(self):
        """Run MCP server (blocking)."""
        asyncio.run(self.run_async())
