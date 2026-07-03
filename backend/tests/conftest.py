import os
import uuid

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-bytes-long")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def signed_up_user(client: AsyncClient) -> dict:
    unique = uuid.uuid4().hex[:8]
    response = await client.post(
        "/auth/signup",
        json={
            "account_name": f"Account {unique}",
            "email": f"owner-{unique}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest_asyncio.fixture(scope="function")
async def auth_headers(signed_up_user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {signed_up_user['access_token']}"}
