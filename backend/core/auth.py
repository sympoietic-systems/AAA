"""Central authentication configuration and constant-time credential checks."""

import os
import secrets


def get_auth_password() -> str:
    return os.environ.get("AAA_PASSWORD", "").strip()


def auth_enabled() -> bool:
    return bool(get_auth_password())


def bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    return token or None


def credentials_valid(token: str | None) -> bool:
    password = get_auth_password()
    if not password or token is None:
        return False
    return secrets.compare_digest(token.encode("utf-8"), password.encode("utf-8"))
