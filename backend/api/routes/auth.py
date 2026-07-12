import os

from fastapi import APIRouter, Header, Request

router = APIRouter()

_AAA_PASSWORD = os.environ.get("AAA_PASSWORD", "").strip()


@router.get("/auth/verify")
async def verify_auth(
    request: Request,
    authorization: str | None = Header(None),
):
    auth_enabled = bool(_AAA_PASSWORD)

    if not auth_enabled:
        return {"status": "authenticated", "auth_enabled": False}

    # Check if a valid password was provided
    token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if token == _AAA_PASSWORD:
        return {"status": "authenticated", "auth_enabled": True}

    return {"status": "unauthenticated", "auth_enabled": True}
