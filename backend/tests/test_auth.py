import uuid

from httpx import AsyncClient


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


async def test_signup_creates_account_and_owner(client: AsyncClient):
    email = _unique_email()
    response = await client.post(
        "/auth/signup",
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account"]["name"] == "Acme"
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "owner"
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
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
    )
    second = await client.post(
        "/auth/signup",
        json={"account_name": "Globex", "email": email, "password": "supersecret2"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["account"]["id"] != second.json()["account"]["id"]


async def test_login_success(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/auth/signup",
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
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
        json={"account_name": "Acme", "email": email, "password": "supersecret1"},
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
        json={"account_name": "Acme", "email": email, "password": password},
    )
    await client.post(
        "/auth/signup",
        json={"account_name": "Globex", "email": email, "password": password},
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
