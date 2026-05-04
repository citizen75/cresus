"""API server entry point."""

import sys
import os
from pathlib import Path

# Set up project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
os.environ.setdefault("CRESUS_PROJECT_ROOT", str(project_root))
os.chdir(project_root)

import uvicorn
from loguru import logger
from utils.env import get_api_host, get_api_port


def main():
	"""Start API server."""
	host = get_api_host()
	port = get_api_port()

	logger.info(f"Starting Cresus API on {host}:{port}")

	uvicorn.run(
		"api.app:create_app",
		factory=True,
		host=host,
		port=port,
		reload=False,
		log_level="info",
	)


if __name__ == "__main__":
	main()
