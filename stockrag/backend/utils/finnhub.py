from __future__ import annotations

import asyncio
import logging
import time

import httpx

logger = logging.getLogger(__name__)

_QUOTE_URL = "https://finnhub.io/api/v1/quote"
_CACHE_TTL = 60  # seconds
_cache: dict[str, tuple[float, float]] = {}  # ticker -> (price, timestamp)


async def _fetch_one(
    client: httpx.AsyncClient,
    ticker: str,
    api_key: str,
) -> tuple[str, float | None]:
    now = time.monotonic()
    cached = _cache.get(ticker)
    if cached and (now - cached[1]) < _CACHE_TTL:
        return ticker, cached[0]

    try:
        resp = await client.get(
            _QUOTE_URL,
            params={"symbol": ticker, "token": api_key},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
        price = data.get("c")
        if isinstance(price, (int, float)) and price > 0:
            _cache[ticker] = (float(price), now)
            return ticker, float(price)
    except Exception:
        logger.debug("Finnhub quote failed for %s", ticker, exc_info=True)

    return ticker, None


async def fetch_prices(
    tickers_by_cik: dict[str, str],
    api_key: str,
) -> dict[str, float]:
    """Fetch live prices for tickers in parallel.

    Args:
        tickers_by_cik: mapping of CIK -> ticker symbol
        api_key: Finnhub API key

    Returns:
        dict of CIK -> price for tickers that returned a valid price
    """
    if not api_key:
        return {}

    valid = {cik: t for cik, t in tickers_by_cik.items() if t}
    if not valid:
        return {}

    async with httpx.AsyncClient() as client:
        tasks = [_fetch_one(client, ticker, api_key) for ticker in valid.values()]
        results = await asyncio.gather(*tasks)

    ticker_to_price = {t: p for t, p in results if p is not None}

    return {
        cik: ticker_to_price[ticker]
        for cik, ticker in valid.items()
        if ticker in ticker_to_price
    }
