from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, users
from app.core.config import CORS_ORIGINS

app = FastAPI(title="Daily Tasks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
