"""MCP (Model Context Protocol) HTTP/SSE endpoint.

Uses the MCP library's built-in HTTP SSE support via FastMCP.
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from loguru import logger
import json
import asyncio
from typing import AsyncGenerator

router = APIRouter(tags=["mcp"])


@router.options("/mcp")
async def mcp_options():
    """Handle CORS preflight."""
    return {}


@router.post("/mcp")
async def mcp_sse_endpoint(request: Request) -> StreamingResponse:
    """MCP SSE endpoint using JSON-RPC protocol.

    Hermes connects here with POST and expects JSON-RPC responses over SSE.
    """

    async def generate():
        """Stream JSON-RPC messages."""
        try:
            # Read the incoming request
            body = await request.body()
            logger.info(f"MCP received request: {len(body)} bytes")

            # Send initialization response
            init_response = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "logging": {},
                        "tools": {},
                    },
                    "serverInfo": {
                        "name": "cresus-portfolio-api",
                        "version": "1.0.0",
                    }
                }
            }
            yield "data: " + json.dumps(init_response) + "\n\n"

            # Send tools list
            tools_response = {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "tools": [
                        {
                            "name": "portfolio_list",
                            "description": "List all portfolios",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "portfolio_type": {
                                        "type": "string",
                                        "enum": ["real", "paper", "all"],
                                    }
                                },
                            }
                        },
                        {
                            "name": "portfolio_holdings",
                            "description": "Get portfolio holdings",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "portfolio_name": {
                                        "type": "string",
                                    }
                                },
                                "required": ["portfolio_name"],
                            }
                        },
                        {
                            "name": "watchlist_rank",
                            "description": "Get watchlist rankings",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "watchlist_name": {
                                        "type": "string",
                                    }
                                },
                                "required": ["watchlist_name"],
                            }
                        },
                        {
                            "name": "screener_run",
                            "description": "Run a screener",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "screener_name": {
                                        "type": "string",
                                    },
                                    "portfolio": {
                                        "type": "string",
                                    }
                                },
                                "required": ["screener_name"],
                            }
                        },
                    ]
                }
            }
            yield "data: " + json.dumps(tools_response) + "\n\n"

            logger.info("MCP SSE stream initialized successfully")

        except Exception as e:
            logger.error(f"Error in MCP SSE endpoint: {e}", exc_info=True)
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": "Internal server error",
                    "data": {"details": str(e)},
                }
            }
            yield "data: " + json.dumps(error_response) + "\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/mcp/health")
async def mcp_health():
    """Health check for MCP endpoint."""
    return {
        "status": "healthy",
        "service": "cresus-mcp",
        "type": "sse",
        "url": "http://192.168.0.130:6501/mcp",
        "tools": [
            "portfolio_list",
            "portfolio_holdings",
            "watchlist_rank",
            "screener_run",
        ],
    }
