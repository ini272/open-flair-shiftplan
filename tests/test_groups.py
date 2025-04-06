def test_create_group(client):
    """Test creating a new group."""
    response = client.post(
        "/groups/",
        json={"name": "Test Group"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Group"
    assert data["is_active"] is True
    assert "id" in data

def test_get_groups(client):
    """Test getting a list of groups."""
    # Create a group first
    client.post(
        "/groups/",
        json={"name": "List Group"}
    )
    
    response = client.get("/groups/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(group["name"] == "List Group" for group in data)

def test_get_group(client):
    """Test getting a specific group."""
    # Create a group first
    create_response = client.post(
        "/groups/",
        json={"name": "Get Group"}
    )
    group_id = create_response.json()["id"]
    
    # Get the group
    response = client.get(f"/groups/{group_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == group_id
    assert data["name"] == "Get Group"

def test_get_nonexistent_group(client):
    """Test getting a group that doesn't exist."""
    response = client.get("/groups/999")
    assert response.status_code == 404

def test_create_duplicate_group_name(client):
    """Test creating a group with a duplicate name."""
    # Create first group
    client.post(
        "/groups/",
        json={"name": "Duplicate Group"}
    )
    
    # Try to create second group with same name
    response = client.post(
        "/groups/",
        json={"name": "Duplicate Group"}
    )
    assert response.status_code == 400

def test_update_group(client):
    """Test updating a group."""
    # Create a group first
    create_response = client.post(
        "/groups/",
        json={"name": "Update Group"}
    )
    group_id = create_response.json()["id"]
    
    # Update the group
    response = client.put(
        f"/groups/{group_id}",
        json={"name": "Updated Group"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == group_id
    assert data["name"] == "Updated Group"

def test_delete_group(client):
    """Test deleting a group."""
    # Create a group first
    create_response = client.post(
        "/groups/",
        json={"name": "Delete Group"}
    )
    group_id = create_response.json()["id"]
    
    # Delete the group
    response = client.delete(f"/groups/{group_id}")
    assert response.status_code == 204
    
    # Verify group is deleted
    get_response = client.get(f"/groups/{group_id}")
    assert get_response.status_code == 404

def test_add_user_to_group(client):
    """Test adding a user to a group."""
    # Create a user
    user_response = client.post(
        "/users/",
        json={"email": "groupuser@example.com", "username": "groupuser"}
    )
    user_id = user_response.json()["id"]
    
    # Create a group
    group_response = client.post(
        "/groups/",
        json={"name": "User Group"}
    )
    group_id = group_response.json()["id"]
    
    # Add user to group
    response = client.post(f"/groups/{group_id}/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["group_id"] == group_id

def test_remove_user_from_group(client):
    """Test removing a user from a group."""
    # Create a user
    user_response = client.post(
        "/users/",
        json={"email": "removeuser@example.com", "username": "removeuser"}
    )
    user_id = user_response.json()["id"]
    
    # Create a group
    group_response = client.post(
        "/groups/",
        json={"name": "Remove Group"}
    )
    group_id = group_response.json()["id"]
    
    # Add user to group
    client.post(f"/groups/{group_id}/users/{user_id}")
    
    # Remove user from group
    response = client.delete(f"/groups/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["group_id"] is None

def test_remove_user_not_in_group(client):
    """Test removing a user that's not in a group."""
    # Create a user without adding to a group
    user_response = client.post(
        "/users/",
        json={"email": "nogroup@example.com", "username": "nogroup"}
    )
    user_id = user_response.json()["id"]
    
    # Try to remove from group
    response = client.delete(f"/groups/users/{user_id}")
    assert response.status_code == 400
