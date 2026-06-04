"""HTTP/SSE MCP server for Cresus APIs."""

import asyncio
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn
from loguru import logger

from .server import CresusMCPServer as StdioMCPServer
from mcp.server.sse import SseServerTransport


class HTTPMCPServer:
    """HTTP/SSE wrapper for MCP server."""

    def __init__(self, api_base_url: str = None, http_port: int = 6502):
        self.api_base_url = api_base_url or os.getenv(
            "CRESUS_API_URL", "http://localhost:8000/api/v1"
        )
        self.http_port = http_port

        # Create base MCP server (we'll use its handlers)
        self.mcp_server = StdioMCPServer(api_base_url=self.api_base_url)

        # Create FastAPI app
        self.app = FastAPI(title="Cresus MCP Server", version="1.0.0")
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "ok",
                "service": "cresus-mcp",
                "api_url": self.api_base_url,
                "tools": 16,
            }

        @self.app.post("/mcp")
        @self.app.get("/mcp")
        async def mcp_endpoint(request: Request):
            """MCP Server over SSE/HTTP."""
            # Get the raw ASGI scope, receive, send
            scope = request.scope

            # Check if this is SSE request
            accept = request.headers.get("accept", "")
            if "text/event-stream" not in accept:
                # First request to establish connection
                return {
                    "status": "ok",
                    "message": "MCP server ready for SSE connection",
                    "tools": 16,
                }

            # Create SSE transport
            async def sse_handler(receive, send):
                """Handle SSE connection."""
                transport = SseServerTransport(
                    endpoint="http://localhost:6502/mcp"
                )

                logger.info("MCP SSE client connected")
                try:
                    await self.mcp_server.server.run(
                        transport.read_stream,
                        transport.write_stream,
                        self.mcp_server.server.create_initialization_options(),
                        raise_exceptions=True,
                    )
                    logger.info("MCP SSE session closed normally")
                except Exception as e:
                    logger.error(f"MCP SSE error: {e}", exc_info=True)
                    raise

            # Return SSE stream
            async def event_stream():
                receive = request.receive
                send = request.send
                await sse_handler(receive, send)

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

    async def run_async(self):
        """Run HTTP server."""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.http_port,
            log_level="info",
            access_log=True,
        )
        server = uvicorn.Server(config)
        logger.info(f"Starting Cresus MCP HTTP Server on 0.0.0.0:{self.http_port}")
        logger.info(f"API: {self.api_base_url}")
        logger.info(f"MCP Endpoint: http://localhost:{self.http_port}/mcp")
        await server.serve()

    def run(self):
        """Run server (blocking)."""
        try:
            logger.info("Starting Cresus MCP HTTP Server")
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("MCP server interrupted")
        except Exception as e:
            logger.error(f"MCP server error: {e}", exc_info=True)
            raise
