"""Optional JWT auth middleware.

Key design: PASSES THROUGH when no token is present.
The app works without login — auth is only required for
history and admin routes, enforced at the router level.
"""

from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import Unauthorized, Forbidden
from app.models.user import User

# optional=True means it won't reject requests without a token
_bearer = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Returns the user if a valid token is present, None otherwise.

    Use this for routes that work for both anonymous and logged-in users
    (e.g., extract/export — saves to history if logged in).
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user and not user.is_active:
        return None

    return user


async def get_current_user_required(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Returns the user or raises 401. Use for protected routes."""
    if credentials is None:
        raise Unauthorized()

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise Unauthorized("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise Unauthorized()

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise Unauthorized("User not found")
    if not user.is_active:
        raise Unauthorized("Account disabled")

    return user


async def get_admin_user(
    user: User = Depends(get_current_user_required),
) -> User:
    """Returns the user if they are an admin, raises 403 otherwise."""
    if not user.is_admin:
        raise Forbidden()
    return user
