import re
import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def captured_emails(monkeypatch):
    calls = []

    async def fake_send_email(to_email, subject, body):
        calls.append({"to": to_email, "subject": subject, "body": body})

    monkeypatch.setattr(
        "app.services.password_reset_service.send_email", fake_send_email
    )
    return calls


def _extract_token(body: str) -> str:
    match = re.search(r"token=([\w\-]+)", body)
    assert match, f"no token found in email body: {body}"
    return match.group(1)


async def test_request_existing_email(
    client: AsyncClient, db_session: AsyncSession, captured_emails
):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
    )

    response = await client.post("/auth/password-reset/request", json={"email": email})
    assert response.status_code == 200

    rows = (await db_session.execute(select(PasswordResetToken))).scalars().all()
    assert len(rows) == 1
    assert len(captured_emails) == 1
    assert captured_emails[0]["to"] == email
    assert "token=" in captured_emails[0]["body"]


async def test_request_nonexistent_email_same_response(
    client: AsyncClient, db_session: AsyncSession, captured_emails
):
    response = await client.post(
        "/auth/password-reset/request", json={"email": _unique_email()}
    )
    assert response.status_code == 200
    assert response.json()["message"] == (
        "If that email exists, we've sent password reset instructions."
    )

    rows = (await db_session.execute(select(PasswordResetToken))).scalars().all()
    assert len(rows) == 0
    assert len(captured_emails) == 0


async def test_request_matches_existing_response_message(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
    )
    response = await client.post("/auth/password-reset/request", json={"email": email})
    assert response.json()["message"] == (
        "If that email exists, we've sent password reset instructions."
    )


async def test_request_email_matching_two_accounts(
    client: AsyncClient, db_session: AsyncSession, captured_emails
):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
    )
    await client.post(
        "/auth/signup",
        json={"account_name": "Globex", "email": email, "password": "supersecret2"},
    )

    response = await client.post("/auth/password-reset/request", json={"email": email})
    assert response.status_code == 200

    rows = (await db_session.execute(select(PasswordResetToken))).scalars().all()
    assert len(rows) == 1
    assert len(captured_emails) == 1
    body = captured_emails[0]["body"]
    assert "Acme" in body
    assert "Globex" in body


async def test_confirm_valid_token_updates_password_and_old_fails(
    client: AsyncClient, captured_emails
):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
    )
    await client.post("/auth/password-reset/request", json={"email": email})
    token = _extract_token(captured_emails[0]["body"])

    response = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "brand-new-pass"},
    )
    assert response.status_code == 200

    new_login = await client.post(
        "/auth/login", json={"email": email, "password": "brand-new-pass"}
    )
    assert new_login.status_code == 200

    old_login = await client.post(
        "/auth/login", json={"email": email, "password": "supersecret1"}
    )
    assert old_login.status_code == 401


async def test_confirm_token_shared_across_two_accounts(
    client: AsyncClient, captured_emails
):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
    )
    await client.post(
        "/auth/signup",
        json={"account_name": "Globex", "email": email, "password": "supersecret2"},
    )
    await client.post("/auth/password-reset/request", json={"email": email})
    token = _extract_token(captured_emails[0]["body"])

    response = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "brand-new-pass"},
    )
    assert response.status_code == 200

    acme_login = await client.post(
        "/auth/login",
        json={"email": email, "password": "brand-new-pass"},
    )
    # Ambiguous (matches both accounts with the same new password) -> account list
    assert acme_login.status_code == 200
    assert acme_login.json().get("accounts") is not None
    assert len(acme_login.json()["accounts"]) == 2


async def test_confirm_invalid_token_returns_400(client: AsyncClient):
    response = await client.post(
        "/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "whatever123"},
    )
    assert response.status_code == 400


async def test_confirm_expired_token_returns_400(
    client: AsyncClient, db_session: AsyncSession, captured_emails
):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
    )
    await client.post("/auth/password-reset/request", json={"email": email})
    token = _extract_token(captured_emails[0]["body"])

    rows = (await db_session.execute(select(PasswordResetToken))).scalars().all()
    rows[0].expires_at = datetime.utcnow() - timedelta(minutes=1)
    await db_session.commit()

    response = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "brand-new-pass"},
    )
    assert response.status_code == 400


async def test_confirm_token_is_single_use(client: AsyncClient, captured_emails):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
    )
    await client.post("/auth/password-reset/request", json={"email": email})
    token = _extract_token(captured_emails[0]["body"])

    first = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "brand-new-pass"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "another-pass"},
    )
    assert second.status_code == 400
