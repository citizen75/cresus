#!/usr/bin/env python
"""Test watchlist add endpoint with real HTTP call."""

import requests
import json

BASE_URL = "http://localhost:6501/api/v1"

def test_add_watchlist():
    """Test POST /watchlists/global/add endpoint."""
    print("Testing POST /api/v1/watchlists/global/add")
    print("=" * 60)

    try:
        # Test data
        payload = {
            "ticker": "TEST.PA"
        }

        print(f"\n1. Sending request...")
        print(f"   URL: {BASE_URL}/watchlists/global/add")
        print(f"   Method: POST")
        print(f"   Payload: {json.dumps(payload, indent=2)}")

        # Make request
        response = requests.post(
            f"{BASE_URL}/watchlists/global/add",
            json=payload,
            timeout=10
        )

        print(f"\n2. Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")

        try:
            response_json = response.json()
            print(f"   Body: {json.dumps(response_json, indent=2)}")
        except:
            print(f"   Body: {response.text}")

        if response.status_code == 200:
            print(f"\n✓ SUCCESS: Ticker added to watchlist!")
            return True
        else:
            print(f"\n✗ FAILED: Status code {response.status_code}")
            return False

    except requests.exceptions.ConnectionError as e:
        print(f"\n✗ Connection Error: {e}")
        print(f"   Make sure the server is running on {BASE_URL}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_add_watchlist()
    exit(0 if success else 1)
