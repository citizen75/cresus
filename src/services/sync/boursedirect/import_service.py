"""Bourse Direct portfolio importer - sync real portfolio data from broker."""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import base64
import hmac
import hashlib
import struct
import time

from loguru import logger
import aiohttp
from playwright.async_api import async_playwright, Browser, BrowserContext

from portfolio.journal import Journal
from portfolio.manager import PortfolioManager


@dataclass
class BourseDirectPosition:
    """Position from Bourse Direct."""
    ticker: str
    quantity: float
    current_price: float
    value: float
    isin: str


@dataclass
class BourseDirectTransaction:
    """Transaction from Bourse Direct."""
    date: str
    operation: str  # BUY, SELL
    ticker: str
    quantity: float
    price: float
    amount: float
    fees: float = 0.0


class BourseDirectAPI:
    """Bourse Direct API client."""

    BASE_URL = "https://www.boursedirect.fr"

    def __init__(self, email: str, password: str, otp_url: Optional[str] = None):
        self.email = email
        self.password = password
        self.otp_url = otp_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.context: Optional[BrowserContext] = None

    def _generate_totp(self) -> str:
        """Generate TOTP code from otpauth URL."""
        if not self.otp_url:
            raise ValueError("OTP URL not provided")

        # Extract secret from otpauth://totp/...?secret=XXX
        secret = self.otp_url.split("secret=")[1].split("&")[0]

        # Decode base32 secret
        secret_bytes = base64.b32decode(secret)

        # Generate TOTP
        counter = int(time.time()) // 30
        msg = struct.pack(">Q", counter)
        hmac_hash = hmac.new(secret_bytes, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0f
        code = (struct.unpack(">I", hmac_hash[offset:offset + 4])[0] & 0x7fffffff) % 1000000

        return str(code).zfill(6)

    async def authenticate(self) -> bool:
        """Authenticate with Bourse Direct using Playwright."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                logger.info("Navigating to Bourse Direct login page...")
                await page.goto(f"{self.BASE_URL}/login")

                # Check for existing session
                cookies = await context.cookies()
                if any(c["name"] == "CAPITOL" for c in cookies):
                    logger.info("Session cookie found, using existing session")
                    self.context = context
                    return True

                # Fill email
                await page.fill('input[name="email"]', self.email)
                await page.fill('input[name="password"]', self.password)

                # Submit login form
                await page.click('button[type="submit"]')

                # Wait for 2FA modal or redirect
                try:
                    await page.wait_for_selector('[data-testid="otp-modal"]', timeout=5000)
                    logger.info("2FA required, entering OTP...")

                    # Generate and fill OTP
                    totp = self._generate_totp()
                    for i, digit in enumerate(totp):
                        await page.fill(f'input[data-testid="otp-input-{i}"]', digit)

                    # Submit OTP
                    await page.click('button[data-testid="otp-submit"]')

                except:
                    logger.info("No 2FA required, login in progress...")

                # Wait for successful login
                await page.wait_for_url(f"{self.BASE_URL}/*", timeout=40000)
                logger.info("Login successful")

                self.context = context
                return True

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def fetch_portfolio(self) -> Dict[str, Any]:
        """Fetch portfolio data from Bourse Direct."""
        if not self.context:
            raise ValueError("Not authenticated")

        page = await self.context.new_page()

        try:
            # Fetch account data
            logger.info("Fetching portfolio data...")
            await page.goto(f"{self.BASE_URL}/streaming/compteTempsReelCK.php?stream=0&nc=1")

            content = await page.content()
            data = json.loads(content)

            return data

        except Exception as e:
            logger.error(f"Failed to fetch portfolio: {e}")
            raise
        finally:
            await page.close()

    async def fetch_transactions(self) -> List[Dict[str, Any]]:
        """Fetch transaction history from Bourse Direct."""
        if not self.context:
            raise ValueError("Not authenticated")

        page = await self.context.new_page()

        try:
            logger.info("Fetching transaction history...")
            await page.goto(f"{self.BASE_URL}/priv/new/historique-de-compte.php")

            # Parse transaction table
            transactions = []
            rows = await page.query_selector_all('table tbody tr')

            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 4:
                    date_text = await cells[0].text_content()
                    label = await cells[1].text_content()
                    amount_text = await cells[3].text_content()

                    transactions.append({
                        'date': date_text.strip(),
                        'label': label.strip(),
                        'amount': float(amount_text.strip().replace('€', '').replace(',', '.')),
                    })

            return transactions

        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            raise
        finally:
            await page.close()

    async def close(self):
        """Close browser context."""
        if self.context:
            await self.context.browser.close()


class BourseDirectImporter:
    """Import portfolio from Bourse Direct broker."""

    def __init__(self, email: str, password: str, otp_url: Optional[str] = None):
        self.api = BourseDirectAPI(email, password, otp_url)
        self.pm = PortfolioManager()

    async def sync_portfolio(self, portfolio_name: str) -> Dict[str, Any]:
        """Sync portfolio from Bourse Direct to local journal."""
        try:
            # Authenticate
            authenticated = await self.api.authenticate()
            if not authenticated:
                return {"status": "error", "message": "Authentication failed"}

            # Fetch portfolio data
            portfolio_data = await self.api.fetch_portfolio()
            transactions_data = await self.api.fetch_transactions()

            # Create or update portfolio
            result = self._create_portfolio(portfolio_name, portfolio_data)
            if result.get("status") == "error":
                return result

            # Import transactions
            self._import_transactions(portfolio_name, transactions_data)

            logger.info(f"Successfully synced portfolio '{portfolio_name}' from Bourse Direct")
            return {
                "status": "success",
                "portfolio": portfolio_name,
                "transactions_imported": len(transactions_data),
            }

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            await self.api.close()

    def _create_portfolio(self, portfolio_name: str, data: Dict) -> Dict[str, Any]:
        """Create portfolio from Bourse Direct data."""
        try:
            result = self.pm.create_portfolio(
                name=portfolio_name,
                portfolio_type="real",
                currency="EUR",
                description="Portfolio imported from Bourse Direct",
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create portfolio: {e}")
            return {"status": "error", "message": str(e)}

    def _import_transactions(self, portfolio_name: str, transactions: List[Dict]) -> int:
        """Import transactions to portfolio journal."""
        journal = Journal(portfolio_name)
        imported = 0

        for tx in transactions:
            try:
                # Parse transaction
                date_str = tx.get('date', '')
                label = tx.get('label', '')
                amount = tx.get('amount', 0)

                # Determine operation and details
                if 'achat' in label.lower():
                    operation = 'BUY'
                elif 'vente' in label.lower():
                    operation = 'SELL'
                else:
                    continue  # Skip unknown operations

                # Extract ticker from label (simplified)
                ticker = label.split('(')[1].split(')')[0] if '(' in label else ''
                if not ticker:
                    continue

                # Add transaction
                journal.add_transaction(
                    operation=operation,
                    ticker=ticker.upper(),
                    quantity=1,  # Placeholder
                    price=amount,
                    fees=0,
                    notes=label,
                    created_at=date_str,
                )
                imported += 1

            except Exception as e:
                logger.warning(f"Failed to import transaction: {e}")
                continue

        logger.info(f"Imported {imported} transactions")
        return imported


async def sync_boursedirect_portfolio(
    portfolio_name: str,
    email: str,
    password: str,
    otp_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Sync a Bourse Direct portfolio."""
    importer = BourseDirectImporter(email, password, otp_url)
    return await importer.sync_portfolio(portfolio_name)


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 3:
        print("Usage: python import_service.py <portfolio_name> <email> <password> [otp_url]")
        sys.exit(1)

    portfolio_name = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    otp_url = sys.argv[4] if len(sys.argv) > 4 else None

    result = asyncio.run(sync_boursedirect_portfolio(portfolio_name, email, password, otp_url))
    print(json.dumps(result, indent=2))
