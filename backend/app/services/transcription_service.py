import io
from functools import lru_cache

from starlette.concurrency import run_in_threadpool

from app.core.config import WHISPER_MODEL_SIZE


@lru_cache(maxsize=1)
def _get_model():
    from faster_whisper import WhisperModel

    return WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def _transcribe_sync(content: bytes) -> str:
    segments, _ = _get_model().transcribe(io.BytesIO(content))
    return " ".join(segment.text.strip() for segment in segments).strip()


async def transcribe(content: bytes) -> str:
    """Transcribes audio/video bytes to text using a local Whisper model.

    The only function that knows *how* transcription happens — swapping to
    a cloud STT provider later means rewriting this function, nothing else
    in the app touches it directly (mirrors app/services/storage_service.py).
    """
    return await run_in_threadpool(_transcribe_sync, content)
