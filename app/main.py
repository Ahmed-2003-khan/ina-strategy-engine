# Purpose: Initializes the FastAPI application and defines API endpoints.

from fastapi import FastAPI
from .schemas import StrategyInput, StrategyOutput

# Initialize the FastAPI app
# We'll add metadata here later for the documentation
app = FastAPI(
    title="INA Strategy Engine (MS 4 - The Brain)",
    description="This service receives financial context and user offers, "
                "then securely decides the next negotiation step.",
    version="1.0.0"
)

# --- Health Check Endpoint ---
@app.get("/health", status_code=200)
async def health_check():
    """
    Simple health check to confirm the service is running.
    """
    return {"status": "ok", "service": "strategy-engine"}

# --- Placeholder for Tomorrow's Work ---
# We will implement this endpoint on Wednesday.
# @app.post("/decide", response_model=StrategyOutput)
# async def decide_strategy(input_data: StrategyInput):
#     # Logic to be added tomorrow
#     pass