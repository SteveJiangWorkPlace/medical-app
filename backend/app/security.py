import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import ApiRateLimit


def require_admin_api_key(x_admin_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if settings.app_env != "production" and not settings.admin_api_key:
        return
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured.",
        )
    if not x_admin_api_key or not secrets.compare_digest(x_admin_api_key, settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key.",
        )


def require_hybrid_rate_limit(request: Request, db: Session = Depends(get_db)) -> None:
    settings = get_settings()
    if settings.app_env != "production":
        return

    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    bucket_key = f"hybrid:{client_ip}"
    now = datetime.now(timezone.utc)
    window_start = now.replace(second=0, microsecond=0)

    statement = (
        insert(ApiRateLimit)
        .values(bucket_key=bucket_key, window_start=window_start, request_count=1)
        .on_conflict_do_update(
            constraint="uq_api_rate_limits_bucket_window",
            set_={"request_count": ApiRateLimit.request_count + 1},
        )
        .returning(ApiRateLimit.request_count)
    )
    count = db.execute(statement).scalar_one()
    db.commit()
    if count > settings.hybrid_rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    cutoff = now - timedelta(minutes=10)
    db.query(ApiRateLimit).filter(ApiRateLimit.window_start < cutoff).delete()
    db.commit()
