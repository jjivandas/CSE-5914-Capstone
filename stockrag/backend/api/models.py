#models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime




class RecommendationRequest(BaseModel):
   """Request model for stock recommendations"""
   query: str = Field(
       ...,
       description="Natural language query for stock recommendations",
       example="Find tech stocks with strong growth potential"
   )
   max_results: int = Field(
       default=10,
       ge=1,
       le=50,
       description="Maximum number of stock recommendations to return"
   )
   filters: Optional[Dict[str, Any]] = Field(
       default=None,
       description="Optional filters for stock recommendations",
       example={
           "sectors": ["Technology", "Healthcare"],
           "market_cap_min": 1000000000,
           "market_cap_max": 500000000000,
           "pe_ratio_max": 30,
           "dividend_yield_min": 0.02
       }
   )


   class Config:
       json_schema_extra = {
           "example": {
               "query": "Find undervalued dividend stocks in the energy sector",
               "max_results": 5,
               "filters": {
                   "sectors": ["Energy"],
                   "dividend_yield_min": 0.03,
                   "pe_ratio_max": 15
               }
           }
       }




class StockMetrics(BaseModel):
   """Financial metrics for a stock"""
   market_cap: Optional[float] = Field(None, description="Market capitalization in USD")
   pe_ratio: Optional[float] = Field(None, description="Price-to-Earnings ratio")
   dividend_yield: Optional[float] = Field(None, description="Dividend yield as decimal (e.g., 0.03 for 3%)")
   price_change_1d: Optional[float] = Field(None, description="1-day price change percentage")
   price_change_1m: Optional[float] = Field(None, description="1-month price change percentage")
   price_change_1y: Optional[float] = Field(None, description="1-year price change percentage")
   volume: Optional[int] = Field(None, description="Trading volume")
   sector: Optional[str] = Field(None, description="Stock sector")
   industry: Optional[str] = Field(None, description="Stock industry")
  
   class Config:
       json_schema_extra = {
           "example": {
               "market_cap": 2500000000000,
               "pe_ratio": 28.5,
               "dividend_yield": 0.015,
               "price_change_1d": 1.2,
               "price_change_1m": -3.5,
               "price_change_1y": 45.8,
               "volume": 85000000,
               "sector": "Technology",
               "industry": "Software"
           }
       }




class StockRecommendation(BaseModel):
   """Individual stock recommendation"""
   ticker: str = Field(..., description="Stock ticker symbol", example="AAPL")
   company_name: Optional[str] = Field(None, description="Company name", example="Apple Inc.")
   match_score: float = Field(
       ...,
       ge=0.0,
       le=1.0,
       description="Relevance score from RAG retrieval (0-1)",
       example=0.92
   )
   explanation: str = Field(
       ...,
       description="AI-generated explanation for why this stock matches the query",
       example="Apple shows strong growth potential with consistent revenue increases and innovation in AI technologies."
   )
   metrics: StockMetrics = Field(..., description="Financial metrics for the stock")
  
   class Config:
       json_schema_extra = {
           "example": {
               "ticker": "MSFT",
               "company_name": "Microsoft Corporation",
               "match_score": 0.89,
               "explanation": "Microsoft demonstrates strong fundamentals with cloud revenue growth and AI integration across products.",
               "metrics": {
                   "market_cap": 3000000000000,
                   "pe_ratio": 32.1,
                   "dividend_yield": 0.008,
                   "sector": "Technology"
               }
           }
       }




class RecommendationResponse(BaseModel):
   """Response model containing stock recommendations"""
   recommendations: List[StockRecommendation] = Field(
       ...,
       description="List of stock recommendations sorted by match score"
   )
   query: str = Field(..., description="Original query from the request")
   total_results: int = Field(..., description="Total number of recommendations returned")
   timestamp: datetime = Field(
       default_factory=datetime.now,
       description="Timestamp when recommendations were generated"
   )
  
   class Config:
       json_schema_extra = {
           "example": {
               "recommendations": [
                   {
                       "ticker": "NVDA",
                       "company_name": "NVIDIA Corporation",
                       "match_score": 0.95,
                       "explanation": "NVIDIA leads in AI chips with strong demand and revenue growth.",
                       "metrics": {
                           "market_cap": 1800000000000,
                           "pe_ratio": 65.3,
                           "sector": "Technology"
                       }
                   }
               ],
               "query": "Find AI and semiconductor stocks",
               "total_results": 1,
               "timestamp": "2024-02-05T10:30:00"
           }
       }