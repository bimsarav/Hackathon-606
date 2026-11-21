"""Demo authentication (ADR 0004): roles OCC, PCU (decision Q19) and EVALUATOR (sees everything; see evaluator_only).

Users come from the DEMO_USERS secret ("user:password:role,..."), set only in the server .env. Tokens are
HMAC-SHA256-signed, expiring bearer tokens (stdlib only). This is a demo control, not an identity provider:
production uses the airline's OIDC provider (ADR 0004, later phase).
"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings

ROLES = frozenset({"OCC", "PCU", "EVALUATOR"})
EVALUATOR = "EVALUATOR"  # sees every view; the other roles do not see the Model and Test data views
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class User:
    username: str
    role: str


def _users(settings: Settings) -> dict[str, tuple[str, str]]:
    users: dict[str, tuple[str, str]] = {}
    for entry in settings.demo_users.get_secret_value().split(","):
        parts = entry.strip().split(":")
        if len(parts) == 3 and parts[2].upper() in ROLES:
            users[parts[0]] = (parts[1], parts[2].upper())
    return users


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _sign(settings: Settings, payload: str) -> str:
    secret = settings.token_secret.get_secret_value().encode()
    return _b64(hmac.new(secret, payload.encode(), hashlib.sha256).digest())


def authenticate(settings: Settings, username: str, password: str) -> User | None:
    known = _users(settings).get(username)
    if known is None or not settings.token_secret.get_secret_value():
        hmac.compare_digest(password, "timing-equaliser")
        return None
    if not hmac.compare_digest(password.encode(), known[0].encode()):
        return None
    return User(username, known[1])


def issue_token(settings: Settings, user: User) -> tuple[str, int]:
    expires = int(time.time()) + settings.token_ttl_hours * 3600
    payload = _b64(json.dumps({"u": user.username, "r": user.role, "exp": expires}).encode())
    return f"{payload}.{_sign(settings, payload)}", expires


def verify_token(settings: Settings, token: str) -> User | None:
    try:
        payload, signature = token.split(".", 1)
    except ValueError:
        return None
    if not settings.token_secret.get_secret_value() or not hmac.compare_digest(signature, _sign(settings, payload)):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except ValueError:
        return None
    if int(data.get("exp", 0)) < time.time() or data.get("r") not in ROLES:
        return None
    return User(str(data["u"]), str(data["r"]))


def current_user(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    user = verify_token(request.app.state.settings, credentials.credentials) if credentials else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required", headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def evaluator_only(user: CurrentUser) -> User:
    """The Model and Test data views (and their endpoints) are for the evaluator role."""
    if user.role != EVALUATOR:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This view is for the evaluator role")
    return user


EvaluatorUser = Annotated[User, Depends(evaluator_only)]
