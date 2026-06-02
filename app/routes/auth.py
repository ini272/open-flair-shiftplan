from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies import get_auth_session, get_tracer
from app.schemas.auth import AuthCheckResponse, LoginRequest, LoginResponse
from app.security import AuthSession, clear_auth_session_cookie, get_role_for_access_code, set_auth_session_cookie


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)

tracer = get_tracer()


@router.post("/login", response_model=LoginResponse)
def login_with_access_code(
    login_data: LoginRequest,
    response: Response,
) -> Any:
    """
    Login with the shared event code or the separate coordinator code.
    """
    with tracer.start_as_current_span("login-with-access-code") as span:
        span.set_attribute("login.attempt", True)

        role = get_role_for_access_code(login_data.access_code)
        if role is None:
            span.add_event("access_code_validation_failed")
            span.set_attribute("error", "Invalid access code")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access code",
            )

        set_auth_session_cookie(response, role=role)

        span.add_event("access_code_validated_successfully")
        span.set_attribute("login.success", True)
        span.set_attribute("login.role", role)
        return {
            "authenticated": True,
            "role": role,
            "user_id": None,
            "message": "Login successful",
        }


@router.get("/logout")
def logout(response: Response) -> Any:
    """
    Logout by clearing the signed session cookie.
    """
    with tracer.start_as_current_span("logout") as span:
        clear_auth_session_cookie(response)
        span.set_attribute("logout.success", True)
        return {"message": "Logout successful"}


@router.get("/check", response_model=AuthCheckResponse)
def check_auth(
    auth_session: Optional[AuthSession] = Depends(get_auth_session),
) -> Any:
    """
    Check if the current browser has a valid signed access-code session.
    """
    with tracer.start_as_current_span("check-auth") as span:
        if not auth_session:
            span.set_attribute("auth.status", "no_session")
            return {"authenticated": False, "role": None, "user_id": None}

        span.set_attribute("auth.status", "valid")
        span.set_attribute("auth.role", auth_session.role)
        return {
            "authenticated": True,
            "role": auth_session.role,
            "user_id": auth_session.user_id,
        }


@router.get("/login/{_legacy_token}", status_code=status.HTTP_410_GONE)
def legacy_login_with_token(_legacy_token: str) -> Any:
    """
    Token login links are intentionally retired.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Token login links are no longer supported. Please use the event access code.",
    )


@router.get("/token/{_legacy_token}", status_code=status.HTTP_410_GONE)
def legacy_validate_token(_legacy_token: str) -> Any:
    """
    Token validation links are intentionally retired.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Token login links are no longer supported. Please use the event access code.",
    )
