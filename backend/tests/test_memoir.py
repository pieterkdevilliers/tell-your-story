import io
import uuid

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import llm_service, memoir_service


def _tiny_png(color: tuple[int, int, int] = (200, 50, 50)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def _tiny_jpg(color: tuple[int, int, int] = (50, 50, 200)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color=color).save(buffer, format="JPEG")
    return buffer.getvalue()


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
def _fake_llm(monkeypatch):
    """POST /memoir/generate fires a real background job; stub the Claude
    call so ordinary tests never hit the real API. PDF rendering is fast,
    local reportlab work with no external call, so it's left real."""

    async def _fake_generate_text(account_name, entries):
        return "# Fake Memoir\n\n## Chapter\n\nSome generated prose."

    monkeypatch.setattr(llm_service, "generate_memoir_text", _fake_generate_text)


async def _generate_draft(
    client: AsyncClient, db_session: AsyncSession, headers: dict, account_id: int
) -> None:
    """Triggers draft generation via the API, then drives the background
    job directly against db_session (see generate_draft_with_session's
    docstring for why: the real background task opens its own session,
    which can't see the test's in-memory database)."""
    trigger = await client.post("/memoir/generate", headers=headers)
    assert trigger.status_code == 200
    memoir = await memoir_service.get_memoir(db_session, account_id)
    await memoir_service.generate_draft_with_session(db_session, memoir.id, account_id)


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


async def test_draft_generation_lands_on_draft_ready_with_no_pdf_yet(
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

    await _generate_draft(client, db_session, headers, account_id)

    listing = await client.get("/memoir", headers=headers)
    assert listing.json()["status"] == "draft_ready"
    assert listing.json()["content"] == (
        "# Fake Memoir\n\n## Chapter\n\nSome generated prose."
    )

    not_ready = await client.get("/memoir/pdf", headers=headers)
    assert not_ready.status_code == 404


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
    await memoir_service.generate_draft_with_session(db_session, memoir.id, account_id)

    assert len(captured["entries"]) == 1
    assert captured["entries"][0][2] == "I was born in a small town."


async def test_update_content_requires_existing_memoir(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])

    response = await client.put(
        "/memoir", json={"content": "Nothing to edit yet"}, headers=headers
    )
    assert response.status_code == 404


async def test_update_content_requires_draft_to_exist(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)
    await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "A memory worth keeping."},
        headers=headers,
    )
    # Triggers generation, but the real background task writes its result
    # through its own session (pointed at a different DB in tests — see
    # generate_draft's docstring), so from db_session's point of view the
    # row stays "pending" with no content, same as if it were still queued.
    await client.post("/memoir/generate", headers=headers)

    response = await client.put(
        "/memoir", json={"content": "Too soon"}, headers=headers
    )
    assert response.status_code == 400


async def test_update_content_requires_storyteller(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    response = await client.put(
        "/memoir", json={"content": "Sneaky edit"}, headers=headers
    )
    assert response.status_code == 403


async def test_update_content_edits_draft_and_invalidates_completed_pdf(
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
    await _generate_draft(client, db_session, headers, account_id)

    render = await client.post("/memoir/render", headers=headers)
    assert render.status_code == 200
    assert render.json()["status"] == "completed"
    assert (await client.get("/memoir/pdf", headers=headers)).status_code == 200

    edited = await client.put(
        "/memoir", json={"content": "Corrected wording."}, headers=headers
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "draft_ready"
    assert edited.json()["content"] == "Corrected wording."

    # The old PDF no longer matches the (now-edited) content.
    stale = await client.get("/memoir/pdf", headers=headers)
    assert stale.status_code == 404


async def test_render_requires_existing_memoir(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])

    response = await client.post("/memoir/render", headers=headers)
    assert response.status_code == 404


async def test_render_requires_draft_to_exist(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)
    await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "A memory worth keeping."},
        headers=headers,
    )
    await client.post("/memoir/generate", headers=headers)

    response = await client.post("/memoir/render", headers=headers)
    assert response.status_code == 400


