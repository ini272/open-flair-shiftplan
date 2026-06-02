from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.crud.user import user as user_crud
from app.crud.group import group as group_crud
from app.security import AuthSession, SESSION_COOKIE_NAME, read_auth_session
from app.tracing import NoopTracer

def get_tracer():
    """
    Returns the application tracer.

    Tracing is currently intentionally disabled for the home-server prototype,
    but route code still uses span calls for structured instrumentation.
    """
    return NoopTracer()

def get_auth_session(
    session_cookie: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
) -> Optional[AuthSession]:
    return read_auth_session(session_cookie)


def require_auth(
    auth_session: Optional[AuthSession] = Depends(get_auth_session),
) -> AuthSession:
    """
    Require a valid signed access-code session.
    """
    if not auth_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    return auth_session


def require_coordinator(
    auth_session: AuthSession = Depends(require_auth),
) -> AuthSession:
    """
    Require that the current session was created with the coordinator access code.
    """
    if not auth_session.is_coordinator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coordinator access required",
        )

    return auth_session


def ensure_self_or_coordinator(auth_session: AuthSession, user_id: int) -> None:
    if auth_session.is_coordinator or auth_session.user_id == user_id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not allowed for this user",
    )


def ensure_group_member_or_coordinator(
    db: Session,
    auth_session: AuthSession,
    group_id: int,
) -> None:
    if auth_session.is_coordinator:
        return

    if auth_session.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed for this group",
        )

    current_user = user_crud.get(db, id=auth_session.user_id)
    if current_user and current_user.group_id == group_id:
        return

    group = group_crud.get(db, id=group_id)
    if group and any(user.id == auth_session.user_id for user in group.users):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not allowed for this group",
    )
