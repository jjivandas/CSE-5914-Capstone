"""
Generate per-company embedding JSON files for the RAG pipeline.

Reads from:
  stockrag/data/processed/sec/facts.parquet         (XBRL facts, normalized)
  stockrag/data/processed/sec/entity_master.parquet (company identities)
  stockrag/data/processed/sec/concepts.parquet      (concept labels/descriptions)

Fetches (once, then cached):
  https://www.sec.gov/files/company_tickers_exchange.json  →  CIK → ticker + exchange

Writes to:
  stockrag/data/rag/companies/{CIK}.json   per-company embedding document
  stockrag/data/rag/companies_index.json   master list for downstream ingestion

Each per-company JSON contains three document types (see DATA_PIPELINE_README.md):
  1. company_profile  – prose identity + most recent FY summary + YoY trends
  2. annual_snapshot  – structured financial data per fiscal year (last 5 years)
  3. fact_sentence    – one sentence per preferred Tier-1 datapoint (all periods)

Design:
  - Pyarrow filters load only preferred Tier-1 facts — never the full 500MB table.
  - Revenue concept fallback: tries multiple XBRL names used across companies/eras.
  - Ratios and YoY growth are computed where both operands are available; skipped otherwise.
  - EDGAR ticker fetch respects the required User-Agent header and caches to disk.
"""

import argparse
import json
import logging
import os
import re
import time
import urllib.parse
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# EDGAR fetch config
# ---------------------------------------------------------------------------

EDGAR_TICKERS_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
# SEC requires a descriptive User-Agent: https://www.sec.gov/os/accessing-edgar-data
EDGAR_USER_AGENT = "StockRAG research/stockrag (contact@stockrag.dev)"

# ---------------------------------------------------------------------------
# Tier-1 concept definitions
# ---------------------------------------------------------------------------

# Revenue has multiple concept names across companies and filing eras.
# Listed in priority order — first one found for a company/year wins.
REVENUE_CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
]

# Each slot: (slot_key, display_label, [concept fallback list], preferred_unit)
# The first concept found in the company's data for a given year is used.
METRIC_SLOTS = [
    # --- Income Statement ---
    ("revenue",           "Revenue",                  REVENUE_CONCEPTS,                                                ["USD"]),
    ("gross_profit",      "Gross Profit",             ["GrossProfit"],                                                 ["USD"]),
    ("operating_income",  "Operating Income",         ["OperatingIncomeLoss"],                                         ["USD"]),
    ("net_income",        "Net Income",               ["NetIncomeLoss"],                                               ["USD"]),
    ("income_tax",        "Income Tax",               ["IncomeTaxExpenseBenefit"],                                     ["USD"]),
    ("eps_basic",         "EPS (Basic)",              ["EarningsPerShareBasic"],                                       ["USD/shares"]),
    ("eps_diluted",       "EPS (Diluted)",            ["EarningsPerShareDiluted"],                                     ["USD/shares"]),
    # --- Balance Sheet ---
    ("total_assets",      "Total Assets",             ["Assets"],                                                      ["USD"]),
    ("current_assets",    "Current Assets",           ["AssetsCurrent"],                                               ["USD"]),
    ("cash",              "Cash & Equivalents",       ["CashAndCashEquivalentsAtCarryingValue"],                       ["USD"]),
    ("ppe_net",           "PP&E Net",                 ["PropertyPlantAndEquipmentNet"],                                ["USD"]),
    ("total_liabilities", "Total Liabilities",        ["Liabilities"],                                                 ["USD"]),
    ("current_liabilities","Current Liabilities",     ["LiabilitiesCurrent"],                                         ["USD"]),
    ("equity",            "Stockholders' Equity",     ["StockholdersEquity", "LiabilitiesAndStockholdersEquity"],     ["USD"]),
    ("retained_earnings", "Retained Earnings",        ["RetainedEarningsAccumulatedDeficit"],                         ["USD"]),
    # --- Cash Flow ---
    ("ocf",               "Operating Cash Flow",      ["NetCashProvidedByUsedInOperatingActivities"],                 ["USD"]),
    ("icf",               "Investing Cash Flow",      ["NetCashProvidedByUsedInInvestingActivities"],                 ["USD"]),
    ("fcf_fin",           "Financing Cash Flow",      ["NetCashProvidedByUsedInFinancingActivities"],                 ["USD"]),
    # --- Shares ---
    ("shares_out",        "Shares Outstanding",       ["CommonStockSharesOutstanding",
                                                       "EntityCommonStockSharesOutstanding"],                          ["shares"]),
    ("avg_shares_basic",  "Avg Shares (Basic)",       ["WeightedAverageNumberOfSharesOutstandingBasic"],              ["shares"]),
    ("avg_shares_diluted","Avg Shares (Diluted)",     ["WeightedAverageNumberOfSharesOutstandingDiluted"],            ["shares"]),
    # --- DEI ---
    ("public_float",      "Public Float",             ["EntityPublicFloat"],                                          ["USD"]),
]

