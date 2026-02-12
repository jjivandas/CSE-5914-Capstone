#routes.py
"""
API routes for Stock Recommendation system
Location: backend/api/routes.py
Updated to match frontend types
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any
import logging

from .models import (
    RecommendationRequest, 
    RecommendationResponse,
    StockRecommendation,
    HealthCheckResponse,
    StatsResponse
)
from services.vector_db import vector_db_service
from services.llm_service import llm_service

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint to verify connectivity to ChromaDB and LLM
    
    Returns:
        HealthCheckResponse with status of each service
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check ChromaDB connection
    try:
        vector_db_status = vector_db_service.check_health()
        health_status["services"]["vector_db"] = {
            "status": "healthy" if vector_db_status else "unhealthy",
            "message": "Connected to Vector DB" if vector_db_status else "Failed to connect"
        }
    except Exception as e:
        logger.error(f"Vector DB health check failed: {e}")
        health_status["services"]["vector_db"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check LLM service connection
    try:
        llm_status = llm_service.check_health()
        health_status["services"]["llm"] = {
            "status": "healthy" if llm_status else "unhealthy",
            "message": "LLM service available" if llm_status else "LLM service unavailable"
        }
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        health_status["services"]["llm"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Overall status
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get statistics about the stock database
    
    Returns:
        StatsResponse with total stocks count and last update timestamp
    """
    try:
        stats = vector_db_service.get_stats()
        
        return StatsResponse(
            total_stocks=stats.get("total_stocks", 0),
            last_update=stats.get("last_update"),
            database_name=stats.get("database_name", "stock_recommendations"),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Get stock recommendations based on query using RAG
    Returns format matching frontend RecommendationResponse
    
    Args:
        request: RecommendationRequest with query and optional topK
    
    Returns:
        RecommendationResponse with list of stock recommendations
    """
    try:
        logger.info(f"Received recommendation request: {request.query}, topK: {request.topK}")
        
        # Import RAG pipeline
        from rag.pipeline import rag_pipeline
        
        # Get recommendations using RAG pipeline
        recommendations = await rag_pipeline.get_recommendations(
            query=request.query,
            top_k=request.topK or 5
        )
        
        # Convert to frontend format
        frontend_recommendations = []
        for rec in recommendations:
            stock_rec = StockRecommendation(
                ticker=rec["ticker"],
                name=rec["name"],
                whyFits=rec["whyFits"],
                currentPrice=rec["currentPrice"],
                sector=rec["sector"]
            )
            frontend_recommendations.append(stock_rec)
        
        return RecommendationResponse(
            recommendations=frontend_recommendations
        )
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}"
        )