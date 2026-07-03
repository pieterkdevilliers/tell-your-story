import uuid

from httpx import AsyncClient


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


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


async def _first_question_id(client: AsyncClient, headers: dict) -> int:
    listing = await client.get("/questions", headers=headers)
    return listing.json()[0]["id"]


async def test_storyteller_creates_answer(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)

    response = await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "My earliest memory is..."},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["text"] == "My earliest memory is..."
    assert response.json()["question_id"] == question_id

    listing = await client.get("/questions", headers=headers)
    question = next(q for q in listing.json() if q["id"] == question_id)
    assert question["answer"]["text"] == "My earliest memory is..."


async def test_upsert_answer_updates_existing_answer(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)

    first = await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "First draft"},
        headers=headers,
    )
    second = await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "Revised answer"},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["text"] == "Revised answer"

    listing = await client.get("/questions", headers=headers)
    question = next(q for q in listing.json() if q["id"] == question_id)
    assert question["answer"]["text"] == "Revised answer"


async def test_upsert_answer_requires_storyteller(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])
    question_id = await _first_question_id(client, headers)

    response = await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "Sneaky answer"},
        headers=headers,
    )
    assert response.status_code == 403


async def test_upsert_answer_requires_auth(client: AsyncClient):
    response = await client.put("/questions/1/answer", json={"text": "No auth"})
    assert response.status_code == 401


async def test_upsert_answer_rejects_other_accounts_question(client: AsyncClient):
    storyteller_a = await _signup(client, "storyteller")
    storyteller_b = await _signup(client, "storyteller")
    other_question_id = await _first_question_id(
        client, _headers(storyteller_b["access_token"])
    )

    response = await client.put(
        f"/questions/{other_question_id}/answer",
        json={"text": "Cross-account attempt"},
        headers=_headers(storyteller_a["access_token"]),
    )
    assert response.status_code == 404


async def test_upsert_answer_nonexistent_question_returns_404(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    response = await client.put(
        "/questions/999999/answer",
        json={"text": "No such question"},
        headers=_headers(storyteller["access_token"]),
    )
    assert response.status_code == 404


async def test_list_questions_shows_null_answer_when_unanswered(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])

    listing = await client.get("/questions", headers=headers)
    assert all(q["answer"] is None for q in listing.json())