# Flat set of all Tier-1 concepts (used for pyarrow filter)
TIER1_CONCEPTS = sorted({c for slot in METRIC_SLOTS for c in slot[2]})

# ---------------------------------------------------------------------------
# Value formatting
# ---------------------------------------------------------------------------


def fmt_usd(val: float) -> str:
    """Format a USD value with B/M/T suffix."""
    a = abs(val)
    if a >= 1e12:
        return f"${val / 1e12:.2f}T"
    if a >= 1e9:
        return f"${val / 1e9:.2f}B"
    if a >= 1e6:
        return f"${val / 1e6:.2f}M"
    if a >= 1e3:
        return f"${val / 1e3:.1f}K"
    return f"${val:,.0f}"


def fmt_shares(val: float) -> str:
    """Format a share count."""
    a = abs(val)
    if a >= 1e9:
        return f"{val / 1e9:.2f}B"
    if a >= 1e6:
        return f"{val / 1e6:.2f}M"
    return f"{val:,.0f}"


def fmt_per_share(val: float) -> str:
    return f"${val:.2f}"


def fmt_value(val: float, unit: str) -> str:
    if unit == "USD":
        return fmt_usd(val)
    if unit == "shares":
        return fmt_shares(val)
    if unit == "USD/shares":
        return fmt_per_share(val)
    return f"{val:,.2f}"


def fmt_pct(val: float) -> str:
    return f"{val:.1f}%"


def fmt_ratio(val: float) -> str:
    return f"{val:.2f}x"


def pct_change(new: float, old: float) -> float | None:
    """YoY percentage change. None if old is zero."""
    if old == 0:
        return None
    return (new - old) / abs(old) * 100


# ---------------------------------------------------------------------------
# EDGAR ticker fetch
# ---------------------------------------------------------------------------


