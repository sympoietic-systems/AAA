import asyncio

from fastapi import APIRouter, Header, HTTPException, Request, Response

from backend.api.deps import get_session_store, require_session_origin
from backend.api.schemas import AuthStatusResponse
from backend.core.auth import auth_enabled, bearer_token, credentials_valid
from backend.core.sessions import SESSION_COOKIE

router = APIRouter()


def _is_secure_request(request: Request) -> bool:
    """Determine if the request transport is HTTPS.

    A cookie marked 'Secure' will be rejected by browsers if received over
    unencrypted HTTP (RFC 6265bis). Only mark the cookie as Secure when the
    connection is actually HTTPS or terminated as HTTPS by an upstream proxy.
    """
    if request.url.scheme == "https":
        return True
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    return forwarded_proto == "https"


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
        authorization is None
        and await asyncio.to_thread(get_session_store(request).valid, request.cookies.get(SESSION_COOKIE))
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
        await asyncio.to_thread(store.revoke, request.cookies.get(SESSION_COOKIE))
        token = await asyncio.to_thread(store.issue)
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=store.ttl,
            httponly=True,
            secure=_is_secure_request(request),
            samesite="strict",
            path="/api",
        )
    return {"status": "authenticated", "auth_enabled": auth_enabled()}


@router.delete("/auth/session", response_model=AuthStatusResponse)
async def delete_session(request: Request, response: Response) -> dict[str, str | bool]:
    require_session_origin(request)
    await asyncio.to_thread(get_session_store(request).revoke, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(
        SESSION_COOKIE,
        path="/api",
        httponly=True,
        samesite="strict",
        secure=_is_secure_request(request),
    )
    response.headers["Cache-Control"] = "no-store"
    return {"status": "unauthenticated", "auth_enabled": auth_enabled()}
