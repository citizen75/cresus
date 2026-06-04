#!/usr/bin/env python3
"""Test MCP tools are working correctly."""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cresus_mcp.server import CresusMCPServer


async def test_mcp_tools():
    """Test all MCP tools."""
    server = CresusMCPServer()

    print("=" * 60)
    print("Testing Cresus MCP Server")
    print("=" * 60)

    # Register domains
    await server._register_domains()
    print(f"\n✓ Registered {len(server.domains)} domain(s)")

    # Test list_tools
    print("\nAvailable Tools:")
    all_tools = []
    for domain_name, domain in server.domains.items():
        tools = await domain.get_tools()
        all_tools.extend(tools)
        print(f"  Domain '{domain_name}': {len(tools)} tools")
        for tool in tools:
            print(f"    - {tool.name}")

    print(f"\nTotal tools: {len(all_tools)}")

    # Test get_portfolio_positions (should exist)
    print("\n" + "=" * 60)
    print("Testing MCP Tool: get_portfolio_positions")
    print("=" * 60)

    try:
        for domain in server.domains.values():
            result = await domain.call_tool(
                "get_portfolio_positions",
                {"portfolio_name": "PEA"}
            )
            print(f"\n✓ Tool executed successfully")
            print(f"Result preview (first 200 chars):")
            result_str = json.dumps(result, indent=2)[:200]
            print(result_str)

            if "error" in result:
                print(f"\n⚠ Tool returned error: {result.get('error')}")
            else:
                print(f"\n✓ Successfully retrieved portfolio data for PEA")
                if isinstance(result, dict) and 'positions' in result:
                    print(f"  Positions found: {len(result.get('positions', []))}")
            break
    except Exception as e:
        print(f"\n✗ Error calling tool: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("MCP Server Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
