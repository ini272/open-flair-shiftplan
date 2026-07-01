def test_create_group(authenticated_client):
    """Test creating a new group."""
    response = authenticated_client.post(
        "/groups/",
        json={"name": "Test Group"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Group"
    assert data["is_active"] is True
    assert "id" in data


def test_create_group_requires_authentication(client):
    """Test creating a group requires an access-code session."""
    response = client.post(
        "/groups/",
        json={"name": "No Auth Group"}
    )
    assert response.status_code == 401


def test_get_groups(authenticated_client):
    """Test getting a list of groups."""
    authenticated_client.post(
        "/groups/",
        json={"name": "List Group"}
    )

    response = authenticated_client.get("/groups/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(group["name"] == "List Group" for group in data)


def test_get_group(authenticated_client):
    """Test getting a specific group."""
    create_response = authenticated_client.post(
        "/groups/",
        json={"name": "Get Group"}
    )
    group_id = create_response.json()["id"]

    response = authenticated_client.get(f"/groups/{group_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == group_id
    assert data["name"] == "Get Group"


def test_get_nonexistent_group(authenticated_client):
    """Test getting a group that doesn't exist."""
    response = authenticated_client.get("/groups/999")
    assert response.status_code == 404


def test_create_duplicate_group_name(authenticated_client):
    """Test creating a group with a duplicate name."""
    authenticated_client.post(
        "/groups/",
        json={"name": "Duplicate Group"}
    )

    response = authenticated_client.post(
        "/groups/",
        json={"name": "Duplicate Group"}
    )
    assert response.status_code == 400


def test_update_group(authenticated_client):
    """Test updating a group as coordinator."""
    create_response = authenticated_client.post(
        "/groups/",
        json={"name": "Update Group"}
    )
    group_id = create_response.json()["id"]

    response = authenticated_client.put(
        f"/groups/{group_id}",
        json={"name": "Updated Group"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == group_id
    assert data["name"] == "Updated Group"


def test_update_group_requires_coordinator(participant_client):
    """Test participants cannot update groups."""
    create_response = participant_client.post(
        "/groups/",
        json={"name": "Participant Group"}
    )
    group_id = create_response.json()["id"]

    response = participant_client.put(
        f"/groups/{group_id}",
        json={"name": "Participant Rename"}
    )
    assert response.status_code == 403


def test_delete_group(authenticated_client):
    """Test deleting a group as coordinator."""
    create_response = authenticated_client.post(
        "/groups/",
        json={"name": "Delete Group"}
    )
    group_id = create_response.json()["id"]

    response = authenticated_client.delete(f"/groups/{group_id}")
    assert response.status_code == 204

    get_response = authenticated_client.get(f"/groups/{group_id}")
    assert get_response.status_code == 404


def test_add_user_to_group(participant_client):
    """Test adding the current participant user to a group."""
    user_response = participant_client.post(
        "/users/",
        json={"email": "groupuser@example.com", "username": "groupuser"}
    )
    user_id = user_response.json()["id"]

    group_response = participant_client.post(
        "/groups/",
        json={"name": "User Group"}
    )
    group_id = group_response.json()["id"]

    response = participant_client.post(f"/groups/{group_id}/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["group_id"] == group_id


def test_remove_user_from_group(participant_client):
    """Test removing the current participant user from their group."""
    user_response = participant_client.post(
        "/users/",
        json={"email": "removeuser@example.com", "username": "removeuser"}
    )
    user_id = user_response.json()["id"]

    group_response = participant_client.post(
        "/groups/",
        json={"name": "Remove Group"}
    )
    group_id = group_response.json()["id"]

    participant_client.post(f"/groups/{group_id}/users/{user_id}")

    response = participant_client.delete(f"/groups/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["group_id"] is None


def test_remove_user_not_in_group(participant_client):
    """Test removing a user that's not in a group."""
    user_response = participant_client.post(
        "/users/",
        json={"email": "nogroup@example.com", "username": "nogroup"}
    )
    user_id = user_response.json()["id"]

    response = participant_client.delete(f"/groups/users/{user_id}")
    assert response.status_code == 400


def test_under_16_users_cannot_join_groups(participant_client):
    """Under-16 accounts must stay out of groups."""
    user_response = participant_client.post(
        "/users/",
        json={
            "email": "under16-group@example.com",
            "username": "under16group",
            "is_under_16": True,
        }
    )
    user_id = user_response.json()["id"]

    group_response = participant_client.post(
        "/groups/",
        json={"name": "Blocked Group"}
    )
    group_id = group_response.json()["id"]

    response = participant_client.post(f"/groups/{group_id}/users/{user_id}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Users under 16 cannot join groups"
