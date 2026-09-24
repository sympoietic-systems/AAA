from fastapi import APIRouter, Header

from backend.core.auth import auth_enabled, bearer_token, credentials_valid

router = APIRouter()


@router.get("/auth/verify")
async def verify_auth(
    authorization: str | None = Header(None),
):
    enabled = auth_enabled()
    if not enabled:
        return {"status": "authenticated", "auth_enabled": False}

    if credentials_valid(bearer_token(authorization)):
        return {"status": "authenticated", "auth_enabled": True}

    return {"status": "unauthenticated", "auth_enabled": True}
