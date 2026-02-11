# src/api/routers/monitoring.py

from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from src.api.routers.auth import get_current_user
from src.services.rate_limiter import get_rate_limiter, check_user_rate_limit

router = APIRouter()


class RateLimitStats(BaseModel):
    requests_this_minute: int
    requests_this_hour: int
    minute_limit: int
    hour_limit: int
    minute_remaining: int
    hour_remaining: int
    minute_percentage: float
    hour_percentage: float


@router.get("/rate-limit/status", response_model=RateLimitStats)
def get_rate_limit_status(request: Request, user_id: int = Depends(get_current_user)):
    """
    Get current rate limit usage for the authenticated user.
    Shows requests used, limits, remaining quota, and usage percentage.
    """
    # Check rate limit on this endpoint too
    check_user_rate_limit(request, user_id)
    
    rate_limiter = get_rate_limiter()
    stats = rate_limiter.get_stats(user_id)
    
    minute_remaining = max(0, stats["minute_limit"] - stats["requests_this_minute"])
    hour_remaining = max(0, stats["hour_limit"] - stats["requests_this_hour"])
    
    minute_percentage = (stats["requests_this_minute"] / stats["minute_limit"]) * 100
    hour_percentage = (stats["requests_this_hour"] / stats["hour_limit"]) * 100
    
    return RateLimitStats(
        requests_this_minute=stats["requests_this_minute"],
        requests_this_hour=stats["requests_this_hour"],
        minute_limit=stats["minute_limit"],
        hour_limit=stats["hour_limit"],
        minute_remaining=minute_remaining,
        hour_remaining=hour_remaining,
        minute_percentage=round(minute_percentage, 2),
        hour_percentage=round(hour_percentage, 2),
    )
