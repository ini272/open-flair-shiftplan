from datetime import datetime, timedelta

def test_create_token(client):
    """Test creating a new token."""
    response = client.post(
        "/auth/tokens/",
        json={"name": "Admin Token", "expires_in_days": 30}
    )
    assert response.status_code == 201
    data = response.json()
    assert "token" in data
    assert data["name"] == "Admin Token"
    assert data["is_active"] is True

def test_list_tokens(client, test_token):
    """Test listing all tokens."""
    response = client.get("/auth/tokens/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(token["token"] == test_token for token in data)

def test_login_with_token(client, test_token):
    """Test logging in with a token."""
    response = client.get(f"/auth/login/{test_token}")
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert response.cookies["access_token"] == test_token

def test_login_with_invalid_token(client):
    """Test logging in with an invalid token."""
    response = client.get("/auth/login/invalid-token")
    assert response.status_code == 401

def test_check_auth_authenticated(authenticated_client):
    """Test checking authentication when authenticated."""
    response = authenticated_client.get("/auth/check")
    assert response.status_code == 200
    assert response.json()["authenticated"] is True

def test_check_auth_unauthenticated(client):
    """Test checking authentication when not authenticated."""
    response = client.get("/auth/check")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False

def test_logout(authenticated_client):
    """Test logging out."""
    response = authenticated_client.get("/auth/logout")
    assert response.status_code == 200
    
    # Check if the Set-Cookie header is present and contains access_token
    assert "Set-Cookie" in response.headers
    assert "access_token=" in response.headers["Set-Cookie"]
    
    # Check if the cookie is being cleared (value should be empty and max-age should be 0 or expires should be in the past)
    cookie_header = response.headers["Set-Cookie"]
    assert "access_token=" in cookie_header
    assert "Max-Age=0" in cookie_header or "Expires=" in cookie_header

def test_revoke_token(client, test_token):
    """Test revoking a token."""
    # First, get the token ID
    response = client.get("/auth/tokens/")
    tokens = response.json()
    token_id = next(token["id"] for token in tokens if token["token"] == test_token)
    
    # Now revoke the token
    response = client.delete(f"/auth/tokens/{token_id}")
    assert response.status_code == 204
    
    # Verify the token is no longer valid for login
    response = client.get(f"/auth/login/{test_token}")
    assert response.status_code == 401
