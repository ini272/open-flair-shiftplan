def test_create_user(client):
    """Test creating a new user."""
    response = client.post(
        "/users/",
        json={
            "email": "test@example.com",
            "username": "testuser"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert data["is_active"] is True
    assert "id" in data

def test_get_users(client):
    """Test getting a list of users."""
    # Create a user first
    client.post(
        "/users/",
        json={
            "email": "list@example.com",
            "username": "listuser"
        }
    )
    
    response = client.get("/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(user["email"] == "list@example.com" for user in data)

def test_get_user(client):
    """Test getting a specific user."""
    # Create a user first
    create_response = client.post(
        "/users/",
        json={
            "email": "get@example.com",
            "username": "getuser"
        }
    )
    user_id = create_response.json()["id"]
    
    # Get the user
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == "get@example.com"
    assert data["username"] == "getuser"

def test_get_nonexistent_user(client):
    """Test getting a user that doesn't exist."""
    response = client.get("/users/999")
    assert response.status_code == 404

def test_create_duplicate_email(client):
    """Test creating a user with a duplicate email."""
    # Create first user
    client.post(
        "/users/",
        json={
            "email": "duplicate@example.com",
            "username": "user1"
        }
    )
    
    # Try to create second user with same email
    response = client.post(
        "/users/",
        json={
            "email": "duplicate@example.com",
            "username": "user2"
        }
    )
    assert response.status_code == 400

def test_create_duplicate_username(client):
    """Test creating a user with a duplicate username."""
    # Create first user
    client.post(
        "/users/",
        json={
            "email": "user1@example.com",
            "username": "duplicate"
        }
    )
    
    # Try to create second user with same username
    response = client.post(
        "/users/",
        json={
            "email": "user2@example.com",
            "username": "duplicate"
        }
    )
    assert response.status_code == 400

def test_update_user(client):
    """Test updating a user."""
    # Create a user first
    create_response = client.post(
        "/users/",
        json={
            "email": "update@example.com",
            "username": "updateuser"
        }
    )
    user_id = create_response.json()["id"]
    
    # Update the user
    response = client.put(
        f"/users/{user_id}",
        json={
            "username": "updateduser"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == "updateduser"
    assert data["email"] == "update@example.com"  # Email should not change

def test_delete_user(client):
    """Test deleting a user."""
    # Create a user first
    create_response = client.post(
        "/users/",
        json={
            "email": "delete@example.com",
            "username": "deleteuser"
        }
    )
    user_id = create_response.json()["id"]
    
    # Delete the user
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 204
    
    # Verify user is deleted
    get_response = client.get(f"/users/{user_id}")
    assert get_response.status_code == 404
