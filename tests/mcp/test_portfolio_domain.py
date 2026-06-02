"""Tests for Portfolio domain."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from mcp.types import Tool, Resource


@pytest.mark.asyncio
class TestPortfolioDomainResources:
    """Test Portfolio domain resources."""

    async def test_get_resources(self, portfolio_domain):
        """Test getting resources."""
        resources = await portfolio_domain.get_resources()

        assert len(resources) == 1
        assert str(resources[0].uri) == "portfolio://docs"
        assert "Portfolio" in resources[0].name
        assert resources[0].mimeType == "application/json"

    async def test_resource_content(self, portfolio_domain):
        """Test resource content structure."""
        resources = await portfolio_domain.get_resources()
        resource = resources[0]

        assert resource.contents is not None
        assert len(resource.contents) > 0
        content = resource.contents[0].text
        assert "Portfolio Management" in content
        assert "endpoints" in content


@pytest.mark.asyncio
class TestPortfolioDomainTools:
    """Test Portfolio domain tools."""

    async def test_get_tools(self, portfolio_domain):
        """Test getting tools list."""
        tools = await portfolio_domain.get_tools()

        assert len(tools) == 16
        tool_names = [t.name for t in tools]

        # Check critical tools exist
        assert "list_portfolios" in tool_names
        assert "create_portfolio" in tool_names
        assert "get_portfolio" in tool_names
        assert "get_portfolio_metrics" in tool_names
        assert "get_portfolio_positions" in tool_names

    async def test_tool_has_schema(self, portfolio_domain):
        """Test that tools have proper input schemas."""
        tools = await portfolio_domain.get_tools()

        for tool in tools:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert tool.inputSchema is not None
            assert "type" in tool.inputSchema
            assert "properties" in tool.inputSchema

    async def test_create_portfolio_schema(self, portfolio_domain):
        """Test create_portfolio tool schema."""
        tools = await portfolio_domain.get_tools()
        create_tool = next(t for t in tools if t.name == "create_portfolio")

        schema = create_tool.inputSchema
        assert schema["properties"]["name"]["type"] == "string"
        assert "name" in schema["required"]
        assert "portfolio_type" in schema["properties"]
        assert schema["properties"]["portfolio_type"]["enum"] == ["paper", "live"]

    async def test_get_portfolio_metrics_schema(self, portfolio_domain):
        """Test get_portfolio_metrics tool schema."""
        tools = await portfolio_domain.get_tools()
        metrics_tool = next(t for t in tools if t.name == "get_portfolio_metrics")

        schema = metrics_tool.inputSchema
        assert "portfolio_name" in schema["required"]
        assert schema["properties"]["portfolio_name"]["type"] == "string"


@pytest.mark.asyncio
class TestPortfolioDomainCallTool:
    """Test Portfolio domain tool execution."""

    async def test_list_portfolios(self, portfolio_domain, mock_client, sample_portfolio):
        """Test listing portfolios."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=[sample_portfolio])
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool("list_portfolios", {})

        mock_client.get.assert_called_once_with("/portfolios")
        assert isinstance(result, list)

    async def test_get_portfolio(
        self, portfolio_domain, mock_client, sample_portfolio
    ):
        """Test getting portfolio details."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=sample_portfolio)
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool("get_portfolio", {"name": "Main"})

        mock_client.get.assert_called_once_with("/portfolios/Main")
        assert result["portfolio"]["name"] == "Main"

    async def test_create_portfolio(self, portfolio_domain, mock_client):
        """Test creating portfolio."""
        response = {"status": "success", "portfolio": {"name": "New"}}
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=response)
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool(
            "create_portfolio",
            {
                "name": "New",
                "initial_capital": 50000,
                "currency": "EUR",
            },
        )

        mock_client.post.assert_called_once()
        assert result["portfolio"]["name"] == "New"

    async def test_get_portfolio_positions(
        self, portfolio_domain, mock_client, sample_positions
    ):
        """Test getting portfolio positions."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=sample_positions)
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool(
            "get_portfolio_positions",
            {"portfolio_name": "Main", "limit": 100},
        )

        mock_client.get.assert_called_once()
        assert len(result["positions"]) == 2
        assert result["positions"][0]["ticker"] == "AAPL"

    async def test_get_portfolio_metrics(
        self, portfolio_domain, mock_client, sample_metrics
    ):
        """Test getting portfolio metrics."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=sample_metrics)
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool(
            "get_portfolio_metrics", {"portfolio_name": "Main"}
        )

        mock_client.get.assert_called_once_with("/portfolios/Main/metrics")
        assert result["metrics"]["sharpe_ratio"] == 1.45
        assert result["metrics"]["volatility"] == 0.18

    async def test_get_portfolio_transactions(
        self, portfolio_domain, mock_client, sample_transactions
    ):
        """Test getting portfolio transactions."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=sample_transactions)
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool(
            "get_portfolio_transactions",
            {"portfolio_name": "Main", "limit": 50, "offset": 0},
        )

        mock_client.get.assert_called_once()
        assert len(result["transactions"]) == 2
        assert result["transactions"][0]["type"] == "BUY"

    async def test_update_portfolio(self, portfolio_domain, mock_client):
        """Test updating portfolio."""
        response = {"status": "success"}
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=response)
        mock_client.put = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool(
            "update_portfolio",
            {
                "name": "Main",
                "description": "Updated",
                "currency": "USD",
            },
        )

        mock_client.put.assert_called_once()
        assert result["status"] == "success"

    async def test_delete_portfolio(self, portfolio_domain, mock_client):
        """Test deleting portfolio."""
        response = {"status": "success"}
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=response)
        mock_client.delete = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool("delete_portfolio", {"name": "Main"})

        mock_client.delete.assert_called_once_with("/portfolios/Main")
        assert result["status"] == "success"

    async def test_compare_portfolios(self, portfolio_domain, mock_client):
        """Test comparing portfolios."""
        response = {
            "status": "success",
            "comparison": {
                "Main": {"sharpe": 1.45, "return": 0.25},
                "Secondary": {"sharpe": 1.2, "return": 0.15},
            },
        }
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=response)
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool(
            "compare_portfolios", {"portfolio_names": ["Main", "Secondary"]}
        )

        mock_client.post.assert_called_once()
        assert "comparison" in result

    async def test_add_position(self, portfolio_domain, mock_client):
        """Test adding position."""
        response = {"status": "success", "position": {"ticker": "MSFT"}}
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=response)
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool(
            "add_position",
            {
                "portfolio_name": "Main",
                "ticker": "MSFT",
                "quantity": 10,
                "entry_price": 350.0,
            },
        )

        mock_client.post.assert_called_once()
        assert result["position"]["ticker"] == "MSFT"

    async def test_close_position(self, portfolio_domain, mock_client):
        """Test closing position."""
        response = {"status": "success"}
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=response)
        mock_client.delete = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool(
            "close_position",
            {
                "portfolio_name": "Main",
                "ticker": "MSFT",
                "exit_price": 360.0,
            },
        )

        mock_client.delete.assert_called_once()
        assert result["status"] == "success"

    async def test_unknown_tool_error(self, portfolio_domain):
        """Test error handling for unknown tool."""
        result = await portfolio_domain.call_tool("unknown_tool", {})

        assert "error" in result
        assert "Unknown tool" in result["error"]

    async def test_api_error_handling(self, portfolio_domain, mock_client):
        """Test error handling when API fails."""
        mock_client.get.side_effect = Exception("Connection failed")

        result = await portfolio_domain.call_tool("list_portfolios", {})

        assert "error" in result
        assert "Connection failed" in result["error"]


