def test_protected_route_authenticated(authenticated_client):
    """Test accessing a protected route when authenticated."""
    response = authenticated_client.get("/protected/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_protected_route_unauthenticated(client):
    """Test accessing a protected route when not authenticated."""
    response = client.get("/protected/")
    assert response.status_code == 401

def test_protected_route_with_invalid_token(client):
    """Test accessing a protected route with an invalid token."""
    client.cookies.set("access_token", "invalid-token")
    response = client.get("/protected/")
    assert response.status_code == 401
