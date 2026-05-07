"""Environment configuration loader."""

import os
from pathlib import Path
from typing import Optional


def get_env_file() -> Path:
	"""Get .env file path.

	Uses CRESUS_ENV_FILE env var if set, otherwise defaults to ~/.cresus/.env.
	Does NOT create the file automatically.

	Returns:
		Path to .env file
	"""
	env_file = os.environ.get("CRESUS_ENV_FILE")
	if env_file:
		return Path(env_file)
	return Path.home() / ".cresus" / ".env"


def get_db_root() -> Path:
	"""Get database root directory path.

	Uses CRESUS_DB_ROOT env var if set, otherwise defaults to ~/.cresus/db.
	Creates directory if it doesn't exist.

	Returns:
		Path to database root directory
	"""
	db_root = os.environ.get("CRESUS_DB_ROOT")
	if db_root:
		path = Path(db_root)
	else:
		path = Path.home() / ".cresus" / "db"

	path.mkdir(parents=True, exist_ok=True)
	return path


def get_config_root() -> Path:
	"""Get configuration root directory path.

	Uses CRESUS_CONFIG_ROOT env var if set, otherwise defaults to ~/.cresus/config.
	Creates directory if it doesn't exist.

	Returns:
		Path to configuration root directory
	"""
	config_root = os.environ.get("CRESUS_CONFIG_ROOT")
	if config_root:
		path = Path(config_root)
	else:
		path = Path.home() / ".cresus" / "config"

	path.mkdir(parents=True, exist_ok=True)
	return path


class EnvConfig:
	"""Load and manage environment configuration from .env file."""

	# Singleton instance
	_instance: Optional["EnvConfig"] = None

	def __new__(cls):
		"""Ensure singleton pattern."""
		if cls._instance is None:
			cls._instance = super().__new__(cls)
			cls._instance._initialized = False
		return cls._instance

	def __init__(self):
		"""Initialize env config (only once)."""
		if self._initialized:
			return

		self._initialized = True
		self._load_env()

	def _load_env(self) -> None:
		"""Load .env file from ~/.cresus/.env."""
		env_file = get_env_file()

		if env_file.exists():
			try:
				with open(env_file) as f:
					for line in f:
						line = line.strip()
						# Skip empty lines and comments
						if not line or line.startswith("#"):
							continue

						# Parse key=value
						if "=" in line:
							key, value = line.split("=", 1)
							key = key.strip()
							value = value.strip()

							# Only set if not already in environment
							if key not in os.environ:
								os.environ[key] = value
			except Exception as e:
				print(f"Warning: Failed to load .env file: {e}")

	def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
		"""Get environment variable.

		Args:
			key: Environment variable name
			default: Default value if not found

		Returns:
			Environment variable value or default
		"""
		return os.environ.get(key, default)

	def get_int(self, key: str, default: int = 0) -> int:
		"""Get environment variable as integer.

		Args:
			key: Environment variable name
			default: Default value if not found

		Returns:
			Environment variable value as integer or default
		"""
		value = os.environ.get(key)
		if value is None:
			return default
		try:
			return int(value)
		except ValueError:
			return default

	def get_bool(self, key: str, default: bool = False) -> bool:
		"""Get environment variable as boolean.

		Args:
			key: Environment variable name
			default: Default value if not found

		Returns:
			Environment variable value as boolean or default
		"""
		value = os.environ.get(key, "").lower()
		if value in ("true", "1", "yes", "on"):
			return True
		elif value in ("false", "0", "no", "off"):
			return False
		return default


# Create singleton instance
env = EnvConfig()


# Server configuration shortcuts
def get_api_host() -> str:
	"""Get API server host."""
	return env.get("API_HOST", "0.0.0.0")


def get_api_port() -> int:
	"""Get API server port."""
	return env.get_int("API_PORT", 8000)


def get_mcp_host() -> str:
	"""Get MCP server host."""
	return env.get("MCP_HOST", "localhost")


def get_mcp_port() -> int:
	"""Get MCP server port."""
	return env.get_int("MCP_PORT", 3000)


def get_front_host() -> str:
	"""Get frontend server host."""
	return env.get("FRONT_HOST", "localhost")


def get_front_port() -> int:
	"""Get frontend server port."""
	return env.get_int("FRONT_PORT", 5173)


def get_gateway_cron_enabled() -> bool:
	"""Check if gateway cron scheduler is enabled."""
	return env.get_bool("GATEWAY_CRON_ENABLED", False)


def get_gateway_mcp_enabled() -> bool:
	"""Check if gateway MCP server is enabled."""
	return env.get_bool("GATEWAY_MCP_ENABLED", True)


def get_gateway_cron_config() -> str:
	"""Get gateway cron config path."""
	cron_config = env.get("GATEWAY_CRON_CONFIG")
	if cron_config:
		return cron_config
	return str(get_config_root() / "cron.yml")


