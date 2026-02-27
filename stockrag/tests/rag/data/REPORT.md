# Finnhub Data Pull -- AAPL
Generated: 2026-02-27  |  Free tier endpoints only

---

## 1. Price Data

### `quote_AAPL`
- **Shape**: dict | flat keys: ['c', 'd', 'dp', 'h', 'l', 'o', 'pc', 't']
- **JSON**: `data/json/quote_AAPL.json`
- **CSV**:  `data/csv/quote_AAPL.csv`
- **Sample**: {'c': 272.95, 'd': -1.28, 'dp': -0.4668, 'h': 276.11, 'l': 270.795, 'o': 274.945}

### `candles_daily_1y_AAPL`
- **Shape**: 0 rows
- **JSON**: `data/json/candles_daily_1y_AAPL.json`

### `candles_daily_5y_AAPL`
- **Shape**: 0 rows
- **JSON**: `data/json/candles_daily_5y_AAPL.json`

### `candles_weekly_5y_AAPL`
- **Shape**: 0 rows
- **JSON**: `data/json/candles_weekly_5y_AAPL.json`

### `candles_monthly_5y_AAPL`
- **Shape**: 0 rows
- **JSON**: `data/json/candles_monthly_5y_AAPL.json`

### `dividends_AAPL`
- ERROR: HTTP 403

### `splits_AAPL`
- ERROR: HTTP 403

### `market_status`
- **Shape**: dict | flat keys: ['exchange', 'holiday', 'isOpen', 'session', 't', 'timezone']
- **JSON**: `data/json/market_status.json`
- **CSV**:  `data/csv/market_status.csv`
- **Sample**: {'exchange': 'US', 'holiday': None, 'isOpen': False, 'session': None, 't': 1772169682, 'timezone': 'America/New_York'}


## 2. Technical Analysis

### `aggregate_indicator_AAPL`
- ERROR: HTTP 403

### `rsi_AAPL`
- ERROR: HTTP 403

### `ema_AAPL`
- ERROR: HTTP 403

### `macd_AAPL`
- ERROR: HTTP 403

### `bbands_AAPL`
- ERROR: HTTP 403

### `patterns_AAPL`
- ERROR: HTTP 403

### `support_resistance_AAPL`
- ERROR: HTTP 403


## 3. Company Intelligence

### `company_profile_AAPL`
- **Shape**: dict | flat keys: ['country', 'currency', 'estimateCurrency', 'exchange', 'finnhubIndustry', 'ipo', 'logo', 'marketCapitalization', 'name', 'phone', 'shareOutstanding', 'ticker', 'weburl']
- **JSON**: `data/json/company_profile_AAPL.json`
- **CSV**:  `data/csv/company_profile_AAPL.csv`
- **Sample**: {'country': 'US', 'currency': 'USD', 'estimateCurrency': 'USD', 'exchange': 'NASDAQ NMS - GLOBAL MARKET', 'finnhubIndustry': 'Technology', 'ipo': '1980-12-12'}

### `executives_AAPL`
- ERROR: HTTP 403

### `peers_AAPL`
- **Shape**: 12 rows
- **JSON**: `data/json/peers_AAPL.json`

### `recommendations_AAPL`
- **Shape**: 4 rows | fields: ['buy', 'hold', 'period', 'sell', 'strongBuy', 'strongSell', 'symbol']
- **JSON**: `data/json/recommendations_AAPL.json`
- **CSV**:  `data/csv/recommendations_AAPL.csv`

### `price_target_AAPL`
- ERROR: HTTP 403

### `upgrades_downgrades_AAPL`
- ERROR: HTTP 403

### `insider_transactions_AAPL`
- **Shape**: dict | flat keys: ['symbol'] | nested lists: {'data': 118}
- **JSON**: `data/json/insider_transactions_AAPL.json`
- **CSV**:  `data/csv/insider_transactions_AAPL.csv`
- **Sample**: {'symbol': 'AAPL'}

### `insider_sentiment_AAPL`
- **Shape**: dict | flat keys: ['symbol'] | nested lists: {'data': 8}
- **JSON**: `data/json/insider_sentiment_AAPL.json`
- **CSV**:  `data/csv/insider_sentiment_AAPL.csv`
- **Sample**: {'symbol': 'AAPL'}

### `supply_chain_AAPL`
- ERROR: HTTP 403

### `press_releases_AAPL`
- ERROR: Expecting value: line 1 column 1 (char 0)


## 4. Fundamental Data

### `basic_financials_AAPL`
- **Shape**: dict | flat keys: ['metricType', 'symbol']
- **JSON**: `data/json/basic_financials_AAPL.json`
- **CSV**:  `data/csv/basic_financials_metrics_AAPL.csv`
- **Sample**: {'metricType': 'all', 'symbol': 'AAPL'}

### `earnings_AAPL`
- **Shape**: 4 rows | fields: ['actual', 'estimate', 'period', 'quarter', 'surprise', 'surprisePercent', 'symbol', 'year']
- **JSON**: `data/json/earnings_AAPL.json`
- **CSV**:  `data/csv/earnings_AAPL.csv`

### `eps_estimates_AAPL`
- ERROR: HTTP 403

