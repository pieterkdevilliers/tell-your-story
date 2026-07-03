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

# Optional: if unset, the email service logs reset emails instead of
# sending them via SES. AWS credentials themselves are not read here —
# boto3's default credential chain picks up AWS_ACCESS_KEY_ID /
# AWS_SECRET_ACCESS_KEY / AWS_REGION from the environment automatically.
SES_FROM_EMAIL = os.environ.get("SES_FROM_EMAIL")
AWS_REGION = os.environ.get("AWS_REGION")
