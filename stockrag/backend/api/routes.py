from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.models import (
    HealthCheckResponse,
    RecommendationRequest,
    RecommendationResponse,
    ServiceStatus,
    StatsResponse,
    StockRecommendation,
)
from config import (
    DESCRIPTIONS_COLLECTION,
    FINNHUB_API_KEY,
    GOOGLE_API_KEY,
    PROFILES_COLLECTION,
    SNAPSHOTS_COLLECTION,
)
from rag import pipeline, vector_db
from utils.finnhub import fetch_prices

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_why_fits(snippet: str) -> str | None:
    """Extract first 1-2 body sentences from a profile text snippet."""
    if not snippet:
        return None
    sentences = snippet.split(". ")
    # Skip the header line (company name / ticker / CIK)
    body = [s.strip() for s in sentences[1:3] if s.strip()]
    if not body:
        return None
    why = ". ".join(body)
    if not why.endswith("."):
        why += "."
    return why


def _safe_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


_EDGAR_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcompany&CIK={cik}&type=10-K&dateb=&owner=include&count=40"
)


def _build_edgar_url(cik: str) -> str:
    return _EDGAR_URL.format(cik=cik)


def _map_sources_to_recommendations(docs: list[vector_db.SearchResult]) -> list[StockRecommendation]:
    recommendations: list[StockRecommendation] = []
    for source in pipeline.get_sources(docs):
        fin = source.get("financials", {})

        # fiscal_year with fallback to most_recent_fy
        fiscal_year = _safe_int(fin.get("fiscal_year")) or _safe_int(fin.get("most_recent_fy"))

        rec = StockRecommendation(
            cik=source["cik"],
            companyName=source["entity_name"],
            ticker=source["ticker"],
            exchange=source["exchange"] or None,
            sourceDocTypes=source["doc_types"],
            whyFits=_extract_why_fits(source.get("text_snippet", "")),
            revenue=_safe_float(fin.get("revenue")),
            netIncome=_safe_float(fin.get("net_income")),
            profitMargin=fin.get("profit_margin") if isinstance(fin.get("profit_margin"), str) else None,
            grossMargin=fin.get("gross_margin") if isinstance(fin.get("gross_margin"), str) else None,
            epsD=_safe_float(fin.get("eps_diluted")),
            totalAssets=_safe_float(fin.get("total_assets")),
            cash=_safe_float(fin.get("cash")),
            equity=_safe_float(fin.get("equity")),
            ocfMargin=fin.get("ocf_margin") if isinstance(fin.get("ocf_margin"), str) else None,
            currentRatio=fin.get("current_ratio") if isinstance(fin.get("current_ratio"), str) else None,
            grossProfit=_safe_float(fin.get("gross_profit")),
            operatingIncome=_safe_float(fin.get("operating_income")),
            totalLiabilities=_safe_float(fin.get("total_liabilities")),
            ocf=_safe_float(fin.get("ocf")),
            fiscalYear=fiscal_year,
        )

        # Compute derived margin fields from raw data when missing
        revenue = _safe_float(fin.get("revenue"))
        net_income = _safe_float(fin.get("net_income"))
        gross_profit = _safe_float(fin.get("gross_profit"))
        ocf_val = _safe_float(fin.get("ocf"))

        if revenue and revenue > 0:
            if not rec.profitMargin and net_income is not None:
                rec.profitMargin = f"{net_income / revenue * 100:.1f}%"
            if not rec.grossMargin and gross_profit is not None:
                rec.grossMargin = f"{gross_profit / revenue * 100:.1f}%"
            if not rec.ocfMargin and ocf_val is not None:
                rec.ocfMargin = f"{ocf_val / revenue * 100:.1f}%"

        if not rec.currentRatio:
            current_assets = _safe_float(fin.get("current_assets"))
            current_liabs = _safe_float(fin.get("current_liabilities"))
            if current_assets and current_liabs and current_liabs > 0:
                rec.currentRatio = f"{current_assets / current_liabs:.2f}x"

        recommendations.append(rec)
    return recommendations


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    profile_count = vector_db.collection_count(PROFILES_COLLECTION)
    snapshot_count = vector_db.collection_count(SNAPSHOTS_COLLECTION)
    description_count = vector_db.collection_count(DESCRIPTIONS_COLLECTION)

    vector_ready = profile_count > 0 or snapshot_count > 0 or description_count > 0
    llm_ready = bool(GOOGLE_API_KEY and GOOGLE_API_KEY != "your_key_here")

    services = {
        "vector_db": ServiceStatus(
            status="healthy" if vector_ready else "unhealthy",
            message=(
                f"Indexed documents found: profiles={profile_count}, "
                f"snapshots={snapshot_count}, descriptions={description_count}"
            ),
        ),
        "llm": ServiceStatus(
            status="healthy" if llm_ready else "unhealthy",
            message="Gemini API key configured" if llm_ready else "Gemini API key missing",
        ),
    }

    overall_status = (
        "healthy"
        if services["vector_db"].status == "healthy" and services["llm"].status == "healthy"
        else "unhealthy"
    )
    return HealthCheckResponse(status=overall_status, services=services)


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    return StatsResponse(
        total_stocks=vector_db.collection_count(PROFILES_COLLECTION),
        profiles_indexed=vector_db.collection_count(PROFILES_COLLECTION),
        snapshots_indexed=vector_db.collection_count(SNAPSHOTS_COLLECTION),
        descriptions_indexed=vector_db.collection_count(DESCRIPTIONS_COLLECTION),
        database_name="chroma_db",
    )


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    try:
        message, docs = pipeline.run(
            query=request.query,
            top_k=request.topK or 5,
            conversation_history=request.conversationHistory,
        )
        recs = _map_sources_to_recommendations(docs)

        # Fetch live prices from Finnhub (parallel, non-blocking)
        tickers_by_cik = {r.cik: r.ticker for r in recs if r.ticker}
        prices = await fetch_prices(tickers_by_cik, FINNHUB_API_KEY)

        for rec in recs:
            price = prices.get(rec.cik)
            if price is not None:
                rec.currentPrice = price
            else:
                rec.edgarUrl = _build_edgar_url(rec.cik)

        return RecommendationResponse(message=message, recommendations=recs)
    except Exception as exc:
        logger.exception("Failed to generate recommendations")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {exc}",
        ) from exc
