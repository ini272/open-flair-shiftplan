def test_create_user(authenticated_client):
    """Test creating a new user."""
    response = authenticated_client.post(
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


def test_create_user_requires_authentication(client):
    """Test creating a user requires an access-code session."""
    response = client.post(
        "/users/",
        json={
            "email": "unauth@example.com",
            "username": "unauth"
        }
    )
    assert response.status_code == 401


def test_get_users(authenticated_client):
    """Test getting a list of users as coordinator."""
    authenticated_client.post(
        "/users/",
        json={
            "email": "list@example.com",
            "username": "listuser"
        }
    )

    response = authenticated_client.get("/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(user["email"] == "list@example.com" for user in data)


def test_get_users_requires_coordinator(participant_client):
    """Test participants cannot list all users."""
    response = participant_client.get("/users/")
    assert response.status_code == 403


def test_get_user(authenticated_client):
    """Test getting a specific user."""
    create_response = authenticated_client.post(
        "/users/",
        json={
            "email": "get@example.com",
            "username": "getuser"
        }
    )
    user_id = create_response.json()["id"]

    response = authenticated_client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == "get@example.com"
    assert data["username"] == "getuser"


def test_get_nonexistent_user(authenticated_client):
    """Test getting a user that doesn't exist."""
    response = authenticated_client.get("/users/999")
    assert response.status_code == 404


def test_create_duplicate_email(authenticated_client):
    """Test creating a user with a duplicate email."""
    authenticated_client.post(
        "/users/",
        json={
            "email": "duplicate@example.com",
            "username": "user1"
        }
    )

    response = authenticated_client.post(
        "/users/",
        json={
            "email": "duplicate@example.com",
            "username": "user2"
        }
    )
    assert response.status_code == 400


def test_create_duplicate_username(authenticated_client):
    """Test creating a user with a duplicate username."""
    authenticated_client.post(
        "/users/",
        json={
            "email": "user1@example.com",
            "username": "duplicate"
        }
    )

    response = authenticated_client.post(
        "/users/",
        json={
            "email": "user2@example.com",
            "username": "duplicate"
        }
    )
    assert response.status_code == 400


def test_update_user(authenticated_client):
    """Test updating a user."""
    create_response = authenticated_client.post(
        "/users/",
        json={
            "email": "update@example.com",
            "username": "updateuser"
        }
    )
    user_id = create_response.json()["id"]

    response = authenticated_client.put(
        f"/users/{user_id}",
        json={
            "username": "updateduser"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == "updateduser"
    assert data["email"] == "update@example.com"


def test_delete_user(authenticated_client):
    """Test deleting a user."""
    create_response = authenticated_client.post(
        "/users/",
        json={
            "email": "delete@example.com",
            "username": "deleteuser"
        }
    )
    user_id = create_response.json()["id"]

    response = authenticated_client.delete(f"/users/{user_id}")
    assert response.status_code == 204

    get_response = authenticated_client.get(f"/users/{user_id}")
    assert get_response.status_code == 404


def test_participant_user_is_not_coordinator(participant_client):
    """Test users created with the event code do not get coordinator rights."""
    response = participant_client.post(
        "/users/",
        json={
            "email": "participant@example.com",
            "username": "participant"
        }
    )

    assert response.status_code == 201
    assert response.json()["is_coordinator"] is False


def test_coordinator_user_requires_coordinator_code(authenticated_client):
    """Test users created with the coordinator code get coordinator rights."""
    response = authenticated_client.post(
        "/users/",
        json={
            "email": "coordinator@example.com",
            "username": "coordinator"
        }
    )

    assert response.status_code == 201
    assert response.json()["is_coordinator"] is True
