import uuid

from httpx import AsyncClient


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


async def _create_member(client: AsyncClient, owner_headers: dict) -> dict:
    response = await client.post(
        "/users",
        json={"email": _unique_email(), "password": "supersecret1"},
        headers=owner_headers,
    )
    assert response.status_code == 201
    return response.json()


async def test_list_users_returns_only_own_account(
    client: AsyncClient, auth_headers: dict
):
    response = await client.get("/users", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_owner_creates_member(client: AsyncClient, auth_headers: dict):
    member = await _create_member(client, auth_headers)
    assert member["role"] == "member"

    listing = await client.get("/users", headers=auth_headers)
    assert len(listing.json()) == 2


async def test_create_user_requires_owner(client: AsyncClient, auth_headers: dict):
    member = await _create_member(client, auth_headers)
    member_login = await client.post(
        "/auth/login", json={"email": member["email"], "password": "supersecret1"}
    )
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}

    response = await client.post(
        "/users",
        json={"email": _unique_email(), "password": "supersecret1"},
        headers=member_headers,
    )
    assert response.status_code == 403


async def test_update_own_profile(client: AsyncClient, auth_headers: dict):
    me = await client.get("/auth/me", headers=auth_headers)
    owner_id = me.json()["user"]["id"]

    new_email = _unique_email()
    response = await client.patch(
        f"/users/{owner_id}", json={"email": new_email}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["email"] == new_email


async def test_update_other_user_requires_owner(
    client: AsyncClient, auth_headers: dict
):
    member = await _create_member(client, auth_headers)
    member_login = await client.post(
        "/auth/login", json={"email": member["email"], "password": "supersecret1"}
    )
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}

    owner_me = await client.get("/auth/me", headers=auth_headers)
    owner_id = owner_me.json()["user"]["id"]

    response = await client.patch(
        f"/users/{owner_id}", json={"email": _unique_email()}, headers=member_headers
    )
    assert response.status_code == 403


async def test_member_cannot_change_own_role(client: AsyncClient, auth_headers: dict):
    member = await _create_member(client, auth_headers)
    member_login = await client.post(
        "/auth/login", json={"email": member["email"], "password": "supersecret1"}
    )
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}

    response = await client.patch(
        f"/users/{member['id']}", json={"role": "owner"}, headers=member_headers
    )
    assert response.status_code == 403


async def test_owner_deletes_member(client: AsyncClient, auth_headers: dict):
    member = await _create_member(client, auth_headers)
    response = await client.delete(f"/users/{member['id']}", headers=auth_headers)
    assert response.status_code == 204

    listing = await client.get("/users", headers=auth_headers)
    assert len(listing.json()) == 1


async def test_cross_account_isolation(client: AsyncClient, auth_headers: dict):
    other_signup = await client.post(
        "/auth/signup",
        json={
            "account_name": "Other Co",
            "email": _unique_email(),
            "password": "supersecret1",
        },
    )
    other_user_id = other_signup.json()["user"]["id"]

    get_response = await client.get(f"/users/{other_user_id}", headers=auth_headers)
    assert get_response.status_code == 404

    patch_response = await client.patch(
        f"/users/{other_user_id}",
        json={"email": _unique_email()},
        headers=auth_headers,
    )
    assert patch_response.status_code == 404

    delete_response = await client.delete(
        f"/users/{other_user_id}", headers=auth_headers
    )
    assert delete_response.status_code == 404


async def test_last_owner_cannot_be_deleted(client: AsyncClient, auth_headers: dict):
    me = await client.get("/auth/me", headers=auth_headers)
    owner_id = me.json()["user"]["id"]

    response = await client.delete(f"/users/{owner_id}", headers=auth_headers)
    assert response.status_code == 409

    listing = await client.get("/users", headers=auth_headers)
    assert len(listing.json()) == 1


async def test_last_owner_guard_allows_deletion_with_second_owner(
    client: AsyncClient, auth_headers: dict
):
    member = await _create_member(client, auth_headers)
    promote = await client.patch(
        f"/users/{member['id']}", json={"role": "owner"}, headers=auth_headers
    )
    assert promote.status_code == 200

    me = await client.get("/auth/me", headers=auth_headers)
    owner_id = me.json()["user"]["id"]

    response = await client.delete(f"/users/{owner_id}", headers=auth_headers)
    assert response.status_code == 204
