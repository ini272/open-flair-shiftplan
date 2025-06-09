from datetime import datetime, timedelta

def test_create_shift(authenticated_client):
    """Test creating a new shift."""
    # Define shift data
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    # Format as ISO string without timezone info
    # This should now be handled by your validator
    response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Morning Shift",
            "description": "Early morning shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 5
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Morning Shift"
    assert data["description"] == "Early morning shift"
    assert data["capacity"] == 5
    assert data["is_active"] is True
    assert "id" in data
    assert data["current_user_count"] == 0

def test_create_shift_with_invalid_times(authenticated_client):
    """Test creating a shift with end_time before start_time."""
    start_time = datetime.utcnow() + timedelta(hours=2)
    end_time = start_time - timedelta(hours=1)  # End before start
    
    response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Invalid Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    assert response.status_code == 422  # Validation error

def test_create_shift_with_invalid_capacity(authenticated_client):
    """Test creating a shift with negative capacity."""
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Invalid Capacity Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": -1
        }
    )
    assert response.status_code == 422  # Validation error

def test_get_shifts(authenticated_client):
    """Test getting a list of shifts."""
    # Create a shift first
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    authenticated_client.post(
        "/shifts/",
        json={
            "title": "List Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    
    response = authenticated_client.get("/shifts/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(shift["title"] == "List Test Shift" for shift in data)

def test_get_shift(authenticated_client):
    """Test getting a specific shift."""
    # Create a shift first
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    create_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Get Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = create_response.json()["id"]
    
    # Get the shift
    response = authenticated_client.get(f"/shifts/{shift_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == shift_id
    assert data["title"] == "Get Test Shift"
    assert "users" in data
    assert "groups" in data

def test_get_nonexistent_shift(authenticated_client):
    """Test getting a shift that doesn't exist."""
    response = authenticated_client.get("/shifts/999")
    assert response.status_code == 404

def test_update_shift(authenticated_client):
    """Test updating a shift."""
    # Create a shift first
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    create_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Update Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = create_response.json()["id"]
    
    # Update the shift
    new_end_time = start_time + timedelta(hours=3)
    response = authenticated_client.put(
        f"/shifts/{shift_id}",
        json={
            "title": "Updated Shift",
            "end_time": new_end_time.isoformat()
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == shift_id
    assert data["title"] == "Updated Shift"
    # The end time should be updated
    assert datetime.fromisoformat(data["end_time"].replace("Z", "+00:00")) > datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))

def test_delete_shift(authenticated_client):
    """Test deleting a shift."""
    # Create a shift first
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    create_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Delete Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = create_response.json()["id"]
    
    # Delete the shift
    response = authenticated_client.delete(f"/shifts/{shift_id}")
    assert response.status_code == 204
    
    # Verify shift is deleted
    get_response = authenticated_client.get(f"/shifts/{shift_id}")
    assert get_response.status_code == 404

def test_add_user_to_shift(authenticated_client):
    """Test adding a user to a shift."""
    # Create a user
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "shiftuser@example.com", "username": "shiftuser"}
    )
    user_id = user_response.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "User Assignment Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 3
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Add user to shift
    response = authenticated_client.post(
        "/shifts/users/",
        json={"shift_id": shift_id, "user_id": user_id}
    )
    assert response.status_code == 200
    
    # Verify user was added to shift
    shift_response = authenticated_client.get(f"/shifts/{shift_id}")
    shift_data = shift_response.json()
    assert any(user["id"] == user_id for user in shift_data["users"])
    assert shift_data["current_user_count"] == 1

def test_add_group_to_shift(authenticated_client):
    """Test adding a group to a shift."""
    # Create a group
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Shift Test Group"}
    )
    group_id = group_response.json()["id"]
    
    # Create users and add to group
    user1_response = authenticated_client.post(
        "/users/",
        json={"email": "groupuser1@example.com", "username": "groupuser1"}
    )
    user1_id = user1_response.json()["id"]
    
    user2_response = authenticated_client.post(
        "/users/",
        json={"email": "groupuser2@example.com", "username": "groupuser2"}
    )
    user2_id = user2_response.json()["id"]
    
    # Add users to group
    authenticated_client.post(f"/groups/{group_id}/users/{user1_id}")
    authenticated_client.post(f"/groups/{group_id}/users/{user2_id}")
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Group Assignment Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 5
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Add group to shift
    response = authenticated_client.post(
        "/shifts/groups/",
        json={"shift_id": shift_id, "group_id": group_id}
    )
    assert response.status_code == 200
    
    # Verify group and its users were added to shift
    shift_response = authenticated_client.get(f"/shifts/{shift_id}")
    shift_data = shift_response.json()
    assert any(group["id"] == group_id for group in shift_data["groups"])
    assert any(user["id"] == user1_id for user in shift_data["users"])
    assert any(user["id"] == user2_id for user in shift_data["users"])
    assert shift_data["current_user_count"] == 2

def test_shift_capacity_limit(authenticated_client):
    """Test that shifts enforce capacity limits."""
    # Create a shift with capacity 1
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Limited Capacity Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 1
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Create two users
    user1_response = authenticated_client.post(
        "/users/",
        json={"email": "capacity1@example.com", "username": "capacity1"}
    )
    user1_id = user1_response.json()["id"]
    
    user2_response = authenticated_client.post(
        "/users/",
        json={"email": "capacity2@example.com", "username": "capacity2"}
    )
    user2_id = user2_response.json()["id"]
    
    # Add first user to shift (should succeed)
    response1 = authenticated_client.post(
        "/shifts/users/",
        json={"shift_id": shift_id, "user_id": user1_id}
    )
    assert response1.status_code == 200
    
    # Try to add second user to shift (should fail due to capacity)
    response2 = authenticated_client.post(
        "/shifts/users/",
        json={"shift_id": shift_id, "user_id": user2_id}
    )
    assert response2.status_code == 400  # Bad request due to capacity limit

def test_remove_user_from_shift(authenticated_client):
    """Test removing a user from a shift."""
    # Create a user
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "removeuser@example.com", "username": "removeuser"}
    )
    user_id = user_response.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Remove User Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Add user to shift
    authenticated_client.post(
        "/shifts/users/",
        json={"shift_id": shift_id, "user_id": user_id}
    )
    
    # Remove user from shift
    response = authenticated_client.delete(f"/shifts/users/{shift_id}/{user_id}")
    assert response.status_code == 200
    
    # Verify user was removed
    shift_response = authenticated_client.get(f"/shifts/{shift_id}")
    shift_data = shift_response.json()
    assert not any(user["id"] == user_id for user in shift_data["users"])
    assert shift_data["current_user_count"] == 0

