"""Analytics router."""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.analytics import AnalyticsResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=AnalyticsResponse)
async def get_analytics_dashboard(
    db: DbSession,
    user: CurrentUser,
):
    """
    Returns aggregated analytics for the authenticated user,
    including total attempts, accuracy, and score trends.
    """
    service = AnalyticsService(db)
    return await service.get_dashboard_analytics(user.id)
