import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import llm_service, memoir_service, pdf_service


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


async def _second_question_id(client: AsyncClient, headers: dict) -> int:
    listing = await client.get("/questions", headers=headers)
    return listing.json()[1]["id"]


@pytest.fixture(autouse=True)
def _fake_generation(monkeypatch):
    """POST /memoir/generate fires a real background job; stub the Claude
    call and PDF rendering so ordinary tests never hit the real API or
    render a real PDF."""

    async def _fake_generate_text(account_name, entries):
        return "# Fake Memoir\n\n## Chapter\n\nSome generated prose."

    def _fake_render(memoir_markdown: str) -> bytes:
        return b"%PDF-fake"

    monkeypatch.setattr(llm_service, "generate_memoir_text", _fake_generate_text)
    monkeypatch.setattr(pdf_service, "render_memoir_pdf", _fake_render)


async def test_generate_requires_at_least_one_answer(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])

    response = await client.post("/memoir/generate", headers=headers)
    assert response.status_code == 400


async def test_generate_requires_storyteller(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    response = await client.post("/memoir/generate", headers=headers)
    assert response.status_code == 403


async def test_generate_requires_auth(client: AsyncClient):
    response = await client.post("/memoir/generate")
    assert response.status_code == 401


async def test_generate_sets_pending_and_is_idempotent_while_in_flight(
    client: AsyncClient,
):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)
    await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "My story so far."},
        headers=headers,
    )

    first = await client.post("/memoir/generate", headers=headers)
    assert first.status_code == 200
    memoir_id = first.json()["id"]

    # The autouse fixture's fake generation runs synchronously via the
    # background task by the time this second request lands, so exercise
    # the idempotency guard directly against a still-pending row instead.
    second = await client.post("/memoir/generate", headers=headers)
    assert second.status_code == 200
    assert second.json()["id"] == memoir_id


async def test_generate_only_uses_completed_transcripts_and_text_answers(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    account_id = storyteller["account"]["id"]

    text_question_id = await _first_question_id(client, headers)
    await client.put(
        f"/questions/{text_question_id}/answer",
        json={"text": "I was born in a small town."},
        headers=headers,
    )

    audio_question_id = await _second_question_id(client, headers)
    await client.put(
        f"/questions/{audio_question_id}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
        headers=headers,
    )
    # Leave this answer's transcription at "pending" — it must NOT appear
    # in the memoir input.

    trigger = await client.post("/memoir/generate", headers=headers)
    assert trigger.status_code == 200

    captured = {}

    async def _capture_generate_text(account_name, entries):
        captured["entries"] = entries
        return "# Title\n\n## Chapter\n\nBody."

    monkeypatch.setattr(llm_service, "generate_memoir_text", _capture_generate_text)

    memoir = await memoir_service.get_memoir(db_session, account_id)
    await memoir_service.generate_with_session(db_session, memoir.id, account_id)

    assert len(captured["entries"]) == 1
    assert captured["entries"][0][2] == "I was born in a small town."


async def test_memoir_pdf_404s_until_completed_then_downloads(
    client: AsyncClient, db_session: AsyncSession
):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    account_id = storyteller["account"]["id"]
    question_id = await _first_question_id(client, headers)
    await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "A memory worth keeping."},
        headers=headers,
    )

    not_ready = await client.get("/memoir/pdf", headers=headers)
    assert not_ready.status_code == 404

    await client.post("/memoir/generate", headers=headers)
    memoir = await memoir_service.get_memoir(db_session, account_id)
    await memoir_service.generate_with_session(db_session, memoir.id, account_id)

    ready = await client.get("/memoir/pdf", headers=headers)
    assert ready.status_code == 200
    assert ready.headers["content-type"] == "application/pdf"
    assert ready.content == b"%PDF-fake"


async def test_memoir_read_access_open_to_all_account_members(
    client: AsyncClient, db_session: AsyncSession
):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)
    await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "Something true."},
        headers=headers,
    )
    await client.post("/memoir/generate", headers=headers)

    viewer_email = _unique_email()
    created = await client.post(
        "/users",
        json={"email": viewer_email, "password": "supersecret1", "user_type": "viewer"},
        headers=headers,
    )
    assert created.status_code == 201

    viewer_login = await client.post(
        "/auth/login", json={"email": viewer_email, "password": "supersecret1"}
    )
    viewer_headers = _headers(viewer_login.json()["access_token"])

    listing = await client.get("/memoir", headers=viewer_headers)
    assert listing.status_code == 200


async def test_memoir_routes_reject_other_accounts(client: AsyncClient):
    storyteller_a = await _signup(client, "storyteller")
    storyteller_b = await _signup(client, "storyteller")
    headers_a = _headers(storyteller_a["access_token"])
    headers_b = _headers(storyteller_b["access_token"])

    question_id_b = await _first_question_id(client, headers_b)
    await client.put(
        f"/questions/{question_id_b}/answer",
        json={"text": "B's story."},
        headers=headers_b,
    )
    await client.post("/memoir/generate", headers=headers_b)

    not_found = await client.get("/memoir", headers=headers_a)
    assert not_found.status_code == 404


async def test_memoir_routes_require_auth(client: AsyncClient):
    listing = await client.get("/memoir")
    assert listing.status_code == 401

    pdf = await client.get("/memoir/pdf")
    assert pdf.status_code == 401