def test_remove_group_from_shift(authenticated_client):
    """Test removing a group from a shift."""
    # Create a group
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Remove Test Group"}
    )
    group_id = group_response.json()["id"]
    
    # Create users and add to group
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "removegroup@example.com", "username": "removegroup"}
    )
    user_id = user_response.json()["id"]
    
    # Add user to group
    authenticated_client.post(f"/groups/{group_id}/users/{user_id}")
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Remove Group Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Add group to shift
    authenticated_client.post(
        "/shifts/groups/",
        json={"shift_id": shift_id, "group_id": group_id}
    )
    
    # Remove group from shift
    response = authenticated_client.delete(f"/shifts/groups/{shift_id}/{group_id}")
    assert response.status_code == 200
    
    # Verify group was removed but user remains
    shift_response = authenticated_client.get(f"/shifts/{shift_id}")
    shift_data = shift_response.json()
    assert not any(group["id"] == group_id for group in shift_data["groups"])
    # User should still be in the shift even though group was remove

def test_shift_requires_authentication(client):
    """Test that shift endpoints require authentication."""
    # Try to access shifts without authentication
    response = client.get("/shifts/")
    assert response.status_code == 401
    
    # Try to create a shift without authentication
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    response = client.post(
        "/shifts/",
        json={
            "title": "Unauthorized Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    assert response.status_code == 401

def test_clear_all_assignments(authenticated_client):
    """Test clearing all shift assignments."""
    # Create a user
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "cleartest@example.com", "username": "cleartest"}
    )
    user_id = user_response.json()["id"]
    
    # Create a group
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Clear Test Group"}
    )
    group_id = group_response.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Clear Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Add user to shift
    authenticated_client.post(
        "/shifts/users/",
        json={"shift_id": shift_id, "user_id": user_id}
    )
    
    # Add group to shift
    authenticated_client.post(
        "/shifts/groups/",
        json={"shift_id": shift_id, "group_id": group_id}
    )
    
    # Verify assignments exist
    shift_response = authenticated_client.get(f"/shifts/{shift_id}")
    shift_data = shift_response.json()
    assert len(shift_data["users"]) > 0
    assert len(shift_data["groups"]) > 0
    
    # Clear all assignments
    response = authenticated_client.delete("/shifts/all-assignments")
    assert response.status_code == 200
    data = response.json()
    assert "assignments_cleared" in data
    assert data["assignments_cleared"] > 0
    
    # Verify assignments are cleared
    shift_response = authenticated_client.get(f"/shifts/{shift_id}")
    shift_data = shift_response.json()
    assert len(shift_data["users"]) == 0
    assert len(shift_data["groups"]) == 0
