"""
Simple token-based authentication for the web API.
"""

from functools import wraps
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings

security = HTTPBearer(auto_error=False)


def verify_token(token: str) -> bool:
    """Verify if the provided token is valid."""
    if not settings.web.auth_token:
        return True  # No auth configured = allow all
    return token == settings.web.auth_token


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Get current authenticated user."""
    # Check Bearer token
    if credentials and verify_token(credentials.credentials):
        return settings.web.default_user

    # Check query param token
    token = request.query_params.get("token")
    if token and verify_token(token):
        return settings.web.default_user

    # Check cookie
    cookie_token = request.cookies.get("auth_token")
    if cookie_token and verify_token(cookie_token):
        return settings.web.default_user

    # No auth configured = allow
    if not settings.web.auth_token:
        return settings.web.default_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
    )


def optional_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Optional auth - returns default user if no auth configured."""
    if not settings.web.auth_token:
        return settings.web.default_user

    if credentials and verify_token(credentials.credentials):
        return settings.web.default_user

    token = request.query_params.get("token")
    if token and verify_token(token):
        return settings.web.default_user

    cookie_token = request.cookies.get("auth_token")
    if cookie_token and verify_token(cookie_token):
        return settings.web.default_user

    return settings.web.default_user
