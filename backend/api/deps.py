import logging
import os
from typing import Optional

from fastapi import Header, HTTPException, Request

logger = logging.getLogger(__name__)

AAA_PASSWORD = os.environ.get("AAA_PASSWORD", "").strip()


async def verify_password(authorization: Optional[str] = Header(None)):
    if not AAA_PASSWORD:
        return

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = None
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    if token != AAA_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
