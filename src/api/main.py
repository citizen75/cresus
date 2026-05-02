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
import yaml
from loguru import logger


def main():
    """Start API server."""
    config_path = Path("config/cresus.yml")
    config = {}
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}

    api_cfg = config.get("servers", {}).get("api", {})
    host = api_cfg.get("host", "0.0.0.0")
    port = api_cfg.get("port", 8000)

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
