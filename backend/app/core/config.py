import os

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3014").split(",")
    if origin.strip()
]

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3014")
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "60")
)
# Invites sit unread far longer than password resets, so they get a much
# longer default lifetime (7 days) rather than reusing the reset window.
INVITE_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("INVITE_TOKEN_EXPIRE_MINUTES", "10080")
)

# Optional: if unset, the email service logs reset emails instead of
# sending them via SES. AWS credentials themselves are not read here —
# boto3's default credential chain picks up AWS_ACCESS_KEY_ID /
# AWS_SECRET_ACCESS_KEY / AWS_REGION from the environment automatically.
SES_FROM_EMAIL = os.environ.get("SES_FROM_EMAIL")
AWS_REGION = os.environ.get("AWS_REGION")

# Local disk path for recorded answer media (audio/video), used whenever
# S3_BUCKET_NAME is unset. See app/services/storage_service.py.
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", "./media")

# Optional: if unset, storage_service reads/writes media (answers, memoir
# PDFs, cover photos) on local disk under MEDIA_ROOT. Set it to switch to
# S3 — credentials/region are the same AWS_REGION / AWS_ACCESS_KEY_ID /
# AWS_SECRET_ACCESS_KEY already used for SES above, read automatically by
# boto3's standard credential chain.
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

# Local Whisper model size used for audio/video transcription. Swappable for
# a cloud STT provider later — see app/services/transcription_service.py.
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")
