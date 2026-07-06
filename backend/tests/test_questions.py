import uuid

from httpx import AsyncClient

from app.core.default_questions import DEFAULT_QUESTIONS

TOTAL_DEFAULT_QUESTIONS = sum(len(texts) for texts in DEFAULT_QUESTIONS.values())
FIRST_CATEGORY = next(iter(DEFAULT_QUESTIONS))
FIRST_QUESTION_TEXT = DEFAULT_QUESTIONS[FIRST_CATEGORY][0]
LAST_CATEGORY = list(DEFAULT_QUESTIONS)[-1]
LAST_QUESTION_TEXT = DEFAULT_QUESTIONS[LAST_CATEGORY][-1]


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
    assert len(body) == TOTAL_DEFAULT_QUESTIONS
    assert body[0]["text"] == FIRST_QUESTION_TEXT
    assert body[0]["category"] == FIRST_CATEGORY.value
    assert body[-1]["text"] == LAST_QUESTION_TEXT
    assert body[-1]["category"] == LAST_CATEGORY.value


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
        json={"category": "career_work", "text": "A question only Other Co should see"},
        headers=other_headers,
    )

    mine = await client.get("/questions", headers=auth_headers)
    mine_texts = [q["text"] for q in mine.json()]
    assert "A question only Other Co should see" not in mine_texts


async def test_owner_creates_question(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/questions",
        json={"category": "career_work", "text": "What's your favourite memory?"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["text"] == "What's your favourite memory?"
    assert response.json()["category"] == "career_work"

    listing = await client.get("/questions", headers=auth_headers)
    body = listing.json()
    assert len(body) == TOTAL_DEFAULT_QUESTIONS + 1
    assert body[-1]["text"] == "What's your favourite memory?"


async def test_create_question_requires_valid_category(
    client: AsyncClient, auth_headers: dict
):
    response = await client.post(
        "/questions",
        json={"category": "not_a_real_category", "text": "Sneaky question"},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_created_question_has_requested_category(
    client: AsyncClient, auth_headers: dict
):
    response = await client.post(
        "/questions",
        json={"category": "career_work", "text": "What did you learn on the job?"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    question_id = response.json()["id"]

    listing = await client.get("/questions", headers=auth_headers)
    created = next(q for q in listing.json() if q["id"] == question_id)
    assert created["category"] == "career_work"


async def test_create_question_requires_owner(client: AsyncClient, auth_headers: dict):
    member_headers = await _member_headers(client, auth_headers)
    response = await client.post(
        "/questions",
        json={"category": "career_work", "text": "Sneaky question"},
        headers=member_headers,
    )
    assert response.status_code == 403


async def test_owner_edits_question_wording(client: AsyncClient, auth_headers: dict):
    listing = await client.get("/questions", headers=auth_headers)
    question_id = listing.json()[0]["id"]
    original_category = listing.json()[0]["category"]

    response = await client.put(
        f"/questions/{question_id}",
        json={"text": "Reworded question?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Reworded question?"
    assert response.json()["category"] == original_category

    after = await client.get("/questions", headers=auth_headers)
    edited = next(q for q in after.json() if q["id"] == question_id)
    assert edited["text"] == "Reworded question?"


async def test_edit_question_requires_owner(client: AsyncClient, auth_headers: dict):
    listing = await client.get("/questions", headers=auth_headers)
    question_id = listing.json()[0]["id"]

    member_headers = await _member_headers(client, auth_headers)
    response = await client.put(
        f"/questions/{question_id}",
        json={"text": "Sneaky rewording"},
        headers=member_headers,
    )
    assert response.status_code == 403


async def test_edit_question_requires_auth(client: AsyncClient):
    response = await client.put("/questions/1", json={"text": "No auth"})
    assert response.status_code == 401


async def test_edit_nonexistent_question_returns_404(
    client: AsyncClient, auth_headers: dict
):
    response = await client.put(
        "/questions/999999", json={"text": "Ghost question"}, headers=auth_headers
    )
    assert response.status_code == 404


async def test_edit_other_accounts_question_returns_404(
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

    response = await client.put(
        f"/questions/{other_question_id}",
        json={"text": "Cross-account rewording"},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_owner_deletes_question(client: AsyncClient, auth_headers: dict):
    listing = await client.get("/questions", headers=auth_headers)
    question_id = listing.json()[0]["id"]

    response = await client.delete(f"/questions/{question_id}", headers=auth_headers)
    assert response.status_code == 204

    after = await client.get("/questions", headers=auth_headers)
    assert len(after.json()) == TOTAL_DEFAULT_QUESTIONS - 1
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
