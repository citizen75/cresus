"""Shell execution flow for running CLI commands via cron."""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from core.flow import Flow
from loguru import logger


class ShellExecFlow(Flow):
    """Flow for executing shell commands safely."""

    def __init__(self, context: Optional[Any] = None):
        """Initialize shell exec flow.

        Args:
            context: Optional AgentContext for shared state
        """
        super().__init__("ShellExecFlow", context=context)

    def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a shell command.

        Args:
            input_data: Dict with 'command' key containing the shell command to run

        Returns:
            Execution result with status and output
        """
        if not input_data or "command" not in input_data:
            return {
                "status": "error",
                "error": "command parameter is required in input_data"
            }

        command = input_data.get("command")

        # Whitelist of allowed commands for safety
        allowed_prefixes = [
            "cresus ",
            "python ",
            "/usr/bin/env python",
        ]

        if not any(command.strip().startswith(prefix) for prefix in allowed_prefixes):
            logger.error(f"Command not allowed: {command}")
            return {
                "status": "error",
                "error": f"Command not allowed: {command}"
            }

        logger.info(f"Executing: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(Path.home())
            )

            status = "success" if result.returncode == 0 else "failed"

            log_msg = f"Shell command '{command}' completed with status: {status}"
            if result.returncode == 0:
                logger.info(log_msg)
            else:
                logger.error(log_msg)

            return {
                "status": status,
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout[:500] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else "",
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            return {
                "status": "timeout",
                "command": command,
                "error": "Command execution timed out after 300 seconds"
            }

        except Exception as e:
            logger.error(f"Command failed: {command} - {e}")
            return {
                "status": "error",
                "command": command,
                "error": str(e)
            }
