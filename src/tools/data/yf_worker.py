"""Top-level yfinance call wrappers, executed in an isolated worker process.

yfinance's HTTP backend (curl_cffi) is known to segfault with no Python
traceback when repeatedly hitting 404/401 errors for delisted/invalid
tickers (confirmed via apport crash reports in production). These functions
must stay free of any project imports beyond stdlib/pandas/yfinance so they
stay cheaply picklable and importable in a freshly spawned worker.
"""


def fetch_ticker_info(ticker: str) -> dict:
    import yfinance as yf

    return dict(yf.Ticker(ticker).info or {})


def fetch_ticker_history(ticker: str, start: str):
    import yfinance as yf

    return yf.Ticker(ticker).history(start=start, interval="1d")
