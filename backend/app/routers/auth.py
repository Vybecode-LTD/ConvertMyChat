"""Auth router — Google OAuth + email/password.

Google OAuth flow:
1. Frontend redirects to GET /api/auth/google/login
2. Google redirects back with ?code=...
3. Frontend sends code to POST /api/auth/google/callback
4. Backend exchanges code for user info, creates/finds user, returns JWT
"""

import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import Unauthorized
from app.models.user import User
from app.models.schemas import (
    RegisterRequest, LoginRequest, AuthResponse,
    GoogleCallbackRequest, UserResponse,
)
from app.middleware.auth import get_current_user_required

logger = logging.getLogger(__name__)
router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# === Email/Password ===

@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register with email and password."""
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise Unauthorized("Email already registered")

    user = User(
        email=body.email,
        display_name=body.display_name or body.email.split("@")[0],
        hashed_password=hash_password(body.password),
        auth_provider="email",
        is_admin=(body.email == settings.admin_email),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), user.is_admin)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise Unauthorized("Invalid credentials")
    if not verify_password(body.password, user.hashed_password):
        raise Unauthorized("Invalid credentials")
    if not user.is_active:
        raise Unauthorized("Account disabled")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(str(user.id), user.is_admin)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


# === Google OAuth ===

@router.get("/google/login")
async def google_login():
    """Returns the Google OAuth URL for the frontend to redirect to."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())
    return {"auth_url": url}


@router.post("/google/callback", response_model=AuthResponse)
async def google_callback(body: GoogleCallbackRequest, db: AsyncSession = Depends(get_db)):
    """Exchange Google auth code for user info, create/find user, return JWT."""
    redirect_uri = body.redirect_uri or settings.google_redirect_uri

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": body.code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        if token_resp.status_code != 200:
            logger.error(f"Google token exchange failed: {token_resp.text}")
            raise Unauthorized("Google authentication failed")

        tokens = token_resp.json()
        access_token = tokens.get("access_token")

        # Get user info
        info_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_resp.status_code != 200:
            raise Unauthorized("Failed to get Google user info")

        info = info_resp.json()

    google_id = info["id"]
    email = info["email"]
    name = info.get("name", email.split("@")[0])
    avatar = info.get("picture")

    # Find by google_id or email
    result = await db.execute(
        select(User).where((User.google_id == google_id) | (User.email == email))
    )
    user = result.scalar_one_or_none()

    if user:
        # Update Google info
        user.google_id = google_id
        user.avatar_url = avatar
        user.last_login = datetime.now(timezone.utc)
        if not user.display_name:
            user.display_name = name
    else:
        # Create new user
        user = User(
            email=email,
            display_name=name,
            avatar_url=avatar,
            google_id=google_id,
            auth_provider="google",
            is_admin=(email == settings.admin_email),
            last_login=datetime.now(timezone.utc),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), user.is_admin)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


# === Current User ===

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user_required)):
    return UserResponse.model_validate(user)
