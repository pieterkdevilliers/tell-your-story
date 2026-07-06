import uuid
from pathlib import Path

from starlette.concurrency import run_in_threadpool

from app.core.config import MEDIA_ROOT


def extension_from_content_type(content_type: str) -> str:
    base = content_type.split(";")[0].strip()
    return base.split("/")[-1] or "bin"


def _resolve(storage_key: str) -> Path:
    return Path(MEDIA_ROOT) / storage_key


async def save_media(
    account_id: int, question_id: int, content: bytes, extension: str
) -> str:
    """Writes `content` to local disk and returns its storage key.

    This is the only function in the app that knows the on-disk layout —
    swapping to S3 later means rewriting save/read/delete here, nothing
    else in the app touches the filesystem directly.
    """
    account_dir = Path(MEDIA_ROOT) / str(account_id)
    filename = f"{question_id}-{uuid.uuid4().hex}.{extension}"
    storage_key = f"{account_id}/{filename}"

    def _write() -> None:
        account_dir.mkdir(parents=True, exist_ok=True)
        (account_dir / filename).write_bytes(content)

    await run_in_threadpool(_write)
    return storage_key


async def save_pdf(account_id: int, content: bytes) -> str:
    """Writes the account's memoir PDF to local disk and returns its
    storage key. Always the same key per account — regenerating a memoir
    overwrites the previous PDF in place, so unlike save_media there's no
    prior file to separately delete.
    """
    account_dir = Path(MEDIA_ROOT) / str(account_id)
    filename = "memoir.pdf"
    storage_key = f"{account_id}/{filename}"

    def _write() -> None:
        account_dir.mkdir(parents=True, exist_ok=True)
        (account_dir / filename).write_bytes(content)

    await run_in_threadpool(_write)
    return storage_key


async def save_cover_photo(account_id: int, content: bytes, extension: str) -> str:
    """Writes the account's memoir cover photo to local disk and returns
    its storage key. Same shape as save_pdf — always the same base
    filename per account, so a later re-upload simply overwrites it.
    """
    account_dir = Path(MEDIA_ROOT) / str(account_id)
    filename = f"cover.{extension}"
    storage_key = f"{account_id}/{filename}"

    def _write() -> None:
        account_dir.mkdir(parents=True, exist_ok=True)
        (account_dir / filename).write_bytes(content)

    await run_in_threadpool(_write)
    return storage_key


async def read_media(storage_key: str) -> bytes:
    return await run_in_threadpool(_resolve(storage_key).read_bytes)


async def delete_media(storage_key: str) -> None:
    def _delete() -> None:
        _resolve(storage_key).unlink(missing_ok=True)

    await run_in_threadpool(_delete)
