"""Tests for HTTP flow."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from flows.http import HttpFlow


class TestHttpFlowInitialization:
	"""Test cases for HttpFlow initialization."""

	def test_http_flow_initialization(self):
		"""Test that HttpFlow can be initialized."""
		flow = HttpFlow()
		assert flow.name == "HttpFlow"
		assert flow.context is not None

	def test_http_flow_has_logger(self):
		"""Test that HttpFlow has a logger instance."""
		flow = HttpFlow()
		assert flow.logger is not None


class TestHttpFlowGet:
	"""Test cases for GET requests."""

	@patch("flows.http.requests.get")
	def test_get_request_success(self, mock_get):
		"""Test successful GET request."""
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"status": "ok", "data": "test"}
		mock_get.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "GET",
			"url": "http://api.example.com/test"
		})

		assert result["status"] == "success"
		assert result["status_code"] == 200
		assert result["response"]["status"] == "ok"
		mock_get.assert_called_once()

	@patch("flows.http.requests.get")
	def test_get_request_defaults_to_get(self, mock_get):
		"""Test that GET is the default method."""
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {}
		mock_get.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"url": "http://api.example.com/test"
		})

		assert result["method"] == "GET"
		mock_get.assert_called_once()

	@patch("flows.http.requests.get")
	def test_get_request_with_headers(self, mock_get):
		"""Test GET request with custom headers."""
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {}
		mock_get.return_value = mock_response

		flow = HttpFlow()
		headers = {"Authorization": "Bearer token123"}
		result = flow.process({
			"method": "GET",
			"url": "http://api.example.com/test",
			"headers": headers
		})

		assert result["status"] == "success"
		call_kwargs = mock_get.call_args[1]
		assert call_kwargs["headers"] == headers


class TestHttpFlowPost:
	"""Test cases for POST requests."""

	@patch("flows.http.requests.post")
	def test_post_request_success(self, mock_post):
		"""Test successful POST request."""
		mock_response = Mock()
		mock_response.status_code = 201
		mock_response.json.return_value = {"id": 123, "created": True}
		mock_post.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "POST",
			"url": "http://api.example.com/create",
			"json": {"name": "test"}
		})

		assert result["status"] == "success"
		assert result["status_code"] == 201
		assert result["response"]["id"] == 123

	@patch("flows.http.requests.post")
	def test_post_request_with_json_body(self, mock_post):
		"""Test POST request with JSON body."""
		mock_response = Mock()
		mock_response.status_code = 201
		mock_response.json.return_value = {}
		mock_post.return_value = mock_response

		flow = HttpFlow()
		json_body = {"name": "test", "value": 42}
		result = flow.process({
			"method": "POST",
			"url": "http://api.example.com/create",
			"json": json_body
		})

		assert result["status"] == "success"
		call_kwargs = mock_post.call_args[1]
		assert call_kwargs["json"] == json_body


class TestHttpFlowPut:
	"""Test cases for PUT requests."""

	@patch("flows.http.requests.put")
	def test_put_request_success(self, mock_put):
		"""Test successful PUT request."""
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"id": 123, "updated": True}
		mock_put.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "PUT",
			"url": "http://api.example.com/update/123",
			"json": {"name": "updated"}
		})

		assert result["status"] == "success"
		assert result["status_code"] == 200


class TestHttpFlowDelete:
	"""Test cases for DELETE requests."""

	@patch("flows.http.requests.delete")
	def test_delete_request_success(self, mock_delete):
		"""Test successful DELETE request."""
		mock_response = Mock()
		mock_response.status_code = 204
		mock_response.json.side_effect = ValueError("No JSON")
		mock_response.text = ""
		mock_delete.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "DELETE",
			"url": "http://api.example.com/delete/123"
		})

		assert result["status"] == "success"
		assert result["status_code"] == 204


class TestHttpFlowPatch:
	"""Test cases for PATCH requests."""

	@patch("flows.http.requests.patch")
	def test_patch_request_success(self, mock_patch):
		"""Test successful PATCH request."""
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"id": 123, "patched": True}
		mock_patch.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "PATCH",
			"url": "http://api.example.com/patch/123",
			"json": {"status": "active"}
		})

		assert result["status"] == "success"
		assert result["status_code"] == 200


class TestHttpFlowErrorHandling:
	"""Test cases for error handling."""

	@patch("flows.http.requests.get")
	def test_http_error_response(self, mock_get):
		"""Test handling of HTTP error responses (4xx, 5xx)."""
		mock_response = Mock()
		mock_response.status_code = 404
		mock_response.json.return_value = {"error": "Not found"}
		mock_get.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "GET",
			"url": "http://api.example.com/notfound"
		})

		assert result["status"] == "failed"
		assert result["status_code"] == 404

	@patch("flows.http.requests.get")
	def test_timeout_error(self, mock_get):
		"""Test handling of timeout errors."""
		mock_get.side_effect = requests.Timeout("Connection timed out")

		flow = HttpFlow()
		result = flow.process({
			"method": "GET",
			"url": "http://api.example.com/slow",
			"timeout": 5
		})

		assert result["status"] == "timeout"
		assert "timed out" in result["error"].lower()

	@patch("flows.http.requests.get")
	def test_connection_error(self, mock_get):
		"""Test handling of connection errors."""
		mock_get.side_effect = requests.ConnectionError("Failed to connect")

		flow = HttpFlow()
		result = flow.process({
			"method": "GET",
			"url": "http://invalid.example.com"
		})

		assert result["status"] == "error"
		assert "Failed to connect" in result["error"]

	def test_missing_url_parameter(self):
		"""Test that missing URL raises error."""
		flow = HttpFlow()
		result = flow.process({
			"method": "GET"
		})

		assert result["status"] == "error"
		assert "url parameter is required" in result["error"]

	def test_empty_input_data(self):
		"""Test that empty input raises error."""
		flow = HttpFlow()
		result = flow.process(None)

		assert result["status"] == "error"
		assert "url parameter is required" in result["error"]

	def test_invalid_http_method(self):
		"""Test that invalid HTTP method raises error."""
		flow = HttpFlow()
		result = flow.process({
			"method": "INVALID",
			"url": "http://api.example.com/test"
		})

		assert result["status"] == "error"
		assert "Invalid HTTP method" in result["error"]


class TestHttpFlowTextResponse:
	"""Test cases for non-JSON responses."""

	@patch("flows.http.requests.get")
	def test_text_response(self, mock_get):
		"""Test handling of text/plain responses."""
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.side_effect = ValueError("Invalid JSON")
		mock_response.text = "Response text content"
		mock_get.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "GET",
			"url": "http://api.example.com/text"
		})

		assert result["status"] == "success"
		assert "Response text" in result["response"]


class TestHttpFlowCronAlert:
	"""Test cases for cron alert use case."""

	@patch("flows.http.requests.post")
	def test_alert_sha_red_endpoint(self, mock_post):
		"""Test calling alert endpoint for sha_red."""
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"status": "success",
			"matches": [
				{"ticker": "AAPL", "value": 0.95},
				{"ticker": "GOOGL", "value": 0.92}
			]
		}
		mock_post.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "POST",
			"url": "http://localhost:8000/api/alerts/sha_red/run"
		})

		assert result["status"] == "success"
		assert result["method"] == "POST"
		assert len(result["response"]["matches"]) == 2

	@patch("flows.http.requests.post")
	def test_alert_with_custom_timeout(self, mock_post):
		"""Test alert endpoint with custom timeout."""
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"status": "success"}
		mock_post.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "POST",
			"url": "http://localhost:8000/api/alerts/sha_red/run",
			"timeout": 60
		})

		assert result["status"] == "success"
		call_kwargs = mock_post.call_args[1]
		assert call_kwargs["timeout"] == 60


class TestHttpFlowReturnValues:
	"""Test cases for return value structure."""

	@patch("flows.http.requests.get")
	def test_success_response_structure(self, mock_get):
		"""Test structure of successful response."""
		mock_response = Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"data": "value"}
		mock_get.return_value = mock_response

		flow = HttpFlow()
		result = flow.process({
			"method": "GET",
			"url": "http://api.example.com/test"
		})

		# Check required fields
		assert "status" in result
		assert "method" in result
		assert "url" in result
		assert "status_code" in result
		assert "response" in result

	def test_error_response_structure(self):
		"""Test structure of error response."""
		flow = HttpFlow()
		result = flow.process({
			"method": "GET"
		})

		# Check error response has required fields
		assert "status" in result
		assert result["status"] == "error"
		assert "error" in result

	@patch("flows.http.requests.get")
	def test_timeout_response_structure(self, mock_get):
		"""Test structure of timeout response."""
		mock_get.side_effect = requests.Timeout()

		flow = HttpFlow()
		result = flow.process({
			"method": "GET",
			"url": "http://api.example.com/test",
			"timeout": 5
		})

		assert result["status"] == "timeout"
		assert "error" in result
		assert "method" in result
		assert "url" in result
