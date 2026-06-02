from app.security import SESSION_COOKIE_NAME


def test_login_with_event_code(client):
    """Test logging in with the participant event code."""
    response = client.post("/auth/login", json={"access_code": "weinzelt2026"})

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.json()["role"] == "participant"
    assert SESSION_COOKIE_NAME in response.cookies


def test_login_with_coordinator_code(client):
    """Test logging in with the coordinator access code."""
    response = client.post("/auth/login", json={"access_code": "koordination2026"})

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.json()["role"] == "coordinator"
    assert SESSION_COOKIE_NAME in response.cookies


def test_login_with_invalid_access_code(client):
    """Test logging in with an invalid access code."""
    response = client.post("/auth/login", json={"access_code": "invalid-code"})
    assert response.status_code == 401


def test_check_auth_authenticated(authenticated_client):
    """Test checking authentication when authenticated."""
    response = authenticated_client.get("/auth/check")

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.json()["role"] == "coordinator"


def test_check_auth_unauthenticated(client):
    """Test checking authentication when unauthenticated."""
    response = client.get("/auth/check")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    assert response.json()["role"] is None


def test_logout(authenticated_client):
    """Test logging out."""
    response = authenticated_client.get("/auth/logout")

    assert response.status_code == 200
    assert "Set-Cookie" in response.headers

    cookie_header = response.headers["Set-Cookie"]
    assert f"{SESSION_COOKIE_NAME}=" in cookie_header
    assert "Max-Age=0" in cookie_header or "expires=" in cookie_header.lower()


def test_legacy_token_login_is_gone(client):
    """Test old token login links are explicitly retired."""
    response = client.get("/auth/login/old-token")
    assert response.status_code == 410


def test_legacy_token_validation_is_gone(client):
    """Test old token validation links are explicitly retired."""
    response = client.get("/auth/token/old-token")
    assert response.status_code == 410
