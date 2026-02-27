"""
finnhub_puller.py
=================
Pulls all free-tier Finnhub data for AAPL.
Saves everything as JSON + CSV and generates REPORT.md.

Usage:
    pip install requests pandas
    python finnhub_puller.py --key YOUR_API_KEY

Output:
    data/
      json/     <- raw API response per endpoint
      csv/      <- every tabular dataset as CSV
    data/REPORT.md
"""

import os
import json
import time
import argparse
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

SYMBOL      = "AAPL"
EXCHANGE    = "US"
BASE_URL    = "https://finnhub.io/api/v1"
RATE_LIMIT  = 0.6   # seconds between calls (free tier = 60/min)

TODAY       = datetime.today()
TODAY_STR   = TODAY.strftime("%Y-%m-%d")
ONE_YEAR    = (TODAY - timedelta(days=365)).strftime("%Y-%m-%d")
FIVE_YEARS  = (TODAY - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
TS_NOW      = int(TODAY.timestamp())
TS_1Y       = int((TODAY - timedelta(days=365)).timestamp())
TS_5Y       = int((TODAY - timedelta(days=365 * 5)).timestamp())
TS_30D      = int((TODAY - timedelta(days=30)).timestamp())

# ── Filesystem ────────────────────────────────────────────────────────────────

def setup():
    Path("data/json").mkdir(parents=True, exist_ok=True)
    Path("data/csv").mkdir(parents=True, exist_ok=True)

def save_json(name, data):
    path = f"data/json/{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path

def save_csv(name, data):
    """Coerce data to DataFrame and save CSV. Returns path or None."""
    try:
        if isinstance(data, list) and data and isinstance(data[0], dict):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and "_error" not in data:
            # Hunt for the first list-of-dicts inside the response
            for val in data.values():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    df = pd.DataFrame(val)
                    break
            else:
                df = pd.DataFrame([data])
        else:
            return None
        path = f"data/csv/{name}.csv"
        df.to_csv(path, index=False)
        return path
    except Exception:
        return None

# ── API call ──────────────────────────────────────────────────────────────────

def get(endpoint, params, api_key):
    params["token"] = api_key
    try:
        r = requests.get(BASE_URL + endpoint, params=params, timeout=10)
        time.sleep(RATE_LIMIT)
        if r.status_code == 200:
            return r.json()
        return {"_error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"_error": str(e)}

# ── Candle helper ─────────────────────────────────────────────────────────────

def candles_to_rows(data):
    """Convert Finnhub parallel-list candle response to list of row dicts."""
    if not isinstance(data, dict) or data.get("s") != "ok":
        return []
    return [
        {
            "date":   datetime.utcfromtimestamp(data["t"][i]).strftime("%Y-%m-%d"),
            "open":   data["o"][i],
            "high":   data["h"][i],
            "low":    data["l"][i],
            "close":  data["c"][i],
            "volume": data["v"][i],
        }
        for i in range(len(data["c"]))
    ]

# ── Report builder ────────────────────────────────────────────────────────────

_report = []

def log(line=""):
    print(line)
    _report.append(line)

def section(title):
    log()
    log(f"## {title}")
    log()

def record(name, data, json_path, csv_path=None):
    """Append one entry to the report."""
    log(f"### `{name}`")

    if isinstance(data, dict) and "_error" in data:
        log(f"- ERROR: {data['_error']}")
        log()
        return

    # Shape description
    if isinstance(data, list):
        shape = f"{len(data)} rows"
        if data and isinstance(data[0], dict):
            shape += f" | fields: {list(data[0].keys())}"
    elif isinstance(data, dict):
        nested = {k: len(v) for k, v in data.items() if isinstance(v, list)}
        flat   = [k for k, v in data.items() if not isinstance(v, (dict, list))]
        shape  = f"dict | flat keys: {flat}"
        if nested:
            shape += f" | nested lists: {nested}"
    else:
        shape = str(type(data))

    log(f"- **Shape**: {shape}")
    log(f"- **JSON**: `{json_path}`")
    if csv_path:
        log(f"- **CSV**:  `{csv_path}`")

    # Print sample values for flat dicts
    if isinstance(data, dict) and "_error" not in data:
        flat = {k: v for k, v in data.items() if not isinstance(v, (dict, list))}
        if flat:
            sample = dict(list(flat.items())[:6])
            log(f"- **Sample**: {sample}")

    log()

# ── Main ──────────────────────────────────────────────────────────────────────

def pull(api_key):
    setup()

    log(f"# Finnhub Data Pull -- {SYMBOL}")
    log(f"Generated: {TODAY_STR}  |  Free tier endpoints only")
    log()
    log("---")

    # =====================================================================
    section("1. Price Data")
    # =====================================================================

    # Real-time quote
    data = get("/quote", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"quote_{SYMBOL}", data)
    cp = save_csv(f"quote_{SYMBOL}", data)
    record(f"quote_{SYMBOL}", data, jp, cp)

    # Daily candles - 1 year
    raw = get("/stock/candle", {"symbol": SYMBOL, "resolution": "D", "from": TS_1Y, "to": TS_NOW}, api_key)
    rows = candles_to_rows(raw)
    jp = save_json(f"candles_daily_1y_{SYMBOL}", raw)
    cp = save_csv(f"candles_daily_1y_{SYMBOL}", rows)
    record(f"candles_daily_1y_{SYMBOL}", rows, jp, cp)

    # Daily candles - 5 years
    raw = get("/stock/candle", {"symbol": SYMBOL, "resolution": "D", "from": TS_5Y, "to": TS_NOW}, api_key)
    rows = candles_to_rows(raw)
    jp = save_json(f"candles_daily_5y_{SYMBOL}", raw)
    cp = save_csv(f"candles_daily_5y_{SYMBOL}", rows)
    record(f"candles_daily_5y_{SYMBOL}", rows, jp, cp)

    # Weekly candles - 5 years
    raw = get("/stock/candle", {"symbol": SYMBOL, "resolution": "W", "from": TS_5Y, "to": TS_NOW}, api_key)
    rows = candles_to_rows(raw)
    jp = save_json(f"candles_weekly_5y_{SYMBOL}", raw)
    cp = save_csv(f"candles_weekly_5y_{SYMBOL}", rows)
    record(f"candles_weekly_5y_{SYMBOL}", rows, jp, cp)

    # Monthly candles - 5 years
    raw = get("/stock/candle", {"symbol": SYMBOL, "resolution": "M", "from": TS_5Y, "to": TS_NOW}, api_key)
    rows = candles_to_rows(raw)
    jp = save_json(f"candles_monthly_5y_{SYMBOL}", raw)
    cp = save_csv(f"candles_monthly_5y_{SYMBOL}", rows)
    record(f"candles_monthly_5y_{SYMBOL}", rows, jp, cp)

    # Dividends
    data = get("/stock/dividend", {"symbol": SYMBOL, "from": FIVE_YEARS, "to": TODAY_STR}, api_key)
    jp = save_json(f"dividends_{SYMBOL}", data)
    cp = save_csv(f"dividends_{SYMBOL}", data)
    record(f"dividends_{SYMBOL}", data, jp, cp)

    # Splits
    data = get("/stock/split", {"symbol": SYMBOL, "from": "2000-01-01", "to": TODAY_STR}, api_key)
    jp = save_json(f"splits_{SYMBOL}", data)
    cp = save_csv(f"splits_{SYMBOL}", data)
    record(f"splits_{SYMBOL}", data, jp, cp)

    # Market status
    data = get("/stock/market-status", {"exchange": "US"}, api_key)
    jp = save_json("market_status", data)
    cp = save_csv("market_status", data)
    record("market_status", data, jp, cp)

    # =====================================================================
    section("2. Technical Analysis")
    # =====================================================================

    # Aggregate indicator (overall buy/sell/neutral signal)
    data = get("/scan/technical-indicator", {"symbol": SYMBOL, "resolution": "D"}, api_key)
    jp = save_json(f"aggregate_indicator_{SYMBOL}", data)
    cp = save_csv(f"aggregate_indicator_{SYMBOL}", data)
    record(f"aggregate_indicator_{SYMBOL}", data, jp, cp)

    # RSI
    data = get("/indicator", {"symbol": SYMBOL, "resolution": "D", "from": TS_1Y, "to": TS_NOW, "indicator": "rsi", "timeperiod": 14}, api_key)
    jp = save_json(f"rsi_{SYMBOL}", data)
    record(f"rsi_{SYMBOL}", data, jp)

    # EMA
    data = get("/indicator", {"symbol": SYMBOL, "resolution": "D", "from": TS_1Y, "to": TS_NOW, "indicator": "ema", "timeperiod": 20}, api_key)
    jp = save_json(f"ema_{SYMBOL}", data)
    record(f"ema_{SYMBOL}", data, jp)

    # MACD
    data = get("/indicator", {"symbol": SYMBOL, "resolution": "D", "from": TS_1Y, "to": TS_NOW, "indicator": "macd"}, api_key)
    jp = save_json(f"macd_{SYMBOL}", data)
    record(f"macd_{SYMBOL}", data, jp)

    # Bollinger Bands
    data = get("/indicator", {"symbol": SYMBOL, "resolution": "D", "from": TS_1Y, "to": TS_NOW, "indicator": "bbands", "timeperiod": 20}, api_key)
    jp = save_json(f"bbands_{SYMBOL}", data)
    record(f"bbands_{SYMBOL}", data, jp)

    # Candlestick pattern recognition
    data = get("/scan/pattern", {"symbol": SYMBOL, "resolution": "D"}, api_key)
    jp = save_json(f"patterns_{SYMBOL}", data)
    cp = save_csv(f"patterns_{SYMBOL}", data)
    record(f"patterns_{SYMBOL}", data, jp, cp)

    # Support & resistance levels
    data = get("/scan/support-resistance", {"symbol": SYMBOL, "resolution": "D"}, api_key)
    jp = save_json(f"support_resistance_{SYMBOL}", data)
    cp = save_csv(f"support_resistance_{SYMBOL}", data)
    record(f"support_resistance_{SYMBOL}", data, jp, cp)

    # =====================================================================
    section("3. Company Intelligence")
    # =====================================================================

    # Company profile
    data = get("/stock/profile2", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"company_profile_{SYMBOL}", data)
    cp = save_csv(f"company_profile_{SYMBOL}", data)
    record(f"company_profile_{SYMBOL}", data, jp, cp)

    # Executives
    data = get("/stock/executive", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"executives_{SYMBOL}", data)
    cp = save_csv(f"executives_{SYMBOL}", data)
    record(f"executives_{SYMBOL}", data, jp, cp)

    # Peers
    data = get("/stock/peers", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"peers_{SYMBOL}", data)
    record(f"peers_{SYMBOL}", data, jp)

    # Recommendation trends
    data = get("/stock/recommendation", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"recommendations_{SYMBOL}", data)
    cp = save_csv(f"recommendations_{SYMBOL}", data)
    record(f"recommendations_{SYMBOL}", data, jp, cp)

    # Price target
    data = get("/stock/price-target", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"price_target_{SYMBOL}", data)
    cp = save_csv(f"price_target_{SYMBOL}", data)
    record(f"price_target_{SYMBOL}", data, jp, cp)

    # Analyst upgrades / downgrades
    data = get("/stock/upgrade-downgrade", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"upgrades_downgrades_{SYMBOL}", data)
    cp = save_csv(f"upgrades_downgrades_{SYMBOL}", data)
    record(f"upgrades_downgrades_{SYMBOL}", data, jp, cp)

    # Insider transactions
    data = get("/stock/insider-transactions", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"insider_transactions_{SYMBOL}", data)
    cp = save_csv(f"insider_transactions_{SYMBOL}", data)
    record(f"insider_transactions_{SYMBOL}", data, jp, cp)

    # Insider sentiment (MSPR)
    data = get("/stock/insider-sentiment", {"symbol": SYMBOL, "from": ONE_YEAR, "to": TODAY_STR}, api_key)
    jp = save_json(f"insider_sentiment_{SYMBOL}", data)
    cp = save_csv(f"insider_sentiment_{SYMBOL}", data)
    record(f"insider_sentiment_{SYMBOL}", data, jp, cp)

    # Supply chain
    data = get("/stock/supply-chain", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"supply_chain_{SYMBOL}", data)
    cp = save_csv(f"supply_chain_{SYMBOL}", data)
    record(f"supply_chain_{SYMBOL}", data, jp, cp)

    # Press releases / major developments
    data = get("/stock/press-releases", {"symbol": SYMBOL, "from": ONE_YEAR, "to": TODAY_STR}, api_key)
    jp = save_json(f"press_releases_{SYMBOL}", data)
    cp = save_csv(f"press_releases_{SYMBOL}", data)
    record(f"press_releases_{SYMBOL}", data, jp, cp)

    # =====================================================================
    section("4. Fundamental Data")
    # =====================================================================

    # Basic financials (117 metrics + historical series)
    data = get("/stock/metric", {"symbol": SYMBOL, "metric": "all"}, api_key)
    jp = save_json(f"basic_financials_{SYMBOL}", data)
    if isinstance(data, dict) and "metric" in data:
        cp = save_csv(f"basic_financials_metrics_{SYMBOL}", data["metric"])
        if "series" in data:
            for freq in ("annual", "quarterly"):
                series = data["series"].get(freq, {})
                rows = []
                for metric_name, pts in series.items():
                    for pt in pts:
                        rows.append({"metric": metric_name, "period": pt.get("period"), "value": pt.get("v")})
                if rows:
                    save_csv(f"basic_financials_series_{freq}_{SYMBOL}", rows)
    else:
        cp = None
    record(f"basic_financials_{SYMBOL}", data, jp, cp)

    # Earnings history (EPS estimate vs actual)
    data = get("/stock/earnings", {"symbol": SYMBOL, "limit": 16}, api_key)
    jp = save_json(f"earnings_{SYMBOL}", data)
    cp = save_csv(f"earnings_{SYMBOL}", data)
    record(f"earnings_{SYMBOL}", data, jp, cp)

    # EPS estimates (forward)
    data = get("/stock/eps-estimate", {"symbol": SYMBOL, "freq": "quarterly"}, api_key)
    jp = save_json(f"eps_estimates_{SYMBOL}", data)
    cp = save_csv(f"eps_estimates_{SYMBOL}", data)
    record(f"eps_estimates_{SYMBOL}", data, jp, cp)

    # Revenue estimates (forward)
    data = get("/stock/revenue-estimate", {"symbol": SYMBOL, "freq": "quarterly"}, api_key)
    jp = save_json(f"revenue_estimates_{SYMBOL}", data)
    cp = save_csv(f"revenue_estimates_{SYMBOL}", data)
    record(f"revenue_estimates_{SYMBOL}", data, jp, cp)

    # EBITDA estimates
    data = get("/stock/ebitda-estimate", {"symbol": SYMBOL, "freq": "annual"}, api_key)
    jp = save_json(f"ebitda_estimates_{SYMBOL}", data)
    cp = save_csv(f"ebitda_estimates_{SYMBOL}", data)
    record(f"ebitda_estimates_{SYMBOL}", data, jp, cp)

    # Standardized financials - Income Statement
    data = get("/stock/financials", {"symbol": SYMBOL, "statement": "ic", "freq": "annual"}, api_key)
    jp = save_json(f"income_statement_annual_{SYMBOL}", data)
    record(f"income_statement_annual_{SYMBOL}", data, jp)

    # Standardized financials - Balance Sheet
    data = get("/stock/financials", {"symbol": SYMBOL, "statement": "bs", "freq": "quarterly"}, api_key)
    jp = save_json(f"balance_sheet_quarterly_{SYMBOL}", data)
    record(f"balance_sheet_quarterly_{SYMBOL}", data, jp)

    # Standardized financials - Cash Flow
    data = get("/stock/financials", {"symbol": SYMBOL, "statement": "cf", "freq": "annual"}, api_key)
    jp = save_json(f"cash_flow_annual_{SYMBOL}", data)
    record(f"cash_flow_annual_{SYMBOL}", data, jp)

    # Revenue breakdown by segment
    data = get("/stock/revenue-breakdown", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"revenue_breakdown_{SYMBOL}", data)
    cp = save_csv(f"revenue_breakdown_{SYMBOL}", data)
    record(f"revenue_breakdown_{SYMBOL}", data, jp, cp)

    # SEC filings list
    data = get("/stock/filings", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"sec_filings_{SYMBOL}", data)
    cp = save_csv(f"sec_filings_{SYMBOL}", data)
    record(f"sec_filings_{SYMBOL}", data, jp, cp)

    # =====================================================================
    section("5. News & Sentiment")
    # =====================================================================

    # Company news (1 year)
    data = get("/company-news", {"symbol": SYMBOL, "from": ONE_YEAR, "to": TODAY_STR}, api_key)
    jp = save_json(f"company_news_{SYMBOL}", data)
    cp = save_csv(f"company_news_{SYMBOL}", data)
    record(f"company_news_{SYMBOL}", data, jp, cp)

    # News sentiment score
    data = get("/news-sentiment", {"symbol": SYMBOL}, api_key)
    jp = save_json(f"news_sentiment_{SYMBOL}", data)
    cp = save_csv(f"news_sentiment_{SYMBOL}", data)
    record(f"news_sentiment_{SYMBOL}", data, jp, cp)

    # Social sentiment (Reddit + Twitter)
    data = get("/stock/social-sentiment", {"symbol": SYMBOL, "from": ONE_YEAR, "to": TODAY_STR}, api_key)
    jp = save_json(f"social_sentiment_{SYMBOL}", data)
    cp = save_csv(f"social_sentiment_{SYMBOL}", data)
    record(f"social_sentiment_{SYMBOL}", data, jp, cp)

    # General market news
    data = get("/news", {"category": "general"}, api_key)
    jp = save_json("market_news_general", data)
    cp = save_csv("market_news_general", data)
    record("market_news_general", data, jp, cp)

    # =====================================================================
    section("6. Calendars & Macro")
    # =====================================================================

    # Earnings calendar (next 30 days - all stocks)
    data = get("/calendar/earnings", {
        "from": TODAY_STR,
        "to": (TODAY + timedelta(days=30)).strftime("%Y-%m-%d")
    }, api_key)
    jp = save_json("earnings_calendar_30d", data)
    cp = save_csv("earnings_calendar_30d", data)
    record("earnings_calendar_30d", data, jp, cp)

    # IPO calendar (last 30 days)
    data = get("/calendar/ipo", {
        "from": (TODAY - timedelta(days=30)).strftime("%Y-%m-%d"),
        "to": TODAY_STR
    }, api_key)
    jp = save_json("ipo_calendar", data)
    cp = save_csv("ipo_calendar", data)
    record("ipo_calendar", data, jp, cp)

    # Economic calendar
    data = get("/calendar/economic", {}, api_key)
    jp = save_json("economic_calendar", data)
    cp = save_csv("economic_calendar", data)
    record("economic_calendar", data, jp, cp)

    # Economic data codes (list of available macro series)
    data = get("/economic/code", {}, api_key)
    jp = save_json("economic_codes", data)
    cp = save_csv("economic_codes", data)
    record("economic_codes", data, jp, cp)

    # Economic data - US GDP (example)
    data = get("/economic", {"code": "MA-USA-656880"}, api_key)
    jp = save_json("economic_US_GDP", data)
    cp = save_csv("economic_US_GDP", data)
    record("economic_US_GDP", data, jp, cp)

    # =====================================================================
    section("7. ETFs & Indices")
    # =====================================================================

    # S&P 500 constituents
    data = get("/index/constituents", {"symbol": "^GSPC"}, api_key)
    jp = save_json("sp500_constituents", data)
    cp = save_csv("sp500_constituents", data)
    record("sp500_constituents", data, jp, cp)

    # ETF profile + holdings (SPY - AAPL is a top holding)
    data = get("/etf/profile", {"symbol": "SPY"}, api_key)
    jp = save_json("etf_profile_SPY", data)
    record("etf_profile_SPY", data, jp)

    data = get("/etf/holdings", {"symbol": "SPY"}, api_key)
    jp = save_json("etf_holdings_SPY", data)
    cp = save_csv("etf_holdings_SPY", data)
    record("etf_holdings_SPY", data, jp, cp)

    data = get("/etf/sector", {"symbol": "SPY"}, api_key)
    jp = save_json("etf_sector_SPY", data)
    cp = save_csv("etf_sector_SPY", data)
    record("etf_sector_SPY", data, jp, cp)

    # =====================================================================
    # RAG PIPELINE SUMMARY
    # =====================================================================
    log()
    log("---")
    log()
    log("## What This Data Means for Your RAG Stock Recommender")
    log()
    log("| Category | Key Files | How to use in RAG |")
    log("|----------|-----------|-------------------|")
    log("| Price history | `candles_daily_5y_AAPL.csv` | Numerical features, momentum, moving averages |")
    log("| Real-time quote | `quote_AAPL.json` | Current price context at query time |")
    log("| Dividends & splits | `dividends_AAPL.csv` | Adjust historical prices; income signal |")
    log("| Technical signals | `aggregate_indicator_AAPL.json`, `rsi/macd/bbands` | Pre-computed buy/sell signals as retrieval features |")
    log("| Company profile | `company_profile_AAPL.json` | Rich text chunk: name, sector, description, exchange |")
    log("| Executives | `executives_AAPL.csv` | Leadership context for news correlation |")
    log("| Fundamentals (117 metrics) | `basic_financials_metrics_AAPL.csv` | Core numerical retrieval: P/E, ROE, beta, margins |")
    log("| Fundamental series | `basic_financials_series_annual/quarterly_AAPL.csv` | Trend over time: is P/E expanding or contracting? |")
    log("| Income / Balance / CF | `income_statement_annual_AAPL.json` etc | Deep fundamental context for LLM reasoning |")
    log("| Earnings history | `earnings_AAPL.csv` | EPS surprise track record -- key signal |")
    log("| Forward estimates | `eps_estimates_AAPL.csv`, `revenue_estimates_AAPL.csv` | Analyst growth expectations |")
    log("| Analyst ratings | `recommendations_AAPL.csv`, `price_target_AAPL.json` | Consensus signal |")
    log("| Upgrades/downgrades | `upgrades_downgrades_AAPL.csv` | Rating change events as text chunks |")
    log("| Insider transactions | `insider_transactions_AAPL.csv` | Unusual buying/selling signal |")
    log("| Insider sentiment (MSPR) | `insider_sentiment_AAPL.csv` | Net insider buy/sell pressure monthly |")
    log("| Company news | `company_news_AAPL.csv` | Primary text corpus for embedding |")
    log("| News sentiment | `news_sentiment_AAPL.json` | Pre-scored bull/bear signal |")
    log("| Social sentiment | `social_sentiment_AAPL.csv` | Reddit/Twitter mention trends |")
    log("| Press releases | `press_releases_AAPL.csv` | Major events as embeddable text |")
    log("| Supply chain | `supply_chain_AAPL.json` | Upstream/downstream relationship graph |")
    log("| Earnings calendar | `earnings_calendar_30d.csv` | Upcoming catalyst awareness |")
    log("| S&P 500 membership | `sp500_constituents.json` | Universe/benchmark context |")
    log("| ETF holdings | `etf_holdings_SPY.csv` | Institutional weighting context |")
    log()
    log(f"Generated: {datetime.now().isoformat()}")

    # Write report
    Path("data/REPORT.md").write_text("\n".join(_report))
    json_count = len(list(Path("data/json").iterdir()))
    csv_count  = len(list(Path("data/csv").iterdir()))
    print("\n" + "=" * 60)
    print("Done!")
    print(f"  JSON   ->  data/json/   ({json_count} files)")
    print(f"  CSV    ->  data/csv/    ({csv_count} files)")
    print(f"  Report ->  data/REPORT.md")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finnhub free-tier data puller -- AAPL")
    parser.add_argument("--key", required=True, help="Finnhub API key")
    args = parser.parse_args()
    pull(args.key)