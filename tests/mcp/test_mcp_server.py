"""Tests for MCP Server."""

import pytest
from unittest.mock import AsyncMock, patch
import httpx
import os
from src.mcp.server import CresusMCPServer
from mcp.types import Tool


class TestCresusMCPServer:
    """Test CresusMCPServer."""

    def test_server_initialization(self):
        """Test server initialization."""
        server = CresusMCPServer(api_base_url="http://localhost:8000/api/v1")

        assert server.api_base_url == "http://localhost:8000/api/v1"
        assert server.server is not None
        assert server.server.name == "cresus-api"

    def test_server_initialization_with_env_var(self):
        """Test server initialization with environment variable."""
        os.environ["CRESUS_API_URL"] = "http://test:9000/api/v1"
        server = CresusMCPServer()

        assert server.api_base_url == "http://test:9000/api/v1"

    def test_server_initialization_with_api_key(self):
        """Test server initialization with API key."""
        os.environ["CRESUS_API_KEY"] = "test_key"
        server = CresusMCPServer()

        assert server.api_key == "test_key"

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test HTTP client initialization."""
        server = CresusMCPServer()
        await server._init_client()

        assert server.client is not None
        assert isinstance(server.client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_domains_registration(self):
        """Test domain registration."""
        server = CresusMCPServer()
        await server._register_domains()

        assert "portfolio" in server.domains
        assert server.domains["portfolio"] is not None

    @pytest.mark.asyncio
    async def test_list_resources(self):
        """Test listing resources."""
        server = CresusMCPServer()

        # Mock the handler
        resources = []

        async def mock_list_resources():
            await server._register_domains()
            for domain in server.domains.values():
                resources.extend(await domain.get_resources())
            return resources

        result = await mock_list_resources()

        assert len(result) > 0
        assert str(result[0].uri) == "portfolio://docs"

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing tools."""
        server = CresusMCPServer()

        # Mock the handler
        tools = []

        async def mock_list_tools():
            await server._register_domains()
            for domain in server.domains.values():
                tools.extend(await domain.get_tools())
            return tools

        result = await mock_list_tools()

        assert len(result) == 16  # Portfolio domain has 16 tools
        tool_names = [t.name for t in result]
        assert "list_portfolios" in tool_names
        assert "get_portfolio_metrics" in tool_names

    @pytest.mark.asyncio
    async def test_call_tool_portfolio(self):
        """Test calling a portfolio tool."""
        from unittest.mock import MagicMock
        server = CresusMCPServer()

        # Mock the client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={
                "portfolios": [],
                "status": "success",
            })
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            server.client = mock_client
            await server._register_domains()

            result = await server.domains["portfolio"].call_tool(
                "list_portfolios", {}
            )

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """Test calling unknown tool."""
        server = CresusMCPServer()
        await server._register_domains()

        # Try to call a tool that doesn't exist
        # This should return an error from the handler
        result = await server.domains["portfolio"].call_tool("nonexistent_tool", {})

        assert "error" in result


@pytest.mark.asyncio
class TestCresusMCPServerIntegration:
    """Integration tests for MCP Server."""

    async def test_server_workflow(self):
        """Test complete server workflow."""
        from unittest.mock import MagicMock
        server = CresusMCPServer()

        # Initialize client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={
                "status": "success",
                "portfolio": {"name": "Main"},
            })
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            server.client = mock_client

            # Register domains
            await server._register_domains()

            # Get tools
            tools = []
            for domain in server.domains.values():
                tools.extend(await domain.get_tools())

            assert len(tools) > 0

            # Call a tool
            result = await server.domains["portfolio"].call_tool(
                "get_portfolio", {"name": "Main"}
            )

            assert result["portfolio"]["name"] == "Main"

    async def test_multiple_domains_support(self):
        """Test that server can support multiple domains."""
        server = CresusMCPServer()
        await server._register_domains()

        # Currently only portfolio, but structure supports more
        assert len(server.domains) >= 1
        assert "portfolio" in server.domains


@pytest.mark.asyncio
class TestMCPServerErrorHandling:
    """Test error handling in MCP Server."""

    async def test_api_connection_error(self):
        """Test handling of API connection errors."""
        server = CresusMCPServer(api_base_url="http://invalid:9999/api/v1")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client_class.return_value = mock_client

            server.client = mock_client
            await server._register_domains()

            result = await server.domains["portfolio"].call_tool(
                "list_portfolios", {}
            )

            assert "error" in result

    async def test_malformed_response(self):
        """Test handling of malformed API response."""
        from unittest.mock import MagicMock
        server = CresusMCPServer()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json = MagicMock(side_effect=ValueError("Invalid JSON"))
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            server.client = mock_client
            await server._register_domains()

            result = await server.domains["portfolio"].call_tool(
                "list_portfolios", {}
            )

            assert "error" in result
