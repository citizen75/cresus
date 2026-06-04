"""MCP (Model Context Protocol) command for exposing portfolio tools."""

import json
import os
import httpx
from rich.console import Console

console = Console()


class MCPCommands:
	"""MCP command handlers for portfolio tools."""

	def handle(self, args: str):
		"""Handle MCP commands."""
		args_str = str(args).strip() if args else ""

		if not args_str:
			self._show_help()
			return

		parts = args_str.split()
		cmd = parts[0] if parts else None

		if cmd == "server":
			self._run_mcp_server()
		elif cmd == "tools":
			self._list_mcp_tools()
		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			self._show_help()

	def _show_help(self):
		"""Show help for MCP commands."""
		console.print("\n[cyan bold]MCP Commands[/cyan bold]")
		console.print("  mcp server   - Run MCP server for AI agent integration")
		console.print("  mcp tools    - List available MCP tools")
		console.print()

	def _list_mcp_tools(self):
		"""List available MCP tools."""
		tools = [
			{
				"name": "list_portfolios",
				"description": "List all available portfolios with summary information",
				"params": [],
			},
			{
				"name": "get_portfolio_positions",
				"description": "Get current positions in a portfolio",
				"params": [{"name": "portfolio_name", "type": "string", "required": True}],
			},
			{
				"name": "get_portfolio_metrics",
				"description": "Get portfolio performance metrics (Sharpe ratio, max drawdown, win rate, etc)",
				"params": [{"name": "portfolio_name", "type": "string", "required": True}],
			},
			{
				"name": "get_portfolio_performance",
				"description": "Get portfolio performance data (returns, drawdown, etc over time)",
				"params": [{"name": "portfolio_name", "type": "string", "required": True}],
			},
			{
				"name": "get_portfolio_allocation",
				"description": "Get portfolio asset allocation by ticker and sector",
				"params": [{"name": "portfolio_name", "type": "string", "required": True}],
			},
			{
				"name": "get_portfolio_value",
				"description": "Get current portfolio total value and cash balance",
				"params": [{"name": "portfolio_name", "type": "string", "required": True}],
			},
		]

		console.print("\n[bold cyan]Available MCP Tools[/bold cyan]\n")
		for i, tool in enumerate(tools, 1):
			console.print(f"{i}. [cyan]{tool['name']}[/cyan]")
			console.print(f"   {tool['description']}")
			if tool["params"]:
				console.print("   Parameters:")
				for param in tool["params"]:
					req = " (required)" if param.get("required") else ""
					console.print(f"     - {param['name']}: {param['type']}{req}")
			console.print()

	def _run_mcp_server(self):
		"""Run MCP server for AI agent integration."""
		try:
			console.print("[cyan]Starting MCP server...[/cyan]")
			console.print("[yellow]⚠[/yellow] MCP server support requires FastMCP integration")
			console.print("[dim]Use: cresus-mcp-server (separate entry point)[/dim]")
		except Exception as e:
			console.print(f"[red]✗[/red] Error: {str(e)}")
