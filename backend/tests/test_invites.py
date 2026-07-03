import re
import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import Invite


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def captured_emails(monkeypatch):
    calls = []

    async def fake_send_email(to_email, subject, body):
        calls.append({"to": to_email, "subject": subject, "body": body})

    monkeypatch.setattr("app.services.invite_service.send_email", fake_send_email)
    return calls


def _extract_token(body: str) -> str:
    match = re.search(r"/invite/([\w\-]+)", body)
    assert match, f"no token found in email body: {body}"
    return match.group(1)


async def _signup(client: AsyncClient, user_type: str, password: str = "supersecret1"):
    response = await client.post(
        "/auth/signup",
        json={
            "account_name": f"Account {uuid.uuid4().hex[:8]}",
            "email": _unique_email(),
            "password": password,
            "user_type": user_type,
        },
    )
    assert response.status_code == 200
    return response.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_story_requester_can_invite_storyteller(
    client: AsyncClient, captured_emails
):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    response = await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["invited_user_type"] == "storyteller"
    assert len(captured_emails) == 1


async def test_story_requester_type_cannot_be_invited(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    response = await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "story_requester"},
        headers=headers,
    )
    assert response.status_code == 422


async def test_cannot_invite_viewer_before_storyteller_exists(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    response = await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "viewer"},
        headers=headers,
    )
    assert response.status_code == 409


async def test_storyteller_cannot_invite_another_storyteller(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])

    response = await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=headers,
    )
    assert response.status_code == 403


async def test_story_requester_or_storyteller_can_invite_viewer(
    client: AsyncClient, captured_emails
):
    requester = await _signup(client, "story_requester")
    requester_headers = _headers(requester["access_token"])

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=requester_headers,
    )
    token = _extract_token(captured_emails[-1]["body"])
    accepted = await client.post(
        "/invites/accept", json={"token": token, "password": "supersecret1"}
    )
    assert accepted.status_code == 200
    storyteller_headers = _headers(accepted.json()["access_token"])

    from_requester = await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "viewer"},
        headers=requester_headers,
    )
    assert from_requester.status_code == 201

    from_storyteller = await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "viewer"},
        headers=storyteller_headers,
    )
    assert from_storyteller.status_code == 201


async def test_viewer_cannot_invite_anyone(client: AsyncClient, captured_emails):
    requester = await _signup(client, "story_requester")
    requester_headers = _headers(requester["access_token"])

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=requester_headers,
    )
    storyteller_token = _extract_token(captured_emails[-1]["body"])
    await client.post(
        "/invites/accept",
        json={"token": storyteller_token, "password": "supersecret1"},
    )

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "viewer"},
        headers=requester_headers,
    )
    viewer_token = _extract_token(captured_emails[-1]["body"])
    viewer_accept = await client.post(
        "/invites/accept", json={"token": viewer_token, "password": "supersecret1"}
    )
    viewer_headers = _headers(viewer_accept.json()["access_token"])

    response = await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "viewer"},
        headers=viewer_headers,
    )
    assert response.status_code == 403


async def test_only_one_storyteller_per_account_via_invite(
    client: AsyncClient, captured_emails
):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=headers,
    )
    token = _extract_token(captured_emails[-1]["body"])
    accepted = await client.post(
        "/invites/accept", json={"token": token, "password": "supersecret1"}
    )
    assert accepted.status_code == 200

    second = await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=headers,
    )
    assert second.status_code == 409


async def test_double_accept_race_second_storyteller_invite_conflicts(
    client: AsyncClient, captured_emails
):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=headers,
    )
    first_token = _extract_token(captured_emails[-1]["body"])

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=headers,
    )
    second_token = _extract_token(captured_emails[-1]["body"])

    first_accept = await client.post(
        "/invites/accept", json={"token": first_token, "password": "supersecret1"}
    )
    assert first_accept.status_code == 200

    second_accept = await client.post(
        "/invites/accept", json={"token": second_token, "password": "supersecret1"}
    )
    assert second_accept.status_code == 409


async def test_accept_invite_creates_user_and_logs_in(
    client: AsyncClient, captured_emails
):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])
    invitee_email = _unique_email()

    await client.post(
        "/invites",
        json={"email": invitee_email, "user_type": "storyteller"},
        headers=headers,
    )
    token = _extract_token(captured_emails[-1]["body"])

    preview = await client.get(f"/invites/{token}")
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["email"] == invitee_email
    assert preview_body["user_type"] == "storyteller"

    accept = await client.post(
        "/invites/accept", json={"token": token, "password": "supersecret1"}
    )
    assert accept.status_code == 200
    body = accept.json()
    assert body["access_token"]
    assert body["user"]["role"] == "member"
    assert body["user"]["user_type"] == "storyteller"
    assert body["user"]["email"] == invitee_email

    me = await client.get("/auth/me", headers=_headers(body["access_token"]))
    assert me.status_code == 200


async def test_accept_invite_token_is_single_use(client: AsyncClient, captured_emails):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=headers,
    )
    token = _extract_token(captured_emails[-1]["body"])

    first = await client.post(
        "/invites/accept", json={"token": token, "password": "supersecret1"}
    )
    assert first.status_code == 200

    second = await client.post(
        "/invites/accept", json={"token": token, "password": "supersecret1"}
    )
    assert second.status_code == 404


async def test_accept_invite_expired_token_rejected(
    client: AsyncClient, db_session: AsyncSession, captured_emails
):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=headers,
    )
    token = _extract_token(captured_emails[-1]["body"])

    rows = (await db_session.execute(select(Invite))).scalars().all()
    rows[0].expires_at = datetime.utcnow() - timedelta(minutes=1)
    await db_session.commit()

    response = await client.post(
        "/invites/accept", json={"token": token, "password": "supersecret1"}
    )
    assert response.status_code == 404


async def test_accept_invite_email_already_member_conflicts(
    client: AsyncClient, captured_emails
):
    # Simulates a race: the invitee is added directly (e.g. by the owner via
    # POST /users) while their invite is still outstanding, so by the time
    # they try to accept it, the account already has a user with that email.
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=headers,
    )
    storyteller_token = _extract_token(captured_emails[-1]["body"])
    await client.post(
        "/invites/accept",
        json={"token": storyteller_token, "password": "supersecret1"},
    )

    invitee_email = _unique_email()
    invite = await client.post(
        "/invites",
        json={"email": invitee_email, "user_type": "viewer"},
        headers=headers,
    )
    assert invite.status_code == 201
    token = _extract_token(captured_emails[-1]["body"])

    direct_create = await client.post(
        "/users",
        json={
            "email": invitee_email,
            "password": "supersecret1",
            "user_type": "viewer",
        },
        headers=headers,
    )
    assert direct_create.status_code == 201

    response = await client.post(
        "/invites/accept", json={"token": token, "password": "supersecret1"}
    )
    assert response.status_code == 409


async def test_list_invites_scoped_to_account(client: AsyncClient):
    requester_a = await _signup(client, "story_requester")
    requester_b = await _signup(client, "story_requester")

    await client.post(
        "/invites",
        json={"email": _unique_email(), "user_type": "storyteller"},
        headers=_headers(requester_a["access_token"]),
    )

    listing_a = await client.get(
        "/invites", headers=_headers(requester_a["access_token"])
    )
    listing_b = await client.get(
        "/invites", headers=_headers(requester_b["access_token"])
    )
    assert len(listing_a.json()) == 1
    assert len(listing_b.json()) == 0