@pytest.mark.asyncio
class TestPortfolioDomainValidation:
    """Test Portfolio domain input validation."""

    async def test_missing_required_parameter(self, portfolio_domain):
        """Test error when required parameter is missing."""
        result = await portfolio_domain.call_tool("get_portfolio", {})

        assert "error" in result

    async def test_invalid_parameter_type(self, portfolio_domain, mock_client):
        """Test handling of invalid parameter types."""
        mock_client.get.side_effect = Exception("Invalid parameter")

        result = await portfolio_domain.call_tool(
            "get_portfolio_positions", {"portfolio_name": "Main", "limit": "invalid"}
        )

        assert "error" in result


@pytest.mark.asyncio
class TestPortfolioDomainIntegration:
    """Integration tests for Portfolio domain."""

    async def test_full_workflow(self, portfolio_domain, mock_client):
        """Test complete workflow: create -> get -> close."""
        # Create portfolio
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "status": "success",
            "portfolio": {"name": "Test", "initial_capital": 100000},
        })
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await portfolio_domain.call_tool(
            "create_portfolio", {"name": "Test", "initial_capital": 100000}
        )
        assert result["portfolio"]["name"] == "Test"

        # Get portfolio
        mock_response2 = MagicMock()
        mock_response2.json = MagicMock(return_value={
            "status": "success",
            "portfolio": {"name": "Test"},
        })
        mock_client.get = AsyncMock(return_value=mock_response2)
        result = await portfolio_domain.call_tool("get_portfolio", {"name": "Test"})
        assert result["portfolio"]["name"] == "Test"

        # Delete portfolio
        mock_response3 = MagicMock()
        mock_response3.json = MagicMock(return_value={"status": "success"})
        mock_client.delete = AsyncMock(return_value=mock_response3)
        result = await portfolio_domain.call_tool("delete_portfolio", {"name": "Test"})
        assert result["status"] == "success"

    async def test_metrics_analysis_workflow(self, portfolio_domain, mock_client):
        """Test workflow for analyzing metrics."""
        # Get metrics
        metrics = {
            "metrics": {
                "sharpe_ratio": 1.5,
                "max_drawdown": -0.1,
                "return": 0.25,
            }
        }
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=metrics)
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await portfolio_domain.call_tool(
            "get_portfolio_metrics", {"portfolio_name": "Main"}
        )

        assert result["metrics"]["sharpe_ratio"] == 1.5
        assert result["metrics"]["return"] == 0.25
