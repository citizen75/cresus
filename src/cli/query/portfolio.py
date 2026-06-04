"""Portfolio query operations - API/MCP layer."""

import json
import os
import httpx
from typing import Optional, Dict, Any, List


class PortfolioQuery:
	"""Reusable query layer for portfolio operations."""

	def __init__(self, api_url: Optional[str] = None):
		"""Initialize with API URL from environment or parameter."""
		self.api_url = api_url or os.getenv(
			"CRESUS_API_URL",
			"http://192.168.0.130:6501/api/v1"
		)

	def list_portfolios(self) -> Dict[str, Any]:
		"""List all portfolios."""
		try:
			client = httpx.Client(timeout=30.0)
			response = client.get(f"{self.api_url}/portfolios")
			client.close()

			if response.status_code != 200:
				raise Exception(f"API error {response.status_code}: {response.text}")

			data = response.json()
			portfolios = data.get("portfolios", [])

			return {
				"status": "success",
				"count": len(portfolios),
				"portfolios": [
					{
						"name": p.get("name"),
						"type": p.get("type"),
						"currency": p.get("currency"),
						"value": p.get("total_portfolio_value"),
						"positions": p.get("num_positions"),
					}
					for p in portfolios
				]
			}
		except Exception as e:
			return {
				"status": "error",
				"message": str(e),
				"count": 0,
				"portfolios": []
			}

	def get_positions(self, portfolio_name: str) -> Dict[str, Any]:
		"""Get positions for a portfolio."""
		try:
			client = httpx.Client(timeout=30.0)
			response = client.get(f"{self.api_url}/portfolios/{portfolio_name}")
			client.close()

			if response.status_code != 200:
				raise Exception(f"API error {response.status_code}: {response.text}")

			data = response.json()
			positions = data.get("positions", [])

			return {
				"status": "success",
				"portfolio": portfolio_name,
				"count": len(positions),
				"positions": positions
			}
		except Exception as e:
			return {
				"status": "error",
				"message": str(e),
				"portfolio": portfolio_name,
				"count": 0,
				"positions": []
			}

	def get_metrics(self, portfolio_name: str) -> Dict[str, Any]:
		"""Get metrics for a portfolio."""
		try:
			client = httpx.Client(timeout=30.0)
			response = client.get(f"{self.api_url}/portfolios/{portfolio_name}/metrics")
			client.close()

			if response.status_code != 200:
				raise Exception(f"API error {response.status_code}: {response.text}")

			data = response.json()

			return {
				"status": "success",
				"portfolio": portfolio_name,
				"metrics": data
			}
		except Exception as e:
			return {
				"status": "error",
				"message": str(e),
				"portfolio": portfolio_name,
				"metrics": {}
			}

	def get_performance(self, portfolio_name: str) -> Dict[str, Any]:
		"""Get performance data for a portfolio."""
		try:
			client = httpx.Client(timeout=30.0)
			response = client.get(f"{self.api_url}/portfolios/{portfolio_name}/performance")
			client.close()

			if response.status_code != 200:
				raise Exception(f"API error {response.status_code}: {response.text}")

			data = response.json()

			return {
				"status": "success",
				"portfolio": portfolio_name,
				"data": data
			}
		except Exception as e:
			return {
				"status": "error",
				"message": str(e),
				"portfolio": portfolio_name,
				"data": {}
			}

	def get_allocation(self, portfolio_name: str) -> Dict[str, Any]:
		"""Get asset allocation for a portfolio."""
		try:
			client = httpx.Client(timeout=30.0)
			response = client.get(f"{self.api_url}/portfolios/{portfolio_name}/allocation")
			client.close()

			if response.status_code != 200:
				raise Exception(f"API error {response.status_code}: {response.text}")

			data = response.json()

			return {
				"status": "success",
				"portfolio": portfolio_name,
				"allocation": data.get("by_ticker", [])
			}
		except Exception as e:
			return {
				"status": "error",
				"message": str(e),
				"portfolio": portfolio_name,
				"allocation": []
			}

	def get_value(self, portfolio_name: str) -> Dict[str, Any]:
		"""Get portfolio value and cash balance."""
		try:
			client = httpx.Client(timeout=30.0)
			response = client.get(f"{self.api_url}/portfolios/{portfolio_name}/value")
			client.close()

			if response.status_code != 200:
				raise Exception(f"API error {response.status_code}: {response.text}")

			data = response.json()

			return {
				"status": "success",
				"portfolio": portfolio_name,
				"total_value": data.get("total_value", 0),
				"invested": data.get("invested", 0),
				"cash": data.get("cash", 0),
			}
		except Exception as e:
			return {
				"status": "error",
				"message": str(e),
				"portfolio": portfolio_name,
				"total_value": 0,
				"invested": 0,
				"cash": 0,
			}
