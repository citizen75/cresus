"""MCP server entry point."""

import sys
import os
from pathlib import Path

# Set project root BEFORE ANY OTHER IMPORTS
project_root = Path(__file__).parent.parent.parent
os.environ.setdefault("CRESUS_PROJECT_ROOT", str(project_root))

# CRITICAL: Configure logging to stderr BEFORE any other imports
from loguru import logger

logger.remove()
logger.add(sys.stderr, level=os.environ.get("CRESUS_LOG_LEVEL", "INFO"))
logger.add("logs/mcp.log", rotation="10 MB", retention="7 days", level="DEBUG")

# NOW set up paths and imports
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)


def main():
    """Start MCP server."""
    logger.info("Starting Cresus MCP server")
    from src.mcp.server import CresusMCPServer

    server = CresusMCPServer()
    server.run()


if __name__ == "__main__":
    main()
