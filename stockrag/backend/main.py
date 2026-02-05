from fastapi import FastAPI
from config import settings
import uvicorn

app = FastAPI(title="Stock Recommendation API")

@app.get("/api/health") 
async def health():
    return {"status": "healthy"} 

if __name__ == "__main__":
    uvicorn.run("main:app", port=settings.api_port, reload=True)