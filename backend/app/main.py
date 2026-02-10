from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.config import get_settings
from app.database import engine, Base, async_session
from app.models import *
from app.models.user import User
from app.models.role import Role, DEFAULT_PERMISSIONS
from app.services.auth import hash_password
from app.routers import auth, users, roles, llm_config, consumption, quotas, costs, moderation, agents, system

settings = get_settings()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if not result.scalar_one_or_none():
            admin_role = Role(
                name="admin",
                description="Full administrator access",
                permissions={k: {a: True for a in v} for k, v in DEFAULT_PERMISSIONS.items()},
            )
            session.add(admin_role)
            await session.flush()

            user_role = Role(
                name="user",
                description="Standard user access",
                permissions=DEFAULT_PERMISSIONS,
            )
            session.add(user_role)
            await session.flush()

            admin = User(
                email=settings.ADMIN_EMAIL,
                username="admin",
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                first_name="Admin",
                last_name="NOVA2",
                is_superadmin=True,
            )
            session.add(admin)
            await session.flush()

            from app.models.user import UserRole as UserRoleModel
            session.add(UserRoleModel(user_id=admin.id, role_id=admin_role.id))
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(llm_config.router)
app.include_router(consumption.router)
app.include_router(quotas.router)
app.include_router(costs.router)
app.include_router(moderation.router)
app.include_router(agents.router)
app.include_router(system.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
