#!/usr/bin/env python3
"""Quick test to verify conversation API endpoints work."""

import requests
import json
from pathlib import Path
import shutil

BASE_URL = "http://localhost:8000"
TEST_PORTFOLIO = "test_portfolio_api"

def cleanup():
    """Clean up test data."""
    test_dir = Path.home() / ".cresus" / "db" / "portfolios" / TEST_PORTFOLIO
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"✓ Cleaned up {test_dir}")

def test_add_message():
    """Test adding a single message."""
    print("\n[TEST] Adding single message...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{TEST_PORTFOLIO}/message",
        json={"source": "user", "content": "Test message 1"},
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Message added. Count: {data['count']}")
        return True
    else:
        print(f"✗ Failed: {response.text}")
        return False

def test_get_history():
    """Test getting history."""
    print("\n[TEST] Getting conversation history...")
    response = requests.get(f"{BASE_URL}/api/v1/conversations/{TEST_PORTFOLIO}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ History retrieved. Messages: {data['count']}")
        for msg in data['history']:
            print(f"  - [{msg['source']}] {msg['content'][:50]}")
        return True
    else:
        print(f"✗ Failed: {response.text}")
        return False

def test_bulk_add():
    """Test bulk message add."""
    print("\n[TEST] Adding bulk messages...")
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{TEST_PORTFOLIO}/messages/bulk",
        json={
            "messages": [
                {"source": "user", "content": "Message 2"},
                {"source": "alert", "content": "Alert message"},
                {"source": "chatbot", "content": "Chatbot response"},
            ]
        },
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Bulk messages added. Total: {data['count']}")
        return True
    else:
        print(f"✗ Failed: {response.text}")
        return False

def test_search():
    """Test searching messages."""
    print("\n[TEST] Searching messages...")
    response = requests.get(
        f"{BASE_URL}/api/v1/conversations/{TEST_PORTFOLIO}/search?q=alert"
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Search found {data['count']} messages")
        return True
    else:
        print(f"✗ Failed: {response.text}")
        return False

def test_stats():
    """Test getting stats."""
    print("\n[TEST] Getting conversation stats...")
    response = requests.get(f"{BASE_URL}/api/v1/conversations/{TEST_PORTFOLIO}/stats")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Stats retrieved:")
        print(f"  Total messages: {data['total_messages']}")
        print(f"  By source: {data['messages_by_source']}")
        return True
    else:
        print(f"✗ Failed: {response.text}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("CONVERSATION API TEST")
    print("=" * 60)

    cleanup()

    tests = [
        test_add_message,
        test_get_history,
        test_bulk_add,
        test_search,
        test_stats,
    ]

    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Exception: {e}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)

    cleanup()
