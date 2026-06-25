from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.prediction import (
    Prediction,
    PredictionReviewStatus,
    PredictionStatus,
    TumorClass,
)
from app.models.user import User, UserRole
from app.schemas.dashboard import DashboardStatistics, TumorClassStatistic


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_statistics(self, *, current_user: User) -> DashboardStatistics:
        patient_conditions = []
        prediction_conditions = []

        if current_user.role == UserRole.doctor:
            patient_conditions.append(Patient.created_by == current_user.id)
            prediction_conditions.append(
                Prediction.doctor_id == current_user.id
            )

        total_patients_query = select(func.count()).select_from(Patient)
        total_predictions_query = select(func.count()).select_from(Prediction)
        successful_query = select(func.count()).select_from(Prediction).where(
            Prediction.status == PredictionStatus.success
        )
        failed_query = select(func.count()).select_from(Prediction).where(
            Prediction.status == PredictionStatus.failed
        )
        reviewed_query = select(func.count()).select_from(Prediction).where(
            Prediction.review_status != PredictionReviewStatus.pending
        )

        if patient_conditions:
            total_patients_query = total_patients_query.where(
                *patient_conditions
            )
        if prediction_conditions:
            total_predictions_query = total_predictions_query.where(
                *prediction_conditions
            )
            successful_query = successful_query.where(*prediction_conditions)
            failed_query = failed_query.where(*prediction_conditions)
            reviewed_query = reviewed_query.where(*prediction_conditions)

        total_patients = self.db.scalar(total_patients_query) or 0
        total_predictions = self.db.scalar(total_predictions_query) or 0
        successful_predictions = self.db.scalar(successful_query) or 0
        failed_predictions = self.db.scalar(failed_query) or 0
        reviewed_predictions = self.db.scalar(reviewed_query) or 0

        distribution_query = (
            select(Prediction.predicted_class, func.count())
            .where(
                Prediction.status == PredictionStatus.success,
                Prediction.predicted_class.is_not(None),
            )
            .group_by(Prediction.predicted_class)
        )
        if prediction_conditions:
            distribution_query = distribution_query.where(
                *prediction_conditions
            )

        counts = {
            tumor_class: count
            for tumor_class, count in self.db.execute(
                distribution_query
            ).all()
        }

        distribution = [
            TumorClassStatistic(
                tumor_class=tumor_class,
                count=counts.get(tumor_class, 0),
                percentage=(
                    round(
                        counts.get(tumor_class, 0)
                        / successful_predictions
                        * 100,
                        2,
                    )
                    if successful_predictions
                    else 0
                ),
            )
            for tumor_class in TumorClass
        ]

        return DashboardStatistics(
            total_patients=total_patients,
            total_predictions=total_predictions,
            successful_predictions=successful_predictions,
            failed_predictions=failed_predictions,
            success_rate=(
                round(
                    successful_predictions / total_predictions * 100,
                    2,
                )
                if total_predictions
                else 0
            ),
            reviewed_predictions=reviewed_predictions,
            review_rate=(
                round(
                    reviewed_predictions / successful_predictions * 100,
                    2,
                )
                if successful_predictions
                else 0
            ),
            result_distribution=distribution,
        )
