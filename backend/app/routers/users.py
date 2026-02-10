from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User, UserRole
from app.models.role import Role
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.middleware.auth import get_current_user, require_permission
from app.services.auth import hash_password

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = 0, limit: int = 50,
    current_user: User = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar()
    result = await db.execute(
        select(User).options(selectinload(User.roles)).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return UserListResponse(
        users=[UserResponse(
            id=u.id, email=u.email, username=u.username, first_name=u.first_name,
            last_name=u.last_name, is_active=u.is_active, is_superadmin=u.is_superadmin,
            preferred_language=u.preferred_language, created_at=u.created_at, updated_at=u.updated_at,
            roles=[{"id": str(r.id), "name": r.name} for r in u.roles],
        ) for u in users],
        total=total,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission("users", "write")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where((User.email == user_data.email) | (User.username == user_data.username)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already exists")
    user = User(
        email=user_data.email, username=user_data.username,
        hashed_password=hash_password(user_data.password),
        first_name=user_data.first_name, last_name=user_data.last_name,
        is_active=user_data.is_active, preferred_language=user_data.preferred_language,
    )
    db.add(user)
    await db.flush()
    for role_id in (user_data.role_ids or []):
        db.add(UserRole(user_id=user.id, role_id=role_id))
    await db.commit()
    await db.refresh(user)
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user.id))
    user = result.scalar_one()
    return UserResponse(
        id=user.id, email=user.email, username=user.username, first_name=user.first_name,
        last_name=user.last_name, is_active=user.is_active, is_superadmin=user.is_superadmin,
        preferred_language=user.preferred_language, created_at=user.created_at, updated_at=user.updated_at,
        roles=[{"id": str(r.id), "name": r.name} for r in user.roles],
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=user.id, email=user.email, username=user.username, first_name=user.first_name,
        last_name=user.last_name, is_active=user.is_active, is_superadmin=user.is_superadmin,
        preferred_language=user.preferred_language, created_at=user.created_at, updated_at=user.updated_at,
        roles=[{"id": str(r.id), "name": r.name} for r in user.roles],
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, user_data: UserUpdate,
    current_user: User = Depends(require_permission("users", "write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    update_data = user_data.model_dump(exclude_unset=True)
    if "password" in update_data:
        user.hashed_password = hash_password(update_data.pop("password"))
    role_ids = update_data.pop("role_ids", None)
    for key, value in update_data.items():
        setattr(user, key, value)
    if role_ids is not None:
        await db.execute(
            UserRole.__table__.delete().where(UserRole.user_id == user_id)
        )
        for role_id in role_ids:
            db.add(UserRole(user_id=user.id, role_id=role_id))
    await db.commit()
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = result.scalar_one()
    return UserResponse(
        id=user.id, email=user.email, username=user.username, first_name=user.first_name,
        last_name=user.last_name, is_active=user.is_active, is_superadmin=user.is_superadmin,
        preferred_language=user.preferred_language, created_at=user.created_at, updated_at=user.updated_at,
        roles=[{"id": str(r.id), "name": r.name} for r in user.roles],
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_permission("users", "delete")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete superadmin")
    await db.delete(user)
    await db.commit()
