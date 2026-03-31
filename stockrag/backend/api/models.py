#new models.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class RecommendationRequest(BaseModel):
    """
    Request model matching frontend types
    Frontend: RecommendationRequest in src/api/types.ts
    """
    query: str = Field(
        ..., 
        description="Natural language query for stock recommendations",
        example="EV car companies"
    )
    topK: Optional[int] = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of recommendations to return (default: 5)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "EV car companies",
                "topK": 5
            }
        }


class StockRecommendation(BaseModel):
    """
    Individual stock recommendation matching frontend types
    Frontend: StockRecommendation in src/api/types.ts
    """
    # Identity
    ticker: str = Field(..., description="Stock ticker symbol", example="TSLA")
    name: str = Field(..., description="Company name", example="Tesla, Inc.")
    
    # The Core Feature (RAG)
    whyFits: str = Field(
        ...,
        description="LLM-generated explanation for why this stock matches the query",
        example="Tesla is the market leader in EV..."
    )
    
    # Context (Minimum viable stats)
    currentPrice: float = Field(..., description="Current stock price", example=245.67)
    sector: str = Field(..., description="Stock sector for color-coding", example="Consumer Cyclical")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "TSLA",
                "name": "Tesla, Inc.",
                "whyFits": "Tesla is the market leader in EV with strong growth potential",
                "currentPrice": 245.67,
                "sector": "Consumer Cyclical"
            }
        }


class RecommendationResponse(BaseModel):
    """
    Response model matching frontend types
    Frontend: RecommendationResponse in src/api/types.ts
    """
    recommendations: List[StockRecommendation] = Field(
        ...,
        description="List of stock recommendations"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "recommendations": [
                    {
                        "ticker": "TSLA",
                        "name": "Tesla, Inc.",
                        "whyFits": "Tesla is the market leader in EV technology",
                        "currentPrice": 245.67,
                        "sector": "Consumer Cyclical"
                    },
                    {
                        "ticker": "RIVN",
                        "name": "Rivian Automotive, Inc.",
                        "whyFits": "Rivian is an emerging EV manufacturer focusing on trucks and SUVs",
                        "currentPrice": 18.92,
                        "sector": "Consumer Cyclical"
                    }
                ]
            }
        }


# Health check and stats models (for backend endpoints)
class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Timestamp of health check")
    services: Dict[str, Dict[str, str]] = Field(..., description="Status of individual services")


class StatsResponse(BaseModel):
    """Stats response model"""
    total_stocks: int = Field(..., description="Total number of stocks in database")
    last_update: Optional[str] = Field(None, description="Last update timestamp")
    database_name: str = Field(..., description="Name of the database collection")
    timestamp: str = Field(..., description="Current timestamp")