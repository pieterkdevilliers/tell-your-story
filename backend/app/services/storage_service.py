import uuid
from pathlib import Path

import boto3
from starlette.concurrency import run_in_threadpool

from app.core.config import AWS_REGION, MEDIA_ROOT, S3_BUCKET_NAME


def extension_from_content_type(content_type: str) -> str:
    base = content_type.split(";")[0].strip()
    return base.split("/")[-1] or "bin"


def _resolve(storage_key: str) -> Path:
    return Path(MEDIA_ROOT) / storage_key


def _s3_client():
    if AWS_REGION:
        return boto3.client("s3", region_name=AWS_REGION)
    return boto3.client("s3")


async def _write(storage_key: str, content: bytes) -> None:
    """Writes `content` under `storage_key`, to S3 if S3_BUCKET_NAME is
    set, otherwise to local disk under MEDIA_ROOT. This (plus read/delete
    below) is the only place in the app that knows where files actually
    live — everything else just deals in storage_key strings.
    """
    if S3_BUCKET_NAME:
        await run_in_threadpool(
            _s3_client().put_object,
            Bucket=S3_BUCKET_NAME,
            Key=storage_key,
            Body=content,
        )
        return

    path = _resolve(storage_key)

    def _write_local() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    await run_in_threadpool(_write_local)


async def save_media(
    account_id: int, question_id: int, content: bytes, extension: str
) -> str:
    filename = f"{question_id}-{uuid.uuid4().hex}.{extension}"
    storage_key = f"{account_id}/{filename}"
    await _write(storage_key, content)
    return storage_key


async def save_pdf(account_id: int, content: bytes) -> str:
    """Always the same key per account — regenerating a memoir overwrites
    the previous PDF in place, so unlike save_media there's no prior file
    to separately delete.
    """
    storage_key = f"{account_id}/memoir.pdf"
    await _write(storage_key, content)
    return storage_key


async def save_cover_photo(account_id: int, content: bytes, extension: str) -> str:
    """Same shape as save_pdf — always the same base filename per account,
    so a later re-upload simply overwrites it.
    """
    storage_key = f"{account_id}/cover.{extension}"
    await _write(storage_key, content)
    return storage_key


async def read_media(storage_key: str) -> bytes:
    if S3_BUCKET_NAME:

        def _get() -> bytes:
            response = _s3_client().get_object(Bucket=S3_BUCKET_NAME, Key=storage_key)
            return response["Body"].read()

        return await run_in_threadpool(_get)

    return await run_in_threadpool(_resolve(storage_key).read_bytes)


async def delete_media(storage_key: str) -> None:
    if S3_BUCKET_NAME:
        await run_in_threadpool(
            _s3_client().delete_object, Bucket=S3_BUCKET_NAME, Key=storage_key
        )
        return

    def _delete() -> None:
        _resolve(storage_key).unlink(missing_ok=True)

    await run_in_threadpool(_delete)
