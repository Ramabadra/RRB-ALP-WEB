"""
Analytics Service — handles computing user performance statistics.
"""

from __future__ import annotations

import logging
from typing import Dict, List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import Attempt
from app.models.result import Result
from app.schemas.analytics import (
    AnalyticsResponse,
    ScoreDataPoint,
    SubjectAnalytics,
    TopicAnalytics,
    WeakArea,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_dashboard_analytics(self, user_id: UUID) -> AnalyticsResponse:
        """
        Calculates all high-level aggregates for a user's dashboard.
        """
        # 1. Overall stats
        stmt_overall = select(
            func.count(Result.id).label("total_attempts"),
            func.avg(Result.score).label("average_score"),
            func.max(Result.score).label("best_score"),
        ).where(
            Result.user_id == user_id,
        )
        overall_res = await self.db.execute(stmt_overall)
        overall_row = overall_res.first()
        
        if not overall_row or overall_row.total_attempts == 0:
            return self._empty_analytics_response()

        total_attempts = overall_row.total_attempts
        avg_score = float(overall_row.average_score or 0.0)
        best_score = float(overall_row.best_score or 0.0)

        # Latest score
        stmt_latest = select(Result).where(
            Result.user_id == user_id,
        ).order_by(Result.created_at.desc()).limit(1)
        latest_res = await self.db.execute(stmt_latest)
        latest_result = latest_res.scalar_one_or_none()
        latest_score = float(latest_result.score) if latest_result else None

        # 2. Score trend (last 10 attempts)
        stmt_trend = select(Result).where(
            Result.user_id == user_id,
        ).order_by(Result.created_at.asc()).limit(10)
        trend_res = await self.db.execute(stmt_trend)
        trend_results = list(trend_res.scalars().all())
        
        score_trend = []
        accuracy_trend = []
        for res in trend_results:
            if res.total_questions > 0 and res.created_at:
                pt = ScoreDataPoint(
                    attempt_id=str(res.attempt_id),
                    date=res.created_at.isoformat(),
                    score=float(res.score),
                    max_score=float(res.max_score),
                    accuracy=res.accuracy,
                )
                score_trend.append(pt)
                accuracy_trend.append(pt)
                
        # 3. Overall question stats
        stmt_qstats = select(
            func.sum(Result.correct).label("correct"),
            func.sum(Result.wrong).label("wrong"),
            func.sum(Result.unanswered).label("unanswered"),
            func.avg(Result.accuracy).label("avg_accuracy"),
        ).where(
            Result.user_id == user_id,
        )
        
        qstats_res = await self.db.execute(stmt_qstats)
        qstats_row = qstats_res.first()
        
        tot_correct = int(qstats_row.correct or 0)
        tot_wrong = int(qstats_row.wrong or 0)
        tot_unanswered = int(qstats_row.unanswered or 0)
        tot_attempted = tot_correct + tot_wrong
        avg_accuracy = float(qstats_row.avg_accuracy or 0.0)
        
        return AnalyticsResponse(
            total_attempts=total_attempts,
            total_questions_attempted=tot_attempted,
            total_correct=tot_correct,
            total_wrong=tot_wrong,
            total_unanswered=tot_unanswered,
            average_score=round(avg_score, 2),
            best_score=best_score,
            latest_score=latest_score,
            average_accuracy=round(avg_accuracy, 2),
            score_trend=score_trend,
            accuracy_trend=accuracy_trend,
            subject_performance={},
            topic_performance={},
            weak_subjects=[],
            weak_topics=[],
        )

    def _empty_analytics_response(self) -> AnalyticsResponse:
        return AnalyticsResponse(
            total_attempts=0,
            total_questions_attempted=0,
            total_correct=0,
            total_wrong=0,
            total_unanswered=0,
            average_score=0.0,
            best_score=0.0,
            latest_score=None,
            average_accuracy=0.0,
            score_trend=[],
            accuracy_trend=[],
            subject_performance={},
            topic_performance={},
            weak_subjects=[],
            weak_topics=[],
        )
