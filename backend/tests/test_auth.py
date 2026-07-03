import uuid

import pytest
from httpx import AsyncClient


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


async def test_signup_creates_account_and_owner(client: AsyncClient):
    email = _unique_email()
    response = await client.post(
        "/auth/signup",
        json={
            "account_name": "Acme",
            "email": email,
            "password": "supersecret1",
            "user_type": "story_requester",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account"]["name"] == "Acme"
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "owner"
    assert body["user"]["user_type"] == "story_requester"
    assert body["access_token"]


async def test_signup_duplicate_email_in_same_account_not_possible(
    client: AsyncClient,
):
    # A fresh account never has an existing user, so signup never collides
    # with itself; this documents that two different accounts CAN reuse
    # the same owner email, since email is unique per-account not globally.
    email = _unique_email()
    first = await client.post(
        "/auth/signup",
        json={
            "account_name": "Acme",
            "email": email,
            "password": "supersecret1",
            "user_type": "story_requester",
        },
    )
    second = await client.post(
        "/auth/signup",
        json={
            "account_name": "Globex",
            "email": email,
            "password": "supersecret2",
            "user_type": "story_requester",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["account"]["id"] != second.json()["account"]["id"]


@pytest.mark.parametrize("user_type", ["storyteller", "story_requester"])
async def test_signup_persists_user_type(client: AsyncClient, user_type: str):
    email = _unique_email()
    response = await client.post(
        "/auth/signup",
        json={
            "account_name": "Acme",
            "email": email,
            "password": "supersecret1",
            "user_type": user_type,
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["user_type"] == user_type


async def test_signup_requires_user_type(client: AsyncClient):
    response = await client.post(
        "/auth/signup",
        json={
            "account_name": "Acme",
            "email": _unique_email(),
            "password": "supersecret1",
        },
    )
    assert response.status_code == 422


async def test_signup_rejects_viewer_user_type(client: AsyncClient):
    response = await client.post(
        "/auth/signup",
        json={
            "account_name": "Acme",
            "email": _unique_email(),
            "password": "supersecret1",
            "user_type": "viewer",
        },
    )
    assert response.status_code == 422


async def test_same_email_storyteller_in_one_account_story_requester_in_another(
    client: AsyncClient,
):
    email = _unique_email()
    password = "supersecret1"
    storyteller_signup = await client.post(
        "/auth/signup",
        json={
            "account_name": "Acme",
            "email": email,
            "password": password,
            "user_type": "storyteller",
        },
    )
    requester_signup = await client.post(
        "/auth/signup",
        json={
            "account_name": "Globex",
            "email": email,
            "password": password,
            "user_type": "story_requester",
        },
    )
    assert storyteller_signup.status_code == 200
    assert requester_signup.status_code == 200
    assert storyteller_signup.json()["user"]["user_type"] == "storyteller"
    assert requester_signup.json()["user"]["user_type"] == "story_requester"

    login = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200
    accounts = login.json()["accounts"]
    assert len(accounts) == 2

    for choice in accounts:
        resolved = await client.post(
            "/auth/login",
            json={"email": email, "password": password, "account_id": choice["id"]},
        )
        assert resolved.status_code == 200
        me = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {resolved.json()['access_token']}"},
        )
        expected_type = (
            "storyteller"
            if choice["id"] == storyteller_signup.json()["account"]["id"]
            else "story_requester"
        )
        assert me.json()["user"]["user_type"] == expected_type


async def test_login_success(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={
            "account_name": "Acme",
            "email": email,
            "password": "supersecret1",
            "user_type": "story_requester",
        },
    )
    response = await client.post(
        "/auth/login", json={"email": email, "password": "supersecret1"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == email


async def test_login_wrong_password(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={
            "account_name": "Acme",
            "email": email,
            "password": "supersecret1",
            "user_type": "story_requester",
        },
    )
    response = await client.post(
        "/auth/login", json={"email": email, "password": "wrong"}
    )
    assert response.status_code == 401


async def test_login_nonexistent_email(client: AsyncClient):
    response = await client.post(
        "/auth/login", json={"email": _unique_email(), "password": "whatever"}
    )
    assert response.status_code == 401


async def test_login_ambiguous_account_returns_choices(client: AsyncClient):
    email = _unique_email()
    password = "supersecret1"
    await client.post(
        "/auth/signup",
        json={
            "account_name": "Acme",
            "email": email,
            "password": password,
            "user_type": "story_requester",
        },
    )
    await client.post(
        "/auth/signup",
        json={
            "account_name": "Globex",
            "email": email,
            "password": password,
            "user_type": "story_requester",
        },
    )

    response = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] is None
    assert len(body["accounts"]) == 2

    chosen_account_id = body["accounts"][0]["id"]
    follow_up = await client.post(
        "/auth/login",
        json={"email": email, "password": password, "account_id": chosen_account_id},
    )
    assert follow_up.status_code == 200
    follow_up_body = follow_up.json()
    assert follow_up_body["access_token"]
    assert follow_up_body["account"]["id"] == chosen_account_id


async def test_get_me_requires_auth(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_get_me_returns_current_user(client: AsyncClient, auth_headers: dict):
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "owner"
    assert body["account"]["id"] == body["user"]["account_id"]
