from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/auth/verify")
async def verify_auth(request: Request):
    return {
        "status": "authenticated",
        "auth_enabled": bool(__import__("os").environ.get("AAA_PASSWORD", "").strip())
    }
