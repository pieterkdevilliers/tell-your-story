import io

import pytest

from app.services import storage_service


class _FakeS3Client:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_object(self, Bucket, Key, Body):
        assert Bucket == "test-bucket"
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        assert Bucket == "test-bucket"
        return {"Body": io.BytesIO(self.objects[Key])}

    def delete_object(self, Bucket, Key):
        assert Bucket == "test-bucket"
        self.objects.pop(Key, None)


@pytest.fixture
def fake_s3(monkeypatch):
    client = _FakeS3Client()
    monkeypatch.setattr(storage_service, "S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(storage_service, "_s3_client", lambda: client)
    return client


@pytest.mark.asyncio
async def test_save_and_read_media_round_trips_through_s3(fake_s3):
    storage_key = await storage_service.save_media(
        account_id=1, question_id=2, content=b"hello", extension="mp3"
    )

    assert storage_key in fake_s3.objects
    assert await storage_service.read_media(storage_key) == b"hello"


@pytest.mark.asyncio
async def test_save_pdf_and_cover_photo_use_stable_keys(fake_s3):
    pdf_key = await storage_service.save_pdf(account_id=1, content=b"%PDF-1.4")
    photo_key = await storage_service.save_cover_photo(
        account_id=1, content=b"jpg-bytes", extension="jpg"
    )

    assert pdf_key == "1/memoir.pdf"
    assert photo_key == "1/cover.jpg"
    assert await storage_service.read_media(pdf_key) == b"%PDF-1.4"
    assert await storage_service.read_media(photo_key) == b"jpg-bytes"


@pytest.mark.asyncio
async def test_delete_media_removes_object_from_s3(fake_s3):
    storage_key = await storage_service.save_media(
        account_id=1, question_id=2, content=b"hello", extension="mp3"
    )

    await storage_service.delete_media(storage_key)

    assert storage_key not in fake_s3.objects


@pytest.mark.asyncio
async def test_delete_media_on_missing_key_does_not_raise(fake_s3):
    await storage_service.delete_media("1/does-not-exist.mp3")
