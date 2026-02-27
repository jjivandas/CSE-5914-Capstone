# Finnhub Data Puller

Part of the **RAG-Based Stock Recommender** capstone project.

This script pulls all available free-tier data from the [Finnhub API](https://finnhub.io) for a given stock symbol, saves everything as JSON + CSV, and generates a `REPORT.md` summarising exactly what came back.

---

## Setup

```bash
pip install requests pandas
```

Get a free API key at [finnhub.io/register](https://finnhub.io/register).

---

## Usage

```bash
python finnhub_puller.py --key YOUR_API_KEY
```

Output lands in a `data/` folder next to the script:

```
data/
  json/        ← raw API response per endpoint
  csv/         ← every tabular dataset as CSV
  REPORT.md    ← field names, row counts, sample values for everything pulled
```

---

## What Gets Pulled

### ✅ Confirmed free (from our test run)

| Category | Endpoint | Output | Notes |
|----------|----------|--------|-------|
| **Price** | Real-time quote | `quote_AAPL.csv` | c, d, dp, h, l, o, pc |
| **Price** | Market status | `market_status.csv` | Is exchange open right now |
| **Company** | Company profile | `company_profile_AAPL.csv` | Name, sector, exchange, market cap, IPO date, logo URL |
| **Company** | Peers | `peers_AAPL.json` | 12 peer tickers |
| **Company** | Insider transactions | `insider_transactions_AAPL.csv` | 118 records — who bought/sold, how many shares |
| **Company** | Insider sentiment (MSPR) | `insider_sentiment_AAPL.csv` | Monthly net insider buy/sell pressure |
| **Analyst** | Recommendation trends | `recommendations_AAPL.csv` | Buy/hold/sell consensus by month |
| **Fundamentals** | Basic financials | `basic_financials_metrics_AAPL.csv` | 117 metrics: P/E, ROE, beta, margins, 52-week range, etc |
| **Fundamentals** | Fundamental series | `basic_financials_series_annual_AAPL.csv` | Annual point-in-time snapshots of ~30 metrics |
| **Fundamentals** | Fundamental series | `basic_financials_series_quarterly_AAPL.csv` | Quarterly point-in-time snapshots |
| **Fundamentals** | Earnings history | `earnings_AAPL.csv` | EPS actual vs estimate + surprise % (4 quarters) |
| **Filings** | SEC filings | `sec_filings_AAPL.csv` | 250 filings — form type, date, URL |
| **News** | Company news | `company_news_AAPL.csv` | 243 articles — headline, summary, source, URL |
| **News** | Market news | `market_news_general.csv` | 100 general market articles |
| **Calendar** | Earnings calendar | `earnings_calendar_30d.csv` | 1,500 upcoming earnings across all stocks |
| **Calendar** | IPO calendar | `ipo_calendar.csv` | 101 recent IPOs |

### ❌ Paywalled on free tier (returns HTTP 403)

Price history (candles), dividends, splits, all technical indicators (RSI/MACD/EMA/Bollinger), executives, price targets, upgrades/downgrades, supply chain, forward estimates (EPS/revenue/EBITDA), financial statements (income/balance sheet/cash flow), news sentiment score, social sentiment, economic data, S&P 500 constituents, all ETF data.

> **Note on candles:** The candle endpoint returns `{"s": "no_data"}` rather than 403 — it may be rate-restricted or require a paid key for historical data. Supplement with `yfinance` (see below).

---

## Supplementing Price History with yfinance

Since Finnhub's free tier doesn't return OHLCV history, use `yfinance` which is completely free with no API key:

```bash
pip install yfinance
```

```python
import yfinance as yf

df = yf.download("AAPL", start="2020-01-01", end="2026-02-27")
df.to_csv("data/csv/candles_daily_5y_AAPL.csv")
```

---

## How This Data Feeds the RAG Pipeline

| Data | File | Role in RAG |
|------|------|-------------|
| Company news (243 articles) | `company_news_AAPL.csv` | **Primary text corpus** — embed headline + summary as chunks |
| Market news (100 articles) | `market_news_general.csv` | Macro context chunks |
| Company profile | `company_profile_AAPL.csv` | Structured metadata attached to each chunk |
| Basic financials (117 metrics) | `basic_financials_metrics_AAPL.csv` | Numerical retrieval features |
| Fundamental series | `basic_financials_series_*.csv` | Trend signals — is P/E expanding? margins improving? |
| Earnings history | `earnings_AAPL.csv` | EPS surprise track record — strong signal for recommender |
| Analyst recommendations | `recommendations_AAPL.csv` | Consensus buy/hold/sell as retrieval feature |
| Insider transactions | `insider_transactions_AAPL.csv` | Unusual activity signal |
| Insider sentiment (MSPR) | `insider_sentiment_AAPL.csv` | Net insider pressure, monthly |
| SEC filings | `sec_filings_AAPL.csv` | Links to source documents for deeper retrieval |
| Earnings calendar | `earnings_calendar_30d.csv` | Upcoming catalyst awareness |
| Price history (yfinance) | `candles_daily_5y_AAPL.csv` | Momentum features, moving averages |

---

## Rate Limits

- Free tier: **60 calls/minute**
- Script uses a **0.6s sleep** between calls — safe buffer
- Full AAPL pull takes ~2–3 minutes
- To scale to 500+ symbols: batch overnight, add checkpointing to skip already-pulled files

---

## Project Context

This data collection is **Step 1** of the RAG stock recommender pipeline:

```
1. Data Collection  ← this script
2. Chunking & Embedding
3. Vector Store Ingestion
4. Query + Retrieval
5. LLM Generation (recommendation)
```