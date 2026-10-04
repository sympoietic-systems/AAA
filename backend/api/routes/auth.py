from fastapi import APIRouter, Header, HTTPException, Request, Response

from backend.api.deps import get_session_store, require_session_origin
from backend.api.schemas import AuthStatusResponse
from backend.core.auth import auth_enabled, bearer_token, credentials_valid
from backend.core.sessions import SESSION_COOKIE

router = APIRouter()


@router.get("/auth/verify", response_model=AuthStatusResponse)
async def verify_auth(
    request: Request,
    response: Response,
    authorization: str | None = Header(None),
) -> dict[str, str | bool]:
    response.headers["Cache-Control"] = "no-store"
    enabled = auth_enabled()
    if not enabled:
        return {"status": "authenticated", "auth_enabled": False}

    if credentials_valid(bearer_token(authorization)) or (
        authorization is None and get_session_store(request).valid(request.cookies.get(SESSION_COOKIE))
    ):
        return {"status": "authenticated", "auth_enabled": True}

    return {"status": "unauthenticated", "auth_enabled": True}


@router.post("/auth/session", response_model=AuthStatusResponse)
async def create_session(
    request: Request, response: Response, authorization: str | None = Header(None)
) -> dict[str, str | bool]:
    require_session_origin(request)
    if auth_enabled() and not credentials_valid(bearer_token(authorization)):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    response.headers["Cache-Control"] = "no-store"
    if auth_enabled():
        store = get_session_store(request)
        store.revoke(request.cookies.get(SESSION_COOKIE))
        response.set_cookie(
            SESSION_COOKIE,
            store.issue(),
            max_age=store.ttl,
            httponly=True,
            secure=request.url.scheme == "https" or request.url.hostname not in {"localhost", "127.0.0.1", "::1"},
            samesite="strict",
            path="/api",
        )
    return {"status": "authenticated", "auth_enabled": auth_enabled()}


@router.delete("/auth/session", response_model=AuthStatusResponse)
async def delete_session(request: Request, response: Response) -> dict[str, str | bool]:
    require_session_origin(request)
    get_session_store(request).revoke(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/api", httponly=True, samesite="strict")
    response.headers["Cache-Control"] = "no-store"
    return {"status": "unauthenticated", "auth_enabled": auth_enabled()}
