"""Admin router — user management.

All routes require is_admin=True. Provides:
- List all users (with search/filter)
- Create user accounts
- Update user (toggle active, toggle admin, rename)
- Reset user password
- Delete user account
- View user's export history
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.core.exceptions import ExtractionError, Unauthorized
from app.models.user import User
from app.models.export_history import ExportHistory
from app.models.schemas import (
    AdminUserCreate, AdminUserUpdate, AdminResetPassword,
    AdminUserListResponse, UserResponse, HistoryItem, HistoryListResponse,
)
from app.middleware.auth import get_admin_user

router = APIRouter()


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    search: str | None = Query(None, description="Search by email or name"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users with optional search."""
    q = select(User)
    count_q = select(func.count()).select_from(User)

    if search:
        pattern = f"%{search}%"
        filt = or_(User.email.ilike(pattern), User.display_name.ilike(pattern))
        q = q.where(filt)
        count_q = count_q.where(filt)

    total = (await db.execute(count_q)).scalar()
    rows = (await db.execute(
        q.order_by(desc(User.created_at)).offset(skip).limit(limit)
    )).scalars().all()

    return AdminUserListResponse(
        users=[UserResponse.model_validate(u) for u in rows],
        total=total,
    )


@router.post("/users", response_model=UserResponse)
async def create_user(
    body: AdminUserCreate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user account."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise ExtractionError("Email already registered")

    user = User(
        email=body.email,
        display_name=body.display_name or body.email.split("@")[0],
        hashed_password=hash_password(body.password),
        auth_provider="email",
        is_admin=body.is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user details."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ExtractionError("User not found")
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: AdminUserUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user — toggle active, toggle admin, rename."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ExtractionError("User not found")

    # Prevent de-admin-ing yourself
    if user.id == admin.id and body.is_admin is False:
        raise Unauthorized("Cannot remove your own admin status")

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_admin is not None:
        user.is_admin = body.is_admin

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: UUID,
    body: AdminResetPassword,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset a user's password."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ExtractionError("User not found")

    user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"success": True, "message": f"Password reset for {user.email}"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user and all their export history (cascade)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ExtractionError("User not found")

    if user.id == admin.id:
        raise Unauthorized("Cannot delete your own account from admin panel")

    await db.delete(user)
    await db.commit()
    return {"deleted": True, "email": user.email}


@router.get("/users/{user_id}/history", response_model=HistoryListResponse)
async def user_history(
    user_id: UUID,
    skip: int = 0, limit: int = 20,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """View a specific user's export history."""
    count_q = select(func.count()).select_from(ExportHistory).where(
        ExportHistory.user_id == user_id
    )
    total = (await db.execute(count_q)).scalar()

    q = (select(ExportHistory)
         .where(ExportHistory.user_id == user_id)
         .order_by(desc(ExportHistory.created_at))
         .offset(skip).limit(limit))
    rows = (await db.execute(q)).scalars().all()

    return HistoryListResponse(
        items=[HistoryItem.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/stats")
async def admin_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick dashboard stats."""
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    active_users = (await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)
    )).scalar()
    total_exports = (await db.execute(
        select(func.count()).select_from(ExportHistory)
    )).scalar()
    total_cached = (await db.execute(
        select(func.count()).select_from(
            __import__('app.models.conversation_cache', fromlist=['ConversationCache']).ConversationCache
        )
    )).scalar()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_exports": total_exports,
        "cached_conversations": total_cached,
    }
