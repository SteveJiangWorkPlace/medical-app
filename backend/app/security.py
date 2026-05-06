import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings


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