### `revenue_estimates_AAPL`
- ERROR: HTTP 403

### `ebitda_estimates_AAPL`
- ERROR: HTTP 403

### `income_statement_annual_AAPL`
- ERROR: HTTP 403

### `balance_sheet_quarterly_AAPL`
- ERROR: HTTP 403

### `cash_flow_annual_AAPL`
- ERROR: HTTP 403

### `revenue_breakdown_AAPL`
- ERROR: HTTP 403

### `sec_filings_AAPL`
- **Shape**: 250 rows | fields: ['accessNumber', 'symbol', 'cik', 'form', 'filedDate', 'acceptedDate', 'reportUrl', 'filingUrl']
- **JSON**: `data/json/sec_filings_AAPL.json`
- **CSV**:  `data/csv/sec_filings_AAPL.csv`


## 5. News & Sentiment

### `company_news_AAPL`
- **Shape**: 243 rows | fields: ['category', 'datetime', 'headline', 'id', 'image', 'related', 'source', 'summary', 'url']
- **JSON**: `data/json/company_news_AAPL.json`
- **CSV**:  `data/csv/company_news_AAPL.csv`

### `news_sentiment_AAPL`
- ERROR: HTTP 403

### `social_sentiment_AAPL`
- ERROR: HTTP 403

### `market_news_general`
- **Shape**: 100 rows | fields: ['category', 'datetime', 'headline', 'id', 'image', 'related', 'source', 'summary', 'url']
- **JSON**: `data/json/market_news_general.json`
- **CSV**:  `data/csv/market_news_general.csv`


## 6. Calendars & Macro

### `earnings_calendar_30d`
- **Shape**: dict | flat keys: [] | nested lists: {'earningsCalendar': 1500}
- **JSON**: `data/json/earnings_calendar_30d.json`
- **CSV**:  `data/csv/earnings_calendar_30d.csv`

### `ipo_calendar`
- **Shape**: dict | flat keys: [] | nested lists: {'ipoCalendar': 101}
- **JSON**: `data/json/ipo_calendar.json`
- **CSV**:  `data/csv/ipo_calendar.csv`

### `economic_calendar`
- ERROR: HTTP 403

### `economic_codes`
- ERROR: HTTP 403

### `economic_US_GDP`
- ERROR: HTTP 403


## 7. ETFs & Indices

### `sp500_constituents`
- ERROR: HTTP 403

### `etf_profile_SPY`
- ERROR: HTTP 403

### `etf_holdings_SPY`
- ERROR: HTTP 403

### `etf_sector_SPY`
- ERROR: HTTP 403


---

## What This Data Means for Your RAG Stock Recommender

| Category | Key Files | How to use in RAG |
|----------|-----------|-------------------|
| Price history | `candles_daily_5y_AAPL.csv` | Numerical features, momentum, moving averages |
| Real-time quote | `quote_AAPL.json` | Current price context at query time |
| Dividends & splits | `dividends_AAPL.csv` | Adjust historical prices; income signal |
| Technical signals | `aggregate_indicator_AAPL.json`, `rsi/macd/bbands` | Pre-computed buy/sell signals as retrieval features |
| Company profile | `company_profile_AAPL.json` | Rich text chunk: name, sector, description, exchange |
| Executives | `executives_AAPL.csv` | Leadership context for news correlation |
| Fundamentals (117 metrics) | `basic_financials_metrics_AAPL.csv` | Core numerical retrieval: P/E, ROE, beta, margins |
| Fundamental series | `basic_financials_series_annual/quarterly_AAPL.csv` | Trend over time: is P/E expanding or contracting? |
| Income / Balance / CF | `income_statement_annual_AAPL.json` etc | Deep fundamental context for LLM reasoning |
| Earnings history | `earnings_AAPL.csv` | EPS surprise track record -- key signal |
| Forward estimates | `eps_estimates_AAPL.csv`, `revenue_estimates_AAPL.csv` | Analyst growth expectations |
| Analyst ratings | `recommendations_AAPL.csv`, `price_target_AAPL.json` | Consensus signal |
| Upgrades/downgrades | `upgrades_downgrades_AAPL.csv` | Rating change events as text chunks |
| Insider transactions | `insider_transactions_AAPL.csv` | Unusual buying/selling signal |
| Insider sentiment (MSPR) | `insider_sentiment_AAPL.csv` | Net insider buy/sell pressure monthly |
| Company news | `company_news_AAPL.csv` | Primary text corpus for embedding |
| News sentiment | `news_sentiment_AAPL.json` | Pre-scored bull/bear signal |
| Social sentiment | `social_sentiment_AAPL.csv` | Reddit/Twitter mention trends |
| Press releases | `press_releases_AAPL.csv` | Major events as embeddable text |
| Supply chain | `supply_chain_AAPL.json` | Upstream/downstream relationship graph |
| Earnings calendar | `earnings_calendar_30d.csv` | Upcoming catalyst awareness |
| S&P 500 membership | `sp500_constituents.json` | Universe/benchmark context |
| ETF holdings | `etf_holdings_SPY.csv` | Institutional weighting context |

Generated: 2026-02-27T00:21:37.737024