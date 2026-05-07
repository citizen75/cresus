"""Heartbeat flow for monitoring gateway health.

Simple flow that logs a heartbeat message to verify the gateway
cron scheduler is running.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from loguru import logger


class HeartbeatFlow(Flow):
	"""Simple heartbeat flow for gateway health monitoring."""

	def __init__(self, context: Optional[Any] = None):
		"""Initialize heartbeat flow.

		Args:
			context: Optional AgentContext for shared state
		"""
		super().__init__("HeartbeatFlow", context=context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Log a heartbeat message.

		Args:
			input_data: Optional input data (unused)

		Returns:
			Heartbeat result
		"""
		timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		logger.info(f"Gateway heartbeat [{timestamp}] - Cron scheduler is running")

		return {
			"status": "success",
			"message": f"Heartbeat logged at {timestamp}",
			"timestamp": timestamp,
		}
