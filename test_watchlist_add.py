#!/usr/bin/env python
"""Test watchlist add endpoint."""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.watchlist import WatchlistManager
import pandas as pd


def test_add_ticker():
    """Test adding a ticker to watchlist."""
    try:
        print("Testing WatchlistManager.add_ticker()...")

        # Test with global watchlist
        watchlist_name = "global"
        ticker = "AF.PA"

        print(f"1. Creating WatchlistManager for '{watchlist_name}'...")
        manager = WatchlistManager(watchlist_name)

        print(f"2. Loading current watchlist...")
        df = manager.load()
        print(f"   Current watchlist: {type(df)}")
        if df is not None:
            print(f"   Shape: {df.shape}")
            print(f"   Columns: {list(df.columns)}")
            print(f"   First few rows:\n{df.head()}")
        else:
            print(f"   Watchlist is None or empty")

        print(f"\n3. Creating new row for ticker '{ticker}'...")
        if df is not None and not df.empty:
            new_row = {col: None for col in df.columns}
        else:
            new_row = {'ticker': None}
        new_row['ticker'] = ticker
        print(f"   New row: {new_row}")

        print(f"\n4. Adding to watchlist...")
        if df is None or df.empty:
            print(f"   Creating new DataFrame...")
            df = pd.DataFrame([new_row])
        else:
            print(f"   Concatenating to existing DataFrame...")
            if ticker not in df['ticker'].values:
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                print(f"   Ticker already exists in watchlist")

        print(f"   New shape: {df.shape}")
        print(f"   Last few rows:\n{df.tail()}")

        print(f"\n5. Saving watchlist...")
        manager.save(df)
        print(f"   Saved successfully!")

        print(f"\n6. Verifying save...")
        df_check = manager.load()
        print(f"   Loaded shape: {df_check.shape}")
        if ticker in df_check['ticker'].values:
            print(f"   ✓ Ticker '{ticker}' found in saved watchlist!")
        else:
            print(f"   ✗ Ticker '{ticker}' NOT found in saved watchlist!")

        return True

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_endpoint():
    """Test the FastAPI endpoint directly."""
    try:
        print("\n" + "="*60)
        print("Testing FastAPI endpoint directly...")
        print("="*60)

        from fastapi.testclient import TestClient
        from src.api.routes.watchlist import router, TickerRequest
        from fastapi import FastAPI

        # Create a test app with just the watchlist router
        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        # Test the add endpoint
        print("\n1. Testing POST /watchlists/global/add...")
        response = client.post(
            "/watchlists/global/add",
            json={"ticker": "TEST.PA"}
        )

        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")

        if response.status_code == 200:
            print(f"   ✓ Success!")
        else:
            print(f"   ✗ Failed!")

        return response.status_code == 200

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Watchlist Add Test Suite")
    print("="*60)

    # Test 1: Direct WatchlistManager
    print("\nTest 1: Direct WatchlistManager")
    print("-"*60)
    success1 = test_add_ticker()

    # Test 2: FastAPI endpoint
    print("\n\nTest 2: FastAPI Endpoint")
    print("-"*60)
    success2 = test_endpoint()

    # Summary
    print("\n" + "="*60)
    print("Summary:")
    print(f"  WatchlistManager: {'✓ PASS' if success1 else '✗ FAIL'}")
    print(f"  FastAPI Endpoint: {'✓ PASS' if success2 else '✗ FAIL'}")
    print("="*60)

    sys.exit(0 if (success1 and success2) else 1)
