from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.prediction import TumorClass


class TumorClassStatistic(BaseModel):
    tumor_class: TumorClass
    count: int = Field(..., ge=0)
    percentage: float = Field(..., ge=0, le=100)


class DashboardStatistics(BaseModel):
    total_patients: int = Field(..., ge=0)
    total_predictions: int = Field(..., ge=0)
    successful_predictions: int = Field(..., ge=0)
    failed_predictions: int = Field(..., ge=0)
    success_rate: float = Field(..., ge=0, le=100)
    reviewed_predictions: int = Field(..., ge=0)
    review_rate: float = Field(..., ge=0, le=100)
    result_distribution: list[TumorClassStatistic] = Field(default_factory=list)
