"""
Pydantic models for prediction service API.

Simple, clean data models with validation.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class PredictionCreate(BaseModel):
    """Request to create a prediction."""
    agent_name: str = Field(..., min_length=1, description="Name of agent making prediction")
    probability: float = Field(..., ge=0.0, le=1.0, description="Predicted probability")
    horizon_minutes: int = Field(..., gt=0, description="Time horizon in minutes")
    condition: str = Field(default="task_complete", description="Condition being predicted")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class PredictionResolve(BaseModel):
    """Request to resolve a prediction."""
    outcome: bool = Field(..., description="Actual outcome (True/False)")


class Prediction(BaseModel):
    """A prediction with all fields."""
    id: int
    agent_name: str
    probability: float
    horizon_minutes: int
    condition: str
    context: Dict[str, Any]
    created_at: datetime
    resolved_at: Optional[datetime] = None
    outcome: Optional[bool] = None
    brier_score: Optional[float] = None

    class Config:
        from_attributes = True


class AgentStats(BaseModel):
    """Statistics for an agent."""
    name: str
    calibration: Optional[float] = None
    prediction_count: int = 0
    last_updated: Optional[datetime] = None


class PredictionResponse(BaseModel):
    """Response after creating a prediction."""
    id: int
    agent_name: str
    status: str = "registered"


class ResolveResponse(BaseModel):
    """Response after resolving a prediction."""
    id: int
    outcome: bool
    brier_score: float
    status: str = "resolved"


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
