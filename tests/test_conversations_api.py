"""Unit tests for conversation API endpoints."""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import shutil
import json

from api.app import create_app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def cleanup():
    """Clean up test data before and after test."""
    # Clean up BEFORE test (in case of leftover data)
    test_dir = Path.home() / ".cresus" / "db" / "portfolios" / "test_portfolio"
    if test_dir.exists():
        shutil.rmtree(test_dir)

    yield

    # Clean up AFTER test
    if test_dir.exists():
        shutil.rmtree(test_dir)


class TestConversationAPI:
    """Test conversation API endpoints."""

    def test_add_single_message(self, client, cleanup):
        """Test adding a single message."""
        response = client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Test message"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["portfolio_name"] == "test_portfolio"
        assert data["count"] == 1
        assert data["history"][0]["source"] == "user"
        assert data["history"][0]["content"] == "Test message"

    def test_add_multiple_messages(self, client, cleanup):
        """Test adding multiple messages."""
        messages = [
            {"source": "user", "content": "Message 1"},
            {"source": "chatbot", "content": "Message 2"},
            {"source": "alert", "content": "Message 3"},
        ]
        response = client.post(
            "/api/v1/conversations/test_portfolio/messages/bulk",
            json={"messages": messages},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3

    def test_get_conversation_history(self, client, cleanup):
        """Test retrieving conversation history."""
        # Add messages first
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Message 1"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "chatbot", "content": "Message 2"},
        )

        # Get history
        response = client.get("/api/v1/conversations/test_portfolio")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["history"]) == 2

    def test_get_history_with_limit(self, client, cleanup):
        """Test history retrieval with limit."""
        # Add 5 messages
        for i in range(5):
            client.post(
                "/api/v1/conversations/test_portfolio/message",
                json={"source": "user", "content": f"Message {i}"},
            )

        # Get with limit
        response = client.get("/api/v1/conversations/test_portfolio?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert data["total"] == 5

    def test_get_history_with_offset(self, client, cleanup):
        """Test history retrieval with offset."""
        # Add 5 messages
        for i in range(5):
            client.post(
                "/api/v1/conversations/test_portfolio/message",
                json={"source": "user", "content": f"Message {i}"},
            )

        # Get with offset
        response = client.get("/api/v1/conversations/test_portfolio?offset=2")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3  # 5 - 2 = 3

    def test_filter_by_source(self, client, cleanup):
        """Test filtering messages by source."""
        # Add different source messages
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "User message"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "alert", "content": "Alert message"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "alert", "content": "Another alert"},
        )

        # Filter by source
        response = client.get(
            "/api/v1/conversations/test_portfolio?source=alert"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        for msg in data["history"]:
            assert msg["source"] == "alert"

    def test_search_messages(self, client, cleanup):
        """Test searching messages by content."""
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Buy AAPL stock"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Sell GOOGL"},
        )

        response = client.get(
            "/api/v1/conversations/test_portfolio/search?q=AAPL"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert "AAPL" in data["history"][0]["content"]

    def test_get_message_count(self, client, cleanup):
        """Test getting message count."""
        # Add messages
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Message 1"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "alert", "content": "Alert 1"},
        )

        # Get count
        response = client.get("/api/v1/conversations/test_portfolio/count")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["by_source"]["user"] == 1
        assert data["by_source"]["alert"] == 1

    def test_get_count_by_source(self, client, cleanup):
        """Test getting count for specific source."""
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Message 1"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Message 2"},
        )

        response = client.get(
            "/api/v1/conversations/test_portfolio/count?source=user"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_get_stats(self, client, cleanup):
        """Test getting conversation statistics."""
        # Add messages
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Message 1"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "alert", "content": "Alert 1"},
        )

        response = client.get("/api/v1/conversations/test_portfolio/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 2
        assert data["messages_by_source"]["user"] == 1
        assert data["messages_by_source"]["alert"] == 1
        assert data["first_message"] is not None
        assert data["last_message"] is not None

    def test_get_last_message(self, client, cleanup):
        """Test getting the last message."""
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "First"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "alert", "content": "Last"},
        )

        response = client.get("/api/v1/conversations/test_portfolio/last")
        assert response.status_code == 200
        data = response.json()
        assert data["message"]["source"] == "alert"
        assert data["message"]["content"] == "Last"

    def test_get_messages_by_source(self, client, cleanup):
        """Test getting messages by specific source."""
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "User message"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "alert", "content": "Alert 1"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "alert", "content": "Alert 2"},
        )

        response = client.get(
            "/api/v1/conversations/test_portfolio/by-source/alert"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        for msg in data["history"]:
            assert msg["source"] == "alert"

    def test_clear_all_messages(self, client, cleanup):
        """Test clearing all conversation history."""
        # Add messages
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Message 1"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Message 2"},
        )

        # Clear
        response = client.delete("/api/v1/conversations/test_portfolio")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"

        # Verify empty
        response = client.get("/api/v1/conversations/test_portfolio")
        data = response.json()
        assert data["count"] == 0

    def test_clear_by_source(self, client, cleanup):
        """Test clearing messages by source."""
        # Add messages
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "User message"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "alert", "content": "Alert 1"},
        )
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "alert", "content": "Alert 2"},
        )

        # Clear alerts
        response = client.delete(
            "/api/v1/conversations/test_portfolio/by-source/alert"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["details"]["source"] == "alert"
        assert data["details"]["cleared_count"] == 2
        assert data["details"]["remaining_count"] == 1

        # Verify only user message remains
        response = client.get("/api/v1/conversations/test_portfolio")
        data = response.json()
        assert data["count"] == 1
        assert data["history"][0]["source"] == "user"

    def test_export_json(self, client, cleanup):
        """Test exporting conversation as JSON."""
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Test message"},
        )

        response = client.get(
            "/api/v1/conversations/test_portfolio/export?format=json"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "json"
        assert data["count"] == 1
        assert isinstance(data["data"], list)

    def test_export_csv(self, client, cleanup):
        """Test exporting conversation as CSV."""
        client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "user", "content": "Test message"},
        )

        response = client.get(
            "/api/v1/conversations/test_portfolio/export?format=csv"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "csv"
        assert data["count"] == 1
        assert "source,content,datetime" in data["data"]

    def test_invalid_source(self, client):
        """Test that invalid source is rejected."""
        response = client.post(
            "/api/v1/conversations/test_portfolio/message",
            json={"source": "invalid_source", "content": "Test"},
        )
        # Should fail validation
        assert response.status_code != 200
