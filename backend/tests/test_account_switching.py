import uuid

from httpx import AsyncClient


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


async def _signup(
    client: AsyncClient, account_name: str, email: str, password: str, user_type: str
):
    response = await client.post(
        "/auth/signup",
        json={
            "account_name": account_name,
            "email": email,
            "password": password,
            "user_type": user_type,
        },
    )
    assert response.status_code == 200
    return response.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_list_accounts_requires_auth(client: AsyncClient):
    response = await client.get("/auth/accounts")
    assert response.status_code == 401


async def test_list_accounts_returns_all_accounts_for_email(client: AsyncClient):
    email = _unique_email()
    acme = await _signup(client, "Acme", email, "password-a", "story_requester")
    globex = await _signup(client, "Globex", email, "password-b", "storyteller")

    response = await client.get(
        "/auth/accounts", headers=_headers(acme["access_token"])
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2

    by_name = {item["name"]: item for item in body}
    assert set(by_name) == {"Acme", "Globex"}
    assert by_name["Acme"]["is_current"] is True
    assert by_name["Acme"]["user_type"] == "story_requester"
    assert by_name["Globex"]["is_current"] is False
    assert by_name["Globex"]["user_type"] == "storyteller"

    # Same query from the other account's token flips which one is "current".
    response2 = await client.get(
        "/auth/accounts", headers=_headers(globex["access_token"])
    )
    by_name2 = {item["name"]: item for item in response2.json()}
    assert by_name2["Globex"]["is_current"] is True
    assert by_name2["Acme"]["is_current"] is False


async def test_switch_account_requires_auth(client: AsyncClient):
    response = await client.post("/auth/switch-account", json={"account_id": 1})
    assert response.status_code == 401


async def test_switch_account_issues_new_token_without_password(
    client: AsyncClient,
):
    email = _unique_email()
    acme = await _signup(client, "Acme", email, "password-a", "story_requester")
    globex = await _signup(client, "Globex", email, "password-b", "storyteller")

    response = await client.post(
        "/auth/switch-account",
        json={"account_id": globex["account"]["id"]},
        headers=_headers(acme["access_token"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account"]["id"] == globex["account"]["id"]
    assert body["user"]["email"] == email
    assert body["user"]["user_type"] == "storyteller"
    assert body["access_token"]
    assert body["access_token"] != acme["access_token"]

    me = await client.get("/auth/me", headers=_headers(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["account"]["id"] == globex["account"]["id"]


async def test_switch_account_rejects_inaccessible_account(client: AsyncClient):
    mine = await _signup(client, "Acme", _unique_email(), "password-a", "storyteller")
    other = await _signup(
        client, "Other Co", _unique_email(), "password-b", "storyteller"
    )

    response = await client.post(
        "/auth/switch-account",
        json={"account_id": other["account"]["id"]},
        headers=_headers(mine["access_token"]),
    )
    assert response.status_code == 404


async def test_switch_account_rejects_nonexistent_account(client: AsyncClient):
    mine = await _signup(client, "Acme", _unique_email(), "password-a", "storyteller")

    response = await client.post(
        "/auth/switch-account",
        json={"account_id": 999999},
        headers=_headers(mine["access_token"]),
    )
    assert response.status_code == 404
