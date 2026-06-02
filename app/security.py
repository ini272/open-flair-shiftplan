import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import Response


SESSION_COOKIE_NAME = "shiftplan_session"
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(30 * 24 * 60 * 60)))

ENVIRONMENT = os.getenv("NODE_ENV", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

SESSION_SECRET = os.getenv("SESSION_SECRET_KEY") or os.getenv("SECRET_KEY")
if IS_PRODUCTION and not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET_KEY or SECRET_KEY must be set in production")
if not SESSION_SECRET:
    SESSION_SECRET = "dev-only-open-flair-shiftplan-session-secret"

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true" if IS_PRODUCTION else "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()


@dataclass(frozen=True)
class AuthSession:
    role: str
    user_id: Optional[int] = None

    @property
    def is_coordinator(self) -> bool:
        return self.role == "coordinator"


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _urlsafe_b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def _sign(payload: str) -> str:
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _urlsafe_b64encode(signature)


def _encode_session(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_part = _urlsafe_b64encode(payload_json)
    return f"{payload_part}.{_sign(payload_part)}"


def _decode_session(cookie_value: str) -> Optional[dict[str, Any]]:
    try:
        payload_part, signature_part = cookie_value.split(".", 1)
    except ValueError:
        return None

    if not hmac.compare_digest(_sign(payload_part), signature_part):
        return None

    try:
        payload = json.loads(_urlsafe_b64decode(payload_part))
    except (ValueError, json.JSONDecodeError):
        return None

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(time.time()):
        return None

    role = payload.get("role")
    if role not in {"participant", "coordinator"}:
        return None

    user_id = payload.get("user_id")
    if user_id is not None and not isinstance(user_id, int):
        return None

    return payload


def read_auth_session(cookie_value: Optional[str]) -> Optional[AuthSession]:
    if not cookie_value:
        return None

    payload = _decode_session(cookie_value)
    if not payload:
        return None

    return AuthSession(role=payload["role"], user_id=payload.get("user_id"))


def set_auth_session_cookie(
    response: Response,
    *,
    role: str,
    user_id: Optional[int] = None,
) -> None:
    now = int(time.time())
    payload = {
        "role": role,
        "iat": now,
        "exp": now + SESSION_MAX_AGE_SECONDS,
    }
    if user_id is not None:
        payload["user_id"] = user_id

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=_encode_session(payload),
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )


def clear_auth_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


def normalize_access_code(access_code: str) -> str:
    return access_code.strip().lower()


def _get_configured_code(env_name: str, development_default: str) -> str:
    configured_code = os.getenv(env_name)
    if IS_PRODUCTION and not configured_code:
        raise RuntimeError(f"{env_name} must be set in production")
    return configured_code or development_default


def get_role_for_access_code(access_code: str) -> Optional[str]:
    candidate = normalize_access_code(access_code)
    if not candidate:
        return None

    event_code = normalize_access_code(_get_configured_code("EVENT_CODE", "weinzelt2026"))
    coordinator_code = normalize_access_code(
        _get_configured_code("COORDINATOR_CODE", "koordination2026")
    )

    if event_code == coordinator_code:
        raise RuntimeError("EVENT_CODE and COORDINATOR_CODE must be different")

    if hmac.compare_digest(candidate, coordinator_code):
        return "coordinator"
    if hmac.compare_digest(candidate, event_code):
        return "participant"
    return None