def fetch_ticker_map(cache_path: Path) -> dict[str, dict]:
    """
    Return {cik_str: {"ticker": ..., "exchange": ...}} from EDGAR.

    company_tickers_exchange.json schema:
      {"fields": ["cik", "name", "ticker", "exchange"], "data": [[cik_int, name, ticker, exchange], ...]}
    """
    if cache_path.exists():
        log.info("Loading ticker map from cache: %s", cache_path)
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    log.info("Fetching ticker map from EDGAR: %s", EDGAR_TICKERS_EXCHANGE_URL)
    time.sleep(0.2)  # Respect EDGAR rate limits
    resp = requests.get(
        EDGAR_TICKERS_EXCHANGE_URL,
        headers={"User-Agent": EDGAR_USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json()

    fields = raw.get("fields", [])
    data = raw.get("data", [])

    try:
        cik_idx = fields.index("cik")
        ticker_idx = fields.index("ticker")
        exchange_idx = fields.index("exchange")
    except ValueError as e:
        raise ValueError(f"Unexpected company_tickers_exchange.json schema: {fields}") from e

    ticker_map: dict[str, dict] = {}
    for row in data:
        cik_str = str(row[cik_idx]).zfill(10)
        ticker_map[cik_str] = {
            "ticker": row[ticker_idx] or "",
            "exchange": row[exchange_idx] or "",
        }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(ticker_map, f)

    log.info("Fetched %d tickers, cached to %s", len(ticker_map), cache_path)
    return ticker_map


# ---------------------------------------------------------------------------
# Company description fetch (Wikipedia → Finnhub fallback)
# ---------------------------------------------------------------------------

WIKIPEDIA_REST_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
FINNHUB_PROFILE_URL = "https://finnhub.io/api/v1/stock/profile2"

# Minimum seconds between successive calls to each API
_WIKI_DELAY = 0.05     # Wikipedia allows up to 200 req/s; 20 req/s is conservative
_FINNHUB_DELAY = 1.05  # free tier: 60 req/min

_ENTITY_STOPWORDS = {
    "the", "and", "of", "inc", "inc.", "corp", "corp.", "corporation", "co",
    "co.", "company", "companies", "group", "holdings", "holding", "plc",
    "llc", "ltd", "limited", "international", "technologies", "technology",
    "systems", "solutions", "ventures",
}


def _normalize_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _identity_tokens(entity_name: str, ticker: str) -> set[str]:
    tokens = {
        token for token in _normalize_words(entity_name)
        if len(token) >= 3 and token not in _ENTITY_STOPWORDS
    }
    if ticker:
        tokens.add(ticker.lower())
    return tokens


def _description_matches(entity_name: str, ticker: str, title: str, description: str) -> bool:
    """
    Accept a fetched description only if it appears to refer to the target company.
    This prevents generic or unrelated Wikipedia/Finnhub pages from poisoning the index.
    """
    tokens = _identity_tokens(entity_name, ticker)
    if not tokens:
        return False

    haystack = " ".join(part for part in [title, description] if part).lower()
    matches = {token for token in tokens if token in haystack}

    # Require a stronger signal for longer company names; ticker alone is acceptable.
    if ticker and ticker.lower() in matches:
        return True
    if len(matches) >= 2:
        return True

    entity_words = _normalize_words(entity_name)
    if entity_words:
        joined = " ".join(entity_words[:3])
        if joined and joined in haystack:
            return True

    return False


class DescriptionFetcher:
    """
    Fetch and cache one-paragraph business descriptions per company.

    Lookup order:
      1. Local cache (descriptions_cache.json) — skipped if force=True
      2. Wikipedia REST summary API (no key, always tried)
      3. Finnhub /stock/profile2 (requires api_key and a known ticker)

    Cache is written after every fetch so the process is safely resumable.
    """

    def __init__(
        self,
        cache_path: Path,
        finnhub_key: str = "",
        force: bool = False,
    ) -> None:
        self._cache_path = cache_path
        self._finnhub_key = finnhub_key
        self._force = force
        self._cache: dict[str, dict] = {}

        if cache_path.exists():
            with open(cache_path, encoding="utf-8") as f:
                self._cache = json.load(f)
            log.info("Loaded %d cached descriptions from %s", len(self._cache), cache_path)

        self._session = requests.Session()
        self._session.headers["User-Agent"] = EDGAR_USER_AGENT
        self._last_wiki_call = 0.0
        self._last_finnhub_call = 0.0
        self._fetch_count = 0  # number of live (non-cache) fetches this run

    # ── public ────────────────────────────────────────────────────────────────

    def get(self, cik: str, entity_name: str, ticker: str) -> str:
        """Return a description string (may be empty if nothing found)."""
        if not self._force and cik in self._cache:
            cached = self._cache[cik].get("description", "")
            if _description_matches(entity_name, ticker, "", cached):
                return cached
            log.warning("Discarding mismatched cached description for %s (%s)", entity_name, cik)

        description = ""
        source = "none"

        # 1. Wikipedia
        description = self._try_wikipedia(entity_name, ticker)
        if description:
            source = "wikipedia"

        # 2. Finnhub (only if we have a key and a ticker and Wikipedia failed)
        if not description and ticker and self._finnhub_key:
            description = self._try_finnhub(ticker)
            if description:
                source = "finnhub"

        self._cache[cik] = {
            "source": source,
            "description": description,
            "fetched_at": date.today().isoformat(),
        }
        self._fetch_count += 1
        if self._fetch_count % 100 == 0:
            log.info("Descriptions fetched so far: %d (cache size: %d)", self._fetch_count, len(self._cache))
        self._save_cache()
        return description

    # ── Wikipedia ─────────────────────────────────────────────────────────────

    def _try_wikipedia(self, entity_name: str, ticker: str) -> str:
        """Try a couple of title strategies then fall back to search."""
        # Only try 2 direct lookups before going to search (reduce delay)
        candidates = [entity_name, f"{entity_name} (company)"]
        for title in candidates:
            extract = self._wiki_fetch_summary(entity_name, ticker, title)
            if extract:
                return extract

        # Fallback: full-text search → fetch top result
        return self._wiki_search(entity_name, ticker)

    def _wiki_fetch_summary(self, entity_name: str, ticker: str, title: str) -> str:
        """GET /page/summary/{title}. Return non-disambiguation extract or ''."""
        self._throttle_wiki()
        url = WIKIPEDIA_REST_URL.format(title=urllib.parse.quote(title, safe=""))
        try:
            resp = self._session.get(url, timeout=5)
        except requests.RequestException:
            return ""
        if resp.status_code != 200:
            return ""
        data = resp.json()
        # Reject disambiguation pages
        if data.get("type") == "disambiguation":
            return ""
        extract: str = data.get("extract", "")
        # Reject very short extracts (likely stubs or wrong page)
        page_title = data.get("title", title)
        if len(extract) <= 80:
            return ""
        return extract if _description_matches(entity_name, ticker, page_title, extract) else ""

    def _wiki_search(self, entity_name: str, ticker: str) -> str:
        """Search Wikipedia and fetch the top result's summary."""
        self._throttle_wiki()
        try:
            resp = self._session.get(
                WIKIPEDIA_SEARCH_URL,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{entity_name} company",
                    "srlimit": 3,
                    "format": "json",
                    "srnamespace": 0,
                },
                timeout=5,
            )
        except requests.RequestException:
            return ""
        if resp.status_code != 200:
            return ""
        results = resp.json().get("query", {}).get("search", [])
        for result in results:
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            if not _description_matches(entity_name, ticker, title, snippet):
                continue
            extract = self._wiki_fetch_summary(entity_name, ticker, title)
            if extract:
                return extract
        return ""

    def _throttle_wiki(self) -> None:
        elapsed = time.monotonic() - self._last_wiki_call
        if elapsed < _WIKI_DELAY:
            time.sleep(_WIKI_DELAY - elapsed)
        self._last_wiki_call = time.monotonic()

    # ── Finnhub ───────────────────────────────────────────────────────────────

    def _try_finnhub(self, ticker: str) -> str:
        """GET /stock/profile2?symbol={ticker}. Return description or ''."""
        self._throttle_finnhub()
        try:
            resp = self._session.get(
                FINNHUB_PROFILE_URL,
                params={"symbol": ticker, "token": self._finnhub_key},
                timeout=5,
            )
        except requests.RequestException:
            return ""
        if resp.status_code != 200:
            return ""
        data = resp.json()
        description = data.get("description", "") or ""
        name = data.get("name", "") or ""
        return description if _description_matches(name or ticker, ticker, name, description) else ""

    def _throttle_finnhub(self) -> None:
        elapsed = time.monotonic() - self._last_finnhub_call
        if elapsed < _FINNHUB_DELAY:
            time.sleep(_FINNHUB_DELAY - elapsed)
        self._last_finnhub_call = time.monotonic()

    # ── cache ─────────────────────────────────────────────────────────────────

    def _save_cache(self) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Annual metrics pivot
# ---------------------------------------------------------------------------


def pivot_annual_metrics(
    fy_df: pd.DataFrame,
) -> dict[int, dict[str, tuple[float, str]]]:
    """
    Build {fy: {slot_key: (value, unit)}} from a company's FY preferred facts.

    For each metric slot, tries each concept in priority order and picks the
    first one found. Where a concept can have multiple units (rare), picks
    the preferred unit from the slot definition.
    """
    if fy_df.empty:
        return {}

    # Index: (concept, unit) → {fy: value}
    # Multiple rows may exist per (concept, unit, fy) because SEC filings
    # include comparative prior-year data.  Keep the value whose end_date
    # is latest (most likely the current-year figure for that FY filing).
    lookup: dict[tuple[str, str], dict[int, float]] = {}
    _best_end: dict[tuple[str, str, int], str] = {}  # (concept, unit, fy) → end_date
    for _, row in fy_df.iterrows():
        key = (row["concept"], row["unit"])
        fy = int(row["fy"])
        end = str(row.get("end_date", "") or "")
        prev_end = _best_end.get((*key, fy), "")
        if end >= prev_end:
            lookup.setdefault(key, {})[fy] = float(row["value"])
            _best_end[(*key, fy)] = end

    all_fy = sorted({int(r) for r in fy_df["fy"].dropna().unique()})
    result: dict[int, dict[str, tuple[float, str]]] = {fy: {} for fy in all_fy}

    for slot_key, _label, concepts, preferred_units in METRIC_SLOTS:
        for concept in concepts:
            # Try each preferred unit in order
            for unit in preferred_units:
                fy_vals = lookup.get((concept, unit), {})
                if fy_vals:
                    for fy, val in fy_vals.items():
                        if slot_key not in result.get(fy, {}):
                            result.setdefault(fy, {})[slot_key] = (val, unit)
                    break  # found this concept with this unit — stop searching
            else:
                # None of the preferred units found; try any unit for this concept
                for (c, u), fy_vals in lookup.items():
                    if c == concept and fy_vals:
                        for fy, val in fy_vals.items():
                            if slot_key not in result.get(fy, {}):
                                result.setdefault(fy, {})[slot_key] = (val, u)
                        break
            # Only stop trying fallback concepts when ALL fiscal years are filled
            if all(slot_key in result.get(fy, {}) for fy in all_fy):
                break

    # Remove years that have no data at all
    return {fy: metrics for fy, metrics in result.items() if metrics}


def compute_ratios(metrics: dict[str, tuple[float, str]]) -> dict[str, str]:
    """
    Compute derived ratios from a single year's metrics.
    Returns {ratio_name: formatted_string}.
    Skips any ratio whose operands are missing.
    """
    ratios: dict[str, str] = {}

    def get(key: str) -> float | None:
        return metrics[key][0] if key in metrics else None

    revenue = get("revenue")
    net_income = get("net_income")
    gross_profit = get("gross_profit")
    operating_income = get("operating_income")
    total_assets = get("total_assets")
    total_liabilities = get("total_liabilities")
    current_assets = get("current_assets")
    current_liabilities = get("current_liabilities")
    ocf = get("ocf")

    if revenue and revenue != 0:
        if net_income is not None:
            ratios["profit_margin"] = fmt_pct(net_income / revenue * 100)
        if gross_profit is not None:
            ratios["gross_margin"] = fmt_pct(gross_profit / revenue * 100)
        if operating_income is not None:
            ratios["operating_margin"] = fmt_pct(operating_income / revenue * 100)
        if ocf is not None:
            ratios["ocf_margin"] = fmt_pct(ocf / revenue * 100)

    if total_assets and total_liabilities:
        equity_implied = total_assets - total_liabilities
        if equity_implied != 0:
            ratios["debt_to_equity"] = fmt_ratio(total_liabilities / equity_implied)
        if total_assets != 0:
            ratios["asset_turnover_proxy"] = fmt_ratio(
                (revenue or 0) / total_assets
            ) if revenue else None

    if current_assets and current_liabilities and current_liabilities != 0:
        ratios["current_ratio"] = fmt_ratio(current_assets / current_liabilities)

    # Drop None values
    return {k: v for k, v in ratios.items() if v is not None}


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------

SLOT_LABEL = {s[0]: s[1] for s in METRIC_SLOTS}


def _metric_line(metrics: dict, key: str) -> str | None:
    """Return 'Label: formatted_value' or None if missing."""
    if key not in metrics:
        return None
    val, unit = metrics[key]
    return f"{SLOT_LABEL[key]}: {fmt_value(val, unit)}"


def build_annual_snapshot(
    entity_name: str, ticker: str, cik: str, fy: int,
    metrics: dict[str, tuple[float, str]],
) -> dict:
    """
    Build one annual_snapshot document for a fiscal year.
    """
    display_name = f"{entity_name} ({ticker})" if ticker else entity_name

    parts = [f"{display_name} — FY{fy} Financial Summary"]

    # Income Statement
    income_keys = ["revenue", "gross_profit", "operating_income", "net_income", "income_tax",
                   "eps_basic", "eps_diluted"]
    income_lines = [_metric_line(metrics, k) for k in income_keys]
    income_lines = [l for l in income_lines if l]
    if income_lines:
        parts.append("Income Statement: " + " | ".join(income_lines))

    # Balance Sheet
    bs_keys = ["total_assets", "current_assets", "cash", "ppe_net",
               "total_liabilities", "current_liabilities", "equity", "retained_earnings"]
    bs_lines = [_metric_line(metrics, k) for k in bs_keys]
    bs_lines = [l for l in bs_lines if l]
    if bs_lines:
        parts.append("Balance Sheet: " + " | ".join(bs_lines))

    # Cash Flow
    cf_keys = ["ocf", "icf", "fcf_fin"]
    cf_lines = [_metric_line(metrics, k) for k in cf_keys]
    cf_lines = [l for l in cf_lines if l]
    if cf_lines:
        parts.append("Cash Flow: " + " | ".join(cf_lines))

    # Shares
    share_keys = ["shares_out", "avg_shares_basic", "avg_shares_diluted"]
    share_lines = [_metric_line(metrics, k) for k in share_keys]
    share_lines = [l for l in share_lines if l]
    if share_lines:
        parts.append("Shares: " + " | ".join(share_lines))

    # Ratios
    ratios = compute_ratios(metrics)
    if ratios:
        ratio_parts = []
        if "profit_margin"    in ratios: ratio_parts.append(f"Profit Margin: {ratios['profit_margin']}")
        if "gross_margin"     in ratios: ratio_parts.append(f"Gross Margin: {ratios['gross_margin']}")
        if "operating_margin" in ratios: ratio_parts.append(f"Operating Margin: {ratios['operating_margin']}")
        if "ocf_margin"       in ratios: ratio_parts.append(f"OCF Margin: {ratios['ocf_margin']}")
        if "current_ratio"    in ratios: ratio_parts.append(f"Current Ratio: {ratios['current_ratio']}")
        if "debt_to_equity"   in ratios: ratio_parts.append(f"Debt/Equity: {ratios['debt_to_equity']}")
        if ratio_parts:
            parts.append("Ratios: " + " | ".join(ratio_parts))

    text = "\n".join(parts)

    # Raw numeric metadata for structured filtering
    meta: dict = {"cik": cik, "entity_name": entity_name, "ticker": ticker,
                  "doc_type": "annual_snapshot", "fiscal_year": fy}
    for key, (val, unit) in metrics.items():
        meta[key] = val
    meta.update(ratios)

    return {"doc_type": "annual_snapshot", "fiscal_year": fy, "text": text, "metadata": meta}


def build_company_description(
    entity_name: str, ticker: str, cik: str,
    description: str, source: str,
) -> dict:
    """
    Build a company_description document from a Wikipedia or Finnhub excerpt.
    This gives the retriever a focused description-only chunk.
    """
    display_name = f"{entity_name} ({ticker})" if ticker else entity_name
    text = f"{display_name}\n\n{description}"
    return {
        "doc_type": "company_description",
        "text": text,
        "metadata": {
            "cik": cik,
            "entity_name": entity_name,
            "ticker": ticker,
            "doc_type": "company_description",
            "description_source": source,
        },
    }


def build_company_profile(
    entity_name: str, ticker: str, exchange: str, cik: str,
    last_filing_date: str,
    annual: dict[int, dict],         # fy → metrics
    all_fy_sorted: list[int],
    description: str = "",
) -> dict:
    """
    Build the company_profile document — the top-level prose summary.
    Covers: identity, most recent FY key metrics, YoY growth, 5-year revenue trend.
    """
    display_name = f"{entity_name} ({ticker})" if ticker else entity_name
    exchange_str = f", {exchange}" if exchange else ""
    recent_fy = all_fy_sorted[-1] if all_fy_sorted else None
    prev_fy = all_fy_sorted[-2] if len(all_fy_sorted) >= 2 else None

    header = f"{display_name}{exchange_str} — CIK {cik}"
    lines = [header]

    # Business description (from Wikipedia or Finnhub)
    if description:
        # Keep first 2 sentences for the profile (full text is in company_description doc)
        sentences = description.split(". ")
        short_desc = ". ".join(sentences[:2]).strip()
        if short_desc and not short_desc.endswith("."):
            short_desc += "."
        lines.append(short_desc)

    if recent_fy:
        lines.append(f"Most recent data: FY{recent_fy} (last filing: {last_filing_date})")
        m = annual.get(recent_fy, {})
        mp = annual.get(prev_fy, {}) if prev_fy else {}

        # Revenue + growth
        if "revenue" in m:
            val, unit = m["revenue"]
            rev_str = fmt_usd(val)
            if prev_fy and "revenue" in mp:
                delta = pct_change(val, mp["revenue"][0])
                sign = "+" if delta and delta >= 0 else ""
                yoy = f" ({sign}{delta:.1f}% vs FY{prev_fy})" if delta is not None else ""
            else:
                yoy = ""
            lines.append(f"Revenue: {rev_str}{yoy}")

        # Net income + margin + growth
        if "net_income" in m:
            val, unit = m["net_income"]
            ni_str = fmt_usd(val)
            ratios = compute_ratios(m)
            margin_str = f" | Profit Margin: {ratios['profit_margin']}" if "profit_margin" in ratios else ""
            if prev_fy and "net_income" in mp:
                delta = pct_change(val, mp["net_income"][0])
                sign = "+" if delta and delta >= 0 else ""
                yoy = f" ({sign}{delta:.1f}% vs FY{prev_fy})" if delta is not None else ""
            else:
                yoy = ""
            lines.append(f"Net Income: {ni_str}{yoy}{margin_str}")

        # Key balance sheet
        for key in ["total_assets", "total_liabilities", "equity", "cash"]:
            if key in m:
                val, unit = m[key]
                lines.append(f"{SLOT_LABEL[key]}: {fmt_usd(val)}")

        # Cash flow
        if "ocf" in m:
            val, unit = m["ocf"]
            ratios = compute_ratios(m)
            ocf_margin = f" | OCF Margin: {ratios['ocf_margin']}" if "ocf_margin" in ratios else ""
            lines.append(f"Operating Cash Flow: {fmt_usd(val)}{ocf_margin}")

        # EPS
        for key in ["eps_basic", "eps_diluted"]:
            if key in m:
                val, unit = m[key]
                lines.append(f"{SLOT_LABEL[key]}: {fmt_per_share(val)}")

        # Ratios block
        ratios = compute_ratios(m)
        ratio_parts = []
        for rk in ["gross_margin", "operating_margin", "current_ratio", "debt_to_equity"]:
            if rk in ratios:
                label = rk.replace("_", " ").title()
                ratio_parts.append(f"{label}: {ratios[rk]}")
        if ratio_parts:
            lines.append("Ratios: " + " | ".join(ratio_parts))

    # 5-year revenue trend (last 5 available FYs)
    trend_fys = all_fy_sorted[-5:]
    rev_trend = [(fy, annual[fy]["revenue"][0]) for fy in trend_fys if "revenue" in annual.get(fy, {})]
    if len(rev_trend) >= 2:
        trend_str = " → ".join(f"{fmt_usd(v)} ({fy})" for fy, v in rev_trend)
        lines.append(f"Revenue trend ({rev_trend[0][1]}–{rev_trend[-1][1]}): {trend_str}")

    text = "\n".join(lines)

    meta = {
        "cik": cik, "entity_name": entity_name, "ticker": ticker,
        "exchange": exchange, "doc_type": "company_profile",
        "most_recent_fy": recent_fy, "last_filing_date": last_filing_date,
    }
    if recent_fy and recent_fy in annual:
        for key, (val, _) in annual[recent_fy].items():
            meta[key] = val

    return {"doc_type": "company_profile", "text": text, "metadata": meta}


def build_fact_sentences(
    entity_name: str, ticker: str, cik: str,
    all_tier1_df: pd.DataFrame,
    concepts_map: dict[tuple[str, str], str],
) -> list[dict]:
    """
    Build one sentence per preferred Tier-1 datapoint (all periods, not just FY).
    These are the finest-grained documents — best for precise lookups.
    """
    docs = []
    display_name = f"{entity_name} ({ticker})" if ticker else entity_name

    for _, row in all_tier1_df.iterrows():
        if not row["is_preferred"]:
            continue

        label = concepts_map.get((row["taxonomy"], row["concept"]), row["concept"])
        val = float(row["value"])
        unit = str(row["unit"])
        val_str = fmt_value(val, unit)

        period_type = str(row.get("period_type", ""))
        start_date = str(row.get("start_date", "") or "")
        end_date = str(row["end_date"])
        fy = row.get("fy")
        fp = str(row.get("fp", "") or "")
        form = str(row.get("form", ""))
        filed = str(row.get("filed_date", ""))
        accn = str(row.get("accession_number", ""))

        if period_type == "duration" and start_date:
            period = f"for the period {start_date} to {end_date}"
        else:
            period = f"as of {end_date}"

        fy_str = f" (FY{fy} {fp})" if fy and fp else (f" (FY{fy})" if fy else "")

        sentence = (
            f"{display_name} reported {label} = {val_str} "
            f"{period}{fy_str}. "
            f"Source: Form {form}, filed {filed}, accession {accn}."
        )

        docs.append({
            "doc_type": "fact_sentence",
            "text": sentence,
            "metadata": {
                "cik": cik,
                "entity_name": entity_name,
                "ticker": ticker,
                "doc_type": "fact_sentence",
                "taxonomy": row["taxonomy"],
                "concept": row["concept"],
                "unit": unit,
                "value": val,
                "end_date": end_date,
                "start_date": start_date,
                "period_type": period_type,
                "period_key": str(row.get("period_key", "")),
                "fy": int(fy) if fy and pd.notna(fy) else None,
                "fp": fp,
                "form": form,
                "filed_date": filed,
                "accession_number": accn,
            },
        })

    return docs


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(
    facts_path: Path,
    entity_path: Path,
    concepts_path: Path,
    ticker_cache: Path,
    output_dir: Path,
    force: bool = False,
    max_years: int = 5,
    description_cache: Path | None = None,
    finnhub_key: str = "",
    force_descriptions: bool = False,
    ciks: list[str] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cik_filter = {str(cik).zfill(10) for cik in (ciks or [])}

    # 1a. Set up description fetcher
    if description_cache is None:
        description_cache = output_dir.parent / "descriptions_cache.json"
    fetcher = DescriptionFetcher(
        cache_path=description_cache,
        finnhub_key=finnhub_key,
        force=force_descriptions,
    )

    # 1b. Fetch ticker map
    ticker_map = fetch_ticker_map(ticker_cache)

    # 2. Load entity master
    log.info("Loading entity master...")
    entity_df = pq.read_table(entity_path).to_pandas()
    entity_dict = {
        row["cik"]: row
        for _, row in entity_df.iterrows()
    }
    if cik_filter:
        entity_dict = {
            cik: row
            for cik, row in entity_dict.items()
            if str(cik).zfill(10) in cik_filter
        }
        log.info("Filtered to %d requested companies", len(entity_dict))

    # 3. Load concepts dimension (tiny — label lookup)
    log.info("Loading concepts table...")
    concepts_df = pq.read_table(concepts_path).to_pandas()
    concepts_map: dict[tuple[str, str], str] = {
        (row["taxonomy"], row["concept"]): row["label"]
        for _, row in concepts_df.iterrows()
    }

    # 4. Load ONLY preferred Tier-1 facts via pyarrow filter (avoids loading 500MB+)
    log.info("Loading preferred Tier-1 facts (filtered)...")
    tier1_table = pq.read_table(
        facts_path,
        filters=[
            ("is_preferred", "=", True),
            ("concept", "in", TIER1_CONCEPTS),
        ],
    )
    tier1_df = tier1_table.to_pandas()
    log.info("Loaded %d preferred Tier-1 fact rows", len(tier1_df))

    # 5. Split into FY (for profile/snapshots) and all (for sentences)
    #    Pre-group by CIK once — avoids O(n²) per-company filtering in the loop.
    log.info("Pre-grouping facts by company...")
    fy_df = tier1_df[tier1_df["fp"] == "FY"].copy()
    fy_groups: dict[str, pd.DataFrame] = {
        cik: grp for cik, grp in fy_df.groupby("cik", sort=False)
    }
    all_groups: dict[str, pd.DataFrame] = {
        cik: grp for cik, grp in tier1_df.groupby("cik", sort=False)
    }
    empty_df = pd.DataFrame(columns=tier1_df.columns)
    log.info("Grouping done. Processing %d companies...", len(entity_dict))

    # 6. Process each company
    companies_index: list[dict] = []
    total = len(entity_dict)
    t0 = time.monotonic()

    for i, (cik, entity) in enumerate(entity_dict.items(), 1):
        if i == 1 or i % 250 == 0 or i == total:
            elapsed = time.monotonic() - t0
            rate = i / elapsed if elapsed > 0 else 0
            log.info("Progress: %d/%d companies (%.1f/s)", i, total, rate)

        out_path = output_dir / f"{cik}.json"
        if not force and out_path.exists():
            companies_index.append({"cik": cik, "path": str(out_path)})
            continue

        entity_name = entity["entity_name"]
        ticker_info = ticker_map.get(cik, {})
        ticker = ticker_info.get("ticker", "")
        exchange = ticker_info.get("exchange", "")
        last_filing = entity.get("last_seen_filing_date", "")
        is_partial = bool(entity.get("partial", False))

        # O(1) CIK lookup via pre-built groups
        company_fy = fy_groups.get(cik, empty_df)
        company_all = all_groups.get(cik, empty_df)

        # Build annual metrics pivot
        annual = pivot_annual_metrics(company_fy)

        # Limit to last max_years fiscal years
        all_fy_sorted = sorted(annual.keys())
        recent_fys = all_fy_sorted[-max_years:]
        annual_recent = {fy: annual[fy] for fy in recent_fys}

        # Fetch business description (Wikipedia → Finnhub fallback, cached)
        description = fetcher.get(cik, entity_name, ticker)
        desc_source = fetcher._cache.get(cik, {}).get("source", "none")

        # Build documents
        docs: list[dict] = []

        # Company profile (always first)
        docs.append(build_company_profile(
            entity_name, ticker, exchange, cik,
            last_filing, annual_recent, recent_fys,
            description=description,
        ))

        # Standalone description document (for focused retrieval)
        if description:
            docs.append(build_company_description(
                entity_name, ticker, cik, description, desc_source,
            ))

        # Annual snapshots (last max_years, newest first)
        for fy in reversed(recent_fys):
            docs.append(build_annual_snapshot(
                entity_name, ticker, cik, fy, annual_recent[fy]
            ))

        # Fact sentences (all periods, Tier-1 preferred)
        docs.extend(build_fact_sentences(
            entity_name, ticker, cik, company_all, concepts_map
        ))

        # Write output
        output = {
            "cik": cik,
            "entity_name": entity_name,
            "ticker": ticker,
            "exchange": exchange,
            "last_filing_date": last_filing,
            "snapshot_date": date.today().isoformat(),
            "partial_data": is_partial,
            "fiscal_years_covered": recent_fys,
            "document_count": len(docs),
            "documents": docs,
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

        companies_index.append({
            "cik": cik,
            "entity_name": entity_name,
            "ticker": ticker,
            "exchange": exchange,
            "fiscal_years": recent_fys,
            "document_count": len(docs),
            "path": str(out_path),
        })

    # Write master index
    index_path = output_dir.parent / "companies_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated": date.today().isoformat(),
            "total_companies": len(companies_index),
            "companies": companies_index,
        }, f, ensure_ascii=False, indent=2)

    elapsed = time.monotonic() - t0
    log.info("=" * 60)
    log.info("DONE in %.1fs — %d company files written to %s", elapsed, len(companies_index), output_dir)
    log.info("Master index: %s", index_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate per-company embedding JSON files.",
        epilog="See DATA_PIPELINE_README.md for document format details.",
    )

    script_dir = Path(__file__).resolve().parent  # stockrag/data/
    sec_dir = script_dir / "processed" / "sec"
    rag_dir = script_dir / "rag"

    parser.add_argument("--facts",    type=Path, default=sec_dir / "facts.parquet")
    parser.add_argument("--entities", type=Path, default=sec_dir / "entity_master.parquet")
    parser.add_argument("--concepts", type=Path, default=sec_dir / "concepts.parquet")
    parser.add_argument("--ticker-cache", type=Path, default=rag_dir / "company_tickers_exchange.json",
                        help="Cache path for EDGAR ticker map")
    parser.add_argument("--output-dir", type=Path, default=rag_dir / "companies",
                        help="Output directory for per-company JSON files")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate even if output already exists")
    parser.add_argument("--cik", action="append", default=[],
                        help="Only process the specified CIK. Repeat for multiple companies.")
    parser.add_argument("--max-years", type=int, default=5,
                        help="Number of most recent fiscal years to include (default: 5)")
    parser.add_argument("--finnhub-key", type=str,
                        default=os.environ.get("FINNHUB_API_KEY", ""),
                        help="Finnhub API key (fallback when Wikipedia has no entry). "
                             "Also reads FINNHUB_API_KEY env var.")
    parser.add_argument("--description-cache", type=Path,
                        default=rag_dir / "descriptions_cache.json",
                        help="Path to cache file for fetched descriptions")
    parser.add_argument("--force-descriptions", action="store_true",
                        help="Re-fetch descriptions even if already cached")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    for p in [args.facts, args.entities, args.concepts]:
        if not p.exists():
            log.error("Required file not found: %s", p)
            raise SystemExit(1)

    run(
        facts_path=args.facts,
        entity_path=args.entities,
        concepts_path=args.concepts,
        ticker_cache=args.ticker_cache,
        output_dir=args.output_dir,
        force=args.force,
        max_years=args.max_years,
        description_cache=args.description_cache,
        finnhub_key=args.finnhub_key,
        force_descriptions=args.force_descriptions,
        ciks=args.cik,
    )


if __name__ == "__main__":
    main()
