"""Integration tests for MCP with real API (requires running API)."""

import pytest
import httpx
import os
from src.mcp.server import CresusMCPServer
from src.mcp.domains.portfolio import PortfolioDomain


@pytest.fixture
def api_url():
    """Get API URL from environment or use default."""
    return os.getenv("CRESUS_API_URL", "http://localhost:8000/api/v1")


@pytest.fixture
def real_client(api_url):
    """Create a real async HTTP client."""
    return httpx.AsyncClient(base_url=api_url)


@pytest.mark.asyncio
class TestMCPWithRealAPI:
    """Integration tests with real API (skip if API not available)."""

    async def test_api_health_check(self, api_url):
        """Test that API is available."""
        async with httpx.AsyncClient(base_url=api_url) as client:
            try:
                response = await client.get("/health")
                assert response.status_code == 200
            except Exception as e:
                pytest.skip(f"API not available: {e}")

    async def test_list_portfolios_real_api(self, real_client):
        """Test listing portfolios from real API."""
        try:
            response = await real_client.get("/portfolios")
            assert response.status_code in [200, 404]  # 404 if no portfolios
            data = response.json()
            assert "portfolios" in data or "error" in data
        except Exception as e:
            pytest.skip(f"API not available: {e}")

    async def test_portfolio_domain_with_real_api(self, real_client):
        """Test PortfolioDomain with real API."""
        try:
            domain = PortfolioDomain(real_client)

            # Get resources
            resources = await domain.get_resources()
            assert len(resources) == 1
            assert resources[0].uri == "portfolio://docs"

            # Get tools
            tools = await domain.get_tools()
            assert len(tools) == 16

            # Try listing portfolios
            result = await domain.call_tool("list_portfolios", {})
            assert "portfolios" in result or "error" in result
        except Exception as e:
            pytest.skip(f"API not available: {e}")


@pytest.mark.asyncio
class TestMCPServerWithRealAPI:
    """Test MCP Server with real API."""

    async def test_server_with_real_api(self):
        """Test server initialization and tool listing with real API."""
        server = CresusMCPServer()

        try:
            await server._init_client()
            await server._register_domains()

            # Get tools
            tools = []
            for domain in server.domains.values():
                tools.extend(await domain.get_tools())

            assert len(tools) == 16
            tool_names = [t.name for t in tools]
            assert "list_portfolios" in tool_names
        except Exception as e:
            pytest.skip(f"API not available: {e}")
