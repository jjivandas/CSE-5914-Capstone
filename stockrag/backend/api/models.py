from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language stock query")
    topK: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of companies to surface",
    )


class StockRecommendation(BaseModel):
    cik: str = Field(..., description="SEC company identifier")
    companyName: str = Field(..., description="Legal entity name")
    ticker: str = Field(..., description="Ticker symbol when available")
    exchange: Optional[str] = Field(default=None, description="Listing exchange")
    sector: Optional[str] = Field(default=None, description="Sector if known")
    whyFits: Optional[str] = Field(
        default=None,
        description="Optional per-company rationale when available",
    )
    sourceDocTypes: List[str] = Field(
        default_factory=list,
        description="Types of retrieved documents used for this company",
    )
    # Financial metrics from most recent filing
    revenue: Optional[float] = Field(default=None, description="Total revenue in USD")
    netIncome: Optional[float] = Field(default=None, description="Net income in USD")
    profitMargin: Optional[str] = Field(default=None, description="Profit margin percentage")
    grossMargin: Optional[str] = Field(default=None, description="Gross margin percentage")
    epsD: Optional[float] = Field(default=None, description="Diluted EPS")
    totalAssets: Optional[float] = Field(default=None, description="Total assets in USD")
    cash: Optional[float] = Field(default=None, description="Cash and equivalents in USD")
    equity: Optional[float] = Field(default=None, description="Stockholders equity in USD")
    ocfMargin: Optional[str] = Field(default=None, description="Operating cash flow margin")
    currentRatio: Optional[str] = Field(default=None, description="Current ratio")
    grossProfit: Optional[float] = Field(default=None, description="Gross profit in USD")
    operatingIncome: Optional[float] = Field(default=None, description="Operating income in USD")
    totalLiabilities: Optional[float] = Field(default=None, description="Total liabilities in USD")
    ocf: Optional[float] = Field(default=None, description="Operating cash flow in USD")
    fiscalYear: Optional[int] = Field(default=None, description="Most recent fiscal year")
    # Live price / external link
    currentPrice: Optional[float] = Field(default=None, description="Live stock price from Finnhub")
    edgarUrl: Optional[str] = Field(default=None, description="SEC EDGAR filings page")


class RecommendationResponse(BaseModel):
    message: str = Field(..., description="Assistant response grounded in retrieved data")
    recommendations: List[StockRecommendation] = Field(
        default_factory=list,
        description="Retrieved companies included in the response",
    )


class ServiceStatus(BaseModel):
    status: str
    message: str


class HealthCheckResponse(BaseModel):
    status: str
    services: dict[str, ServiceStatus]


class StatsResponse(BaseModel):
    total_stocks: int
    profiles_indexed: int
    snapshots_indexed: int
    descriptions_indexed: int
    database_name: str
