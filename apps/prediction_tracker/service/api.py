"""
Prediction Service API

Simple HTTP service for prediction tracking.
4 endpoints: create, resolve, query, stats.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import os

from .models import (
    PredictionCreate,
    PredictionResolve,
    Prediction,
    AgentStats,
    PredictionResponse,
    ResolveResponse,
    ErrorResponse
)
from .storage import PredictionStore


# Initialize FastAPI app
app = FastAPI(
    title="Prediction Tracker API",
    description="Track predictions and measure calibration",
    version="1.0.0"
)

# Initialize storage
db_path = os.getenv("PREDICTION_DB", "tracker.db")
store = PredictionStore(db_path)


@app.get("/")
def root():
    """API status endpoint."""
    return {
        "service": "Prediction Tracker API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/predictions", response_model=PredictionResponse)
def create_prediction(prediction: PredictionCreate):
    """
    Create a new prediction.

    Args:
        prediction: Prediction data (agent, probability, horizon, etc.)

    Returns:
        Prediction ID and confirmation

    Raises:
        400: Invalid prediction data
        500: Database error
    """
    try:
        pred_id = store.create_prediction(
            agent_name=prediction.agent_name,
            probability=prediction.probability,
            horizon_minutes=prediction.horizon_minutes,
            condition=prediction.condition,
            context=prediction.context
        )

        return PredictionResponse(
            id=pred_id,
            agent_name=prediction.agent_name,
            status="registered"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predictions/{prediction_id}/resolve", response_model=ResolveResponse)
def resolve_prediction(prediction_id: int, resolution: PredictionResolve):
    """
    Resolve a prediction with an outcome.

    Args:
        prediction_id: ID of prediction to resolve
        resolution: Outcome (True/False)

    Returns:
        Brier score and confirmation

    Raises:
        404: Prediction not found
        500: Database error
    """
    try:
        brier_score = store.resolve_prediction(prediction_id, resolution.outcome)

        return ResolveResponse(
            id=prediction_id,
            outcome=resolution.outcome,
            brier_score=brier_score,
            status="resolved"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predictions", response_model=List[Prediction])
def get_predictions(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """
    Query predictions with optional filters.

    Args:
        agent_name: Filter by agent name (optional)
        resolved: Filter by resolution status - true/false/null for all (optional)
        limit: Maximum results (default: 100, max: 1000)

    Returns:
        List of predictions matching filters
    """
    try:
        predictions = store.get_predictions(
            agent_name=agent_name,
            resolved=resolved,
            limit=limit
        )
        return predictions

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_name}/stats", response_model=AgentStats)
def get_agent_stats(agent_name: str):
    """
    Get calibration statistics for an agent.

    Args:
        agent_name: Name of agent

    Returns:
        Agent statistics (calibration, prediction count, etc.)

    Raises:
        404: Agent not found
    """
    try:
        stats = store.get_agent_stats(agent_name)

        if not stats:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        return AgentStats(**stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents", response_model=List[AgentStats])
def get_leaderboard():
    """
    Get leaderboard of all agents sorted by calibration.

    Returns:
        List of agents sorted by calibration (best first)
    """
    try:
        leaderboard = store.get_leaderboard()
        return [AgentStats(**agent) for agent in leaderboard]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup():
    """Run on startup."""
    print(f"Prediction Tracker API starting...")
    print(f"Database: {db_path}")


@app.on_event("shutdown")
async def shutdown():
    """Run on shutdown."""
    print("Shutting down...")
    store.close()