async def test_render_requires_storyteller(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    response = await client.post("/memoir/render", headers=headers)
    assert response.status_code == 403


async def test_render_produces_real_pdf_with_and_without_cover_photo(
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
    await _generate_draft(client, db_session, headers, account_id)

    render_without_photo = await client.post("/memoir/render", headers=headers)
    assert render_without_photo.status_code == 200
    pdf_without_photo = await client.get("/memoir/pdf", headers=headers)
    assert pdf_without_photo.content.startswith(b"%PDF")

    photo_upload = await client.put(
        "/memoir/photo",
        files={"file": ("cover.png", _tiny_png(), "image/png")},
        headers=headers,
    )
    assert photo_upload.status_code == 200
    assert photo_upload.json()["has_cover_photo"] is True
    # Uploading a photo onto an already-completed memoir invalidates the PDF.
    assert photo_upload.json()["status"] == "draft_ready"

    render_with_photo = await client.post("/memoir/render", headers=headers)
    assert render_with_photo.status_code == 200
    pdf_with_photo = await client.get("/memoir/pdf", headers=headers)
    assert pdf_with_photo.content.startswith(b"%PDF")
    assert pdf_with_photo.content != pdf_without_photo.content


async def test_cover_photo_upload_download_delete_round_trip(
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
    await _generate_draft(client, db_session, headers, account_id)

    first_photo = _tiny_png()
    upload = await client.put(
        "/memoir/photo",
        files={"file": ("cover.png", first_photo, "image/png")},
        headers=headers,
    )
    assert upload.status_code == 200
    assert upload.json()["has_cover_photo"] is True

    download = await client.get("/memoir/photo", headers=headers)
    assert download.status_code == 200
    assert download.content == first_photo
    assert download.headers["content-type"] == "image/png"

    # Replacing it removes the old file (no orphaned photo left behind).
    second_photo = _tiny_jpg()
    replaced = await client.put(
        "/memoir/photo",
        files={"file": ("cover.jpg", second_photo, "image/jpeg")},
        headers=headers,
    )
    assert replaced.status_code == 200
    redownload = await client.get("/memoir/photo", headers=headers)
    assert redownload.content == second_photo
    assert redownload.headers["content-type"] == "image/jpeg"

    deleted = await client.delete("/memoir/photo", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["has_cover_photo"] is False

    gone = await client.get("/memoir/photo", headers=headers)
    assert gone.status_code == 404


async def test_cover_photo_requires_existing_memoir(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])

    upload = await client.put(
        "/memoir/photo",
        files={"file": ("cover.png", _tiny_png(), "image/png")},
        headers=headers,
    )
    assert upload.status_code == 404

    download = await client.get("/memoir/photo", headers=headers)
    assert download.status_code == 404


async def test_cover_photo_rejects_non_image_upload(
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
    await _generate_draft(client, db_session, headers, account_id)

    response = await client.put(
        "/memoir/photo",
        files={"file": ("notes.txt", b"not a photo", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 422


async def test_cover_photo_rejects_undecodable_image_bytes(
    client: AsyncClient, db_session: AsyncSession
):
    """A file claiming to be an image via content-type, but whose bytes
    aren't actually decodable, must be rejected cleanly at upload time —
    not accepted and left to crash later when /memoir/render tries to
    decode it for the PDF.
    """
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    account_id = storyteller["account"]["id"]
    question_id = await _first_question_id(client, headers)
    await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "A memory worth keeping."},
        headers=headers,
    )
    await _generate_draft(client, db_session, headers, account_id)

    response = await client.put(
        "/memoir/photo",
        files={"file": ("cover.png", b"not-actually-a-png", "image/png")},
        headers=headers,
    )
    assert response.status_code == 422


async def test_cover_photo_upload_requires_storyteller(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    response = await client.put(
        "/memoir/photo",
        files={"file": ("cover.png", _tiny_png(), "image/png")},
        headers=headers,
    )
    assert response.status_code == 403


async def test_cover_photo_delete_requires_storyteller(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])

    response = await client.delete("/memoir/photo", headers=headers)
    assert response.status_code == 403


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
