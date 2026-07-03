import uuid

from httpx import AsyncClient

from app.core.default_questions import DEFAULT_QUESTIONS


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


async def _create_member(client: AsyncClient, owner_headers: dict) -> dict:
    response = await client.post(
        "/users",
        json={
            "email": _unique_email(),
            "password": "supersecret1",
            "user_type": "storyteller",
        },
        headers=owner_headers,
    )
    assert response.status_code == 201
    return response.json()


async def _member_headers(client: AsyncClient, owner_headers: dict) -> dict:
    member = await _create_member(client, owner_headers)
    login = await client.post(
        "/auth/login", json={"email": member["email"], "password": "supersecret1"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_signup_seeds_default_questions(client: AsyncClient, auth_headers: dict):
    response = await client.get("/questions", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(DEFAULT_QUESTIONS)
    assert body[0]["text"] == DEFAULT_QUESTIONS[0]
    assert body[-1]["text"] == DEFAULT_QUESTIONS[-1]


async def test_list_questions_requires_auth(client: AsyncClient):
    response = await client.get("/questions")
    assert response.status_code == 401


async def test_list_questions_scoped_to_account(
    client: AsyncClient, auth_headers: dict
):
    other_signup = await client.post(
        "/auth/signup",
        json={
            "account_name": "Other Co",
            "email": _unique_email(),
            "password": "supersecret1",
            "user_type": "story_requester",
        },
    )
    other_headers = {"Authorization": f"Bearer {other_signup.json()['access_token']}"}
    await client.post(
        "/questions",
        json={"text": "A question only Other Co should see"},
        headers=other_headers,
    )

    mine = await client.get("/questions", headers=auth_headers)
    mine_texts = [q["text"] for q in mine.json()]
    assert "A question only Other Co should see" not in mine_texts


async def test_owner_creates_question(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/questions",
        json={"text": "What's your favourite memory?"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["text"] == "What's your favourite memory?"

    listing = await client.get("/questions", headers=auth_headers)
    body = listing.json()
    assert len(body) == len(DEFAULT_QUESTIONS) + 1
    assert body[-1]["text"] == "What's your favourite memory?"


async def test_create_question_requires_owner(client: AsyncClient, auth_headers: dict):
    member_headers = await _member_headers(client, auth_headers)
    response = await client.post(
        "/questions", json={"text": "Sneaky question"}, headers=member_headers
    )
    assert response.status_code == 403


async def test_owner_deletes_question(client: AsyncClient, auth_headers: dict):
    listing = await client.get("/questions", headers=auth_headers)
    question_id = listing.json()[0]["id"]

    response = await client.delete(f"/questions/{question_id}", headers=auth_headers)
    assert response.status_code == 204

    after = await client.get("/questions", headers=auth_headers)
    assert len(after.json()) == len(DEFAULT_QUESTIONS) - 1
    assert all(q["id"] != question_id for q in after.json())


async def test_delete_question_requires_owner(client: AsyncClient, auth_headers: dict):
    listing = await client.get("/questions", headers=auth_headers)
    question_id = listing.json()[0]["id"]

    member_headers = await _member_headers(client, auth_headers)
    response = await client.delete(f"/questions/{question_id}", headers=member_headers)
    assert response.status_code == 403


async def test_delete_nonexistent_question_returns_404(
    client: AsyncClient, auth_headers: dict
):
    response = await client.delete("/questions/999999", headers=auth_headers)
    assert response.status_code == 404


async def test_delete_other_accounts_question_returns_404(
    client: AsyncClient, auth_headers: dict
):
    other_signup = await client.post(
        "/auth/signup",
        json={
            "account_name": "Other Co",
            "email": _unique_email(),
            "password": "supersecret1",
            "user_type": "story_requester",
        },
    )
    other_headers = {"Authorization": f"Bearer {other_signup.json()['access_token']}"}
    other_questions = await client.get("/questions", headers=other_headers)
    other_question_id = other_questions.json()[0]["id"]

    response = await client.delete(
        f"/questions/{other_question_id}", headers=auth_headers
    )
    assert response.status_code == 404
