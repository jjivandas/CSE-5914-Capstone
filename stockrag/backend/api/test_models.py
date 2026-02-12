#test_models.py
from models import RecommendationRequest, RecommendationResponse, StockRecommendation, StockMetrics
from datetime import datetime




# Example 1: Creating a request
def example_request():
   """Example of creating a recommendation request"""
  
   # Simple request with just query
   simple_request = RecommendationRequest(
       query="Find growth stocks in technology",
       max_results=5
   )
  
   # Request with filters
   filtered_request = RecommendationRequest(
       query="Find undervalued dividend stocks",
       max_results=10,
       filters={
           "sectors": ["Energy", "Utilities"],
           "dividend_yield_min": 0.03,
           "pe_ratio_max": 15,
           "market_cap_min": 10000000000
       }
   )
  
   print("Simple Request:")
   print(simple_request.model_dump_json(indent=2))
   print("\nFiltered Request:")
   print(filtered_request.model_dump_json(indent=2))
  
   return filtered_request




# Example 2: Creating a response
def example_response(request: RecommendationRequest):
   """Example of creating a recommendation response"""
  
   # Create sample stock recommendations
   recommendations = [
       StockRecommendation(
           ticker="XOM",
           company_name="Exxon Mobil Corporation",
           match_score=0.92,
           explanation="Exxon Mobil offers a strong dividend yield of 3.5% with a reasonable P/E ratio of 12.4. The company has consistent cash flow from oil and gas operations.",
           metrics=StockMetrics(
               market_cap=450000000000,
               pe_ratio=12.4,
               dividend_yield=0.035,
               price_change_1d=0.5,
               price_change_1m=2.3,
               price_change_1y=15.7,
               volume=25000000,
               sector="Energy",
               industry="Oil & Gas"
           )
       ),
       StockRecommendation(
           ticker="CVX",
           company_name="Chevron Corporation",
           match_score=0.88,
           explanation="Chevron provides reliable dividends with a 3.2% yield and trades at a P/E of 13.1. Strong balance sheet and proven reserves support long-term stability.",
           metrics=StockMetrics(
               market_cap=280000000000,
               pe_ratio=13.1,
               dividend_yield=0.032,
               price_change_1d=-0.2,
               price_change_1m=1.8,
               price_change_1y=12.3,
               volume=18000000,
               sector="Energy",
               industry="Oil & Gas"
           )
       )
   ]
  
   # Create response
   response = RecommendationResponse(
       recommendations=recommendations,
       query=request.query,
       total_results=len(recommendations),
       timestamp=datetime.now()
   )
  
   print("\nResponse:")
   print(response.model_dump_json(indent=2))
  
   return response




# Example 3: Validating incoming data
def validate_request_data():
   """Example of validating request data with Pydantic"""
  
   # Valid data
   valid_data = {
       "query": "Find tech stocks",
       "max_results": 5
   }
  
   try:
       request = RecommendationRequest(**valid_data)
       print("✓ Valid request created")
   except Exception as e:
       print(f"✗ Validation error: {e}")
  
   # Invalid data (max_results too high)
   invalid_data = {
       "query": "Find stocks",
       "max_results": 100  # exceeds limit of 50
   }
  
   try:
       request = RecommendationRequest(**invalid_data)
       print("✓ Request created")
   except Exception as e:
       print(f"✗ Validation error: {e}")




# Example 4: Using in FastAPI
def fastapi_example():
   """
   Example of how to use these models in FastAPI endpoints
  
   from fastapi import FastAPI
   from models import RecommendationRequest, RecommendationResponse
  
   app = FastAPI()
  
   @app.post("/recommendations", response_model=RecommendationResponse)
   async def get_recommendations(request: RecommendationRequest):
       # Your RAG logic here
       # 1. Process the query
       # 2. Retrieve relevant stock data from vector database
       # 3. Generate explanations
       # 4. Apply filters
       # 5. Build response
      
       recommendations = []  # Your RAG results
      
       return RecommendationResponse(
           recommendations=recommendations,
           query=request.query,
           total_results=len(recommendations)
       )
   """
   print("\nFastAPI Usage Example:")
   print(fastapi_example.__doc__)




if __name__ == "__main__":
   print("=== Pydantic Models Examples ===\n")
  
   # Run examples
   request = example_request()
   print("\n" + "="*50 + "\n")
  
   response = example_response(request)
   print("\n" + "="*50 + "\n")
  
   validate_request_data()
   print("\n" + "="*50 + "\n")
  
   fastapi_example()