"""Gateway server entry point."""

import sys
import os
from pathlib import Path

# Set up project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
os.environ.setdefault("CRESUS_PROJECT_ROOT", str(project_root))
os.chdir(project_root)

from loguru import logger
from utils.env import (
	get_api_host,
	get_api_port,
	get_gateway_cron_enabled,
	get_gateway_mcp_enabled,
)
from gateway.server import create_gateway


def main():
	"""Start unified gateway server."""
	# Get configuration from environment
	api_host = get_api_host()
	api_port = get_api_port()
	enable_cron = get_gateway_cron_enabled()
	enable_mcp = get_gateway_mcp_enabled()

	# Create and start gateway
	logger.info("Initializing Cresus Gateway")
	gateway = create_gateway(
		api_host=api_host,
		api_port=api_port,
		enable_cron=enable_cron,
		enable_mcp=enable_mcp,
	)

	logger.info(f"Gateway configuration: API on {api_host}:{api_port}, Cron {'enabled' if enable_cron else 'disabled'}, MCP {'enabled' if enable_mcp else 'disabled'}")

	# Start gateway (blocking call)
	gateway.start()


if __name__ == "__main__":
	main()
