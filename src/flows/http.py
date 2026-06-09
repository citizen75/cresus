"""HTTP request flow for calling API endpoints via cron."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional
import requests

# Ensure src is in path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from core.flow import Flow
from loguru import logger


class HttpFlow(Flow):
    """Flow for making HTTP requests."""

    def __init__(self, context: Optional[Any] = None):
        """Initialize HTTP flow.

        Args:
            context: Optional AgentContext for shared state
        """
        super().__init__("HttpFlow", context=context)

    def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an HTTP request.

        Args:
            input_data: Dict with:
                - method: HTTP method (GET, POST, PUT, DELETE) - default: GET
                - url: Target URL (required)
                - headers: Optional dict of headers
                - json: Optional JSON body
                - timeout: Request timeout in seconds (default: 30)

        Returns:
            Response with status, status_code, and response data
        """
        if not input_data or "url" not in input_data:
            return {
                "status": "error",
                "error": "url parameter is required in input_data"
            }

        method = input_data.get("method", "GET").upper()
        url = input_data.get("url")
        headers = input_data.get("headers", {})
        json_body = input_data.get("json")
        timeout = input_data.get("timeout", 30)

        # Validate method
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        if method not in valid_methods:
            return {
                "status": "error",
                "error": f"Invalid HTTP method: {method}"
            }

        logger.info(f"Making HTTP {method} request to: {url}")

        try:
            kwargs = {
                "timeout": timeout,
                "headers": headers,
            }

            if json_body:
                kwargs["json"] = json_body

            if method == "GET":
                response = requests.get(url, **kwargs)
            elif method == "POST":
                response = requests.post(url, **kwargs)
            elif method == "PUT":
                response = requests.put(url, **kwargs)
            elif method == "DELETE":
                response = requests.delete(url, **kwargs)
            elif method == "PATCH":
                response = requests.patch(url, **kwargs)

            status = "success" if response.status_code < 400 else "failed"

            log_msg = f"HTTP {method} {url} completed with status: {response.status_code}"
            if response.status_code < 400:
                logger.info(log_msg)
            else:
                logger.error(log_msg)

            try:
                response_data = response.json()
            except:
                response_data = response.text[:500]

            return {
                "status": status,
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "response": response_data,
            }

        except requests.Timeout:
            logger.error(f"HTTP request timed out: {method} {url}")
            return {
                "status": "timeout",
                "method": method,
                "url": url,
                "error": f"Request timed out after {timeout} seconds"
            }

        except Exception as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            return {
                "status": "error",
                "method": method,
                "url": url,
                "error": str(e)
            }
