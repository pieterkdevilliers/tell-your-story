import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import MEDIA_ROOT
from app.models.answer import Answer
from app.services import answer_service, transcription_service


@pytest.fixture(autouse=True)
def _fake_transcription(monkeypatch):
    """Every media upload fires a real background transcription job; stub
    the model call so ordinary media tests don't load/download a real
    Whisper model over the network."""

    async def _fake_transcribe(content: bytes) -> str:
        return "fake transcript"

    monkeypatch.setattr(transcription_service, "transcribe", _fake_transcribe)


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


async def _answer_media_path(db_session: AsyncSession, question_id: int) -> str:
    stmt = select(Answer).where(Answer.question_id == question_id)
    answer = (await db_session.execute(stmt)).scalar_one()
    return answer.media_path


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
    assert response.json()["answer_type"] == "text"
    assert response.json()["question_id"] == question_id

    listing = await client.get("/questions", headers=headers)
    question = next(q for q in listing.json() if q["id"] == question_id)
    assert question["answer"]["text"] == "My earliest memory is..."
    assert question["answer"]["answer_type"] == "text"


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


async def test_storyteller_uploads_audio_answer(client: AsyncClient):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)

    response = await client.put(
        f"/questions/{question_id}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"fake-audio-bytes", "audio/webm")},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["answer_type"] == "audio"
    assert response.json()["text"] is None
    assert response.json()["transcription_status"] == "pending"
    assert response.json()["transcript"] is None

    media = await client.get(f"/questions/{question_id}/answer/media", headers=headers)
    assert media.status_code == 200
    assert media.content == b"fake-audio-bytes"
    assert media.headers["content-type"].startswith("audio/webm")


async def test_uploading_video_replaces_existing_audio_answer(
    client: AsyncClient, db_session: AsyncSession
):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)

    audio_response = await client.put(
        f"/questions/{question_id}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
        headers=headers,
    )
    audio_path = Path(MEDIA_ROOT) / (await _answer_media_path(db_session, question_id))
    assert audio_path.exists()

    video_response = await client.put(
        f"/questions/{question_id}/answer/media",
        data={"answer_type": "video"},
        files={"file": ("clip.webm", b"video-bytes", "video/webm")},
        headers=headers,
    )
    assert video_response.status_code == 200
    assert video_response.json()["id"] == audio_response.json()["id"]
    assert video_response.json()["answer_type"] == "video"
    assert video_response.json()["transcription_status"] == "pending"
    assert not audio_path.exists()

    media = await client.get(f"/questions/{question_id}/answer/media", headers=headers)
    assert media.content == b"video-bytes"


async def test_delete_answer_removes_row_and_file(
    client: AsyncClient, db_session: AsyncSession
):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)

    await client.put(
        f"/questions/{question_id}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
        headers=headers,
    )
    media_path = Path(MEDIA_ROOT) / (await _answer_media_path(db_session, question_id))
    assert media_path.exists()

    response = await client.delete(f"/questions/{question_id}/answer", headers=headers)
    assert response.status_code == 204
    assert not media_path.exists()

    media = await client.get(f"/questions/{question_id}/answer/media", headers=headers)
    assert media.status_code == 404

    listing = await client.get("/questions", headers=headers)
    question = next(q for q in listing.json() if q["id"] == question_id)
    assert question["answer"] is None


async def test_media_upload_requires_storyteller(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    headers = _headers(requester["access_token"])
    question_id = await _first_question_id(client, headers)

    response = await client.put(
        f"/questions/{question_id}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
        headers=headers,
    )
    assert response.status_code == 403


async def test_delete_answer_requires_storyteller(client: AsyncClient):
    requester = await _signup(client, "story_requester")
    requester_headers = _headers(requester["access_token"])
    question_id = await _first_question_id(client, requester_headers)

    response = await client.delete(
        f"/questions/{question_id}/answer", headers=requester_headers
    )
    assert response.status_code == 403


async def test_media_routes_require_auth(client: AsyncClient):
    upload = await client.put(
        "/questions/1/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
    )
    assert upload.status_code == 401

    get_media = await client.get("/questions/1/answer/media")
    assert get_media.status_code == 401

    delete = await client.delete("/questions/1/answer")
    assert delete.status_code == 401


async def test_media_routes_reject_other_accounts_question(client: AsyncClient):
    storyteller_a = await _signup(client, "storyteller")
    storyteller_b = await _signup(client, "storyteller")
    headers_a = _headers(storyteller_a["access_token"])
    headers_b = _headers(storyteller_b["access_token"])
    question_id_b = await _first_question_id(client, headers_b)

    upload = await client.put(
        f"/questions/{question_id_b}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
        headers=headers_a,
    )
    assert upload.status_code == 404

    await client.put(
        f"/questions/{question_id_b}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
        headers=headers_b,
    )

    get_media = await client.get(
        f"/questions/{question_id_b}/answer/media", headers=headers_a
    )
    assert get_media.status_code == 404

    delete = await client.delete(
        f"/questions/{question_id_b}/answer", headers=headers_a
    )
    assert delete.status_code == 404


async def test_transcribe_answer_completes_and_stores_transcript(
    client: AsyncClient, db_session: AsyncSession
):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)

    upload = await client.put(
        f"/questions/{question_id}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
        headers=headers,
    )
    answer_id = upload.json()["id"]
    media_path = await _answer_media_path(db_session, question_id)

    await answer_service.transcribe_answer(
        db_session, answer_id, media_path, b"audio-bytes"
    )

    listing = await client.get("/questions", headers=headers)
    question = next(q for q in listing.json() if q["id"] == question_id)
    assert question["answer"]["transcription_status"] == "completed"
    assert question["answer"]["transcript"] == "fake transcript"


async def test_transcribe_answer_ignores_stale_media_path(
    client: AsyncClient, db_session: AsyncSession
):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)

    first_upload = await client.put(
        f"/questions/{question_id}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"first-bytes", "audio/webm")},
        headers=headers,
    )
    answer_id = first_upload.json()["id"]
    stale_media_path = await _answer_media_path(db_session, question_id)

    # Re-record before the (simulated) slow first transcription job finishes.
    await client.put(
        f"/questions/{question_id}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"second-bytes", "audio/webm")},
        headers=headers,
    )
    assert await _answer_media_path(db_session, question_id) != stale_media_path

    # The stale job (still keyed to the first upload's media_path) finishes
    # late and must not clobber the second upload's pending status.
    await answer_service.transcribe_answer(
        db_session, answer_id, stale_media_path, b"first-bytes"
    )

    listing = await client.get("/questions", headers=headers)
    question = next(q for q in listing.json() if q["id"] == question_id)
    assert question["answer"]["transcription_status"] == "pending"
    assert question["answer"]["transcript"] is None


async def test_upsert_text_answer_clears_transcript_fields(
    client: AsyncClient, db_session: AsyncSession
):
    storyteller = await _signup(client, "storyteller")
    headers = _headers(storyteller["access_token"])
    question_id = await _first_question_id(client, headers)

    upload = await client.put(
        f"/questions/{question_id}/answer/media",
        data={"answer_type": "audio"},
        files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
        headers=headers,
    )
    answer_id = upload.json()["id"]
    media_path = await _answer_media_path(db_session, question_id)
    await answer_service.transcribe_answer(
        db_session, answer_id, media_path, b"audio-bytes"
    )

    response = await client.put(
        f"/questions/{question_id}/answer",
        json={"text": "Switched to text"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["transcript"] is None
    assert response.json()["transcription_status"] is None
