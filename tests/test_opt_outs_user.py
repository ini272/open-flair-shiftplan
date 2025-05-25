from datetime import datetime, timedelta

def test_user_opt_out(authenticated_client):
    """Test opting a user out of a shift."""
    # Create a user
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "optout@example.com", "username": "optoutuser"}
    )
    user_id = user_response.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Opt-Out Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 3
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Opt the user out
    response = authenticated_client.post(
        "/shifts/user-opt-out",
        json={
            "user_id": user_id,
            "shift_id": shift_id
        }
    )
    assert response.status_code == 200
    assert "opted out" in response.json()["message"]
    
    # Check opt-out status
    status_response = authenticated_client.get(f"/shifts/opt-out-status/{shift_id}/{user_id}")
    assert status_response.status_code == 200
    assert status_response.json()["is_opted_out"] is True
    
    # Get all shifts the user is opted out of
    shifts_response = authenticated_client.get(f"/shifts/user-opt-outs/{user_id}")
    assert shifts_response.status_code == 200
    shifts = shifts_response.json()
    assert len(shifts) == 1
    assert shifts[0]["id"] == shift_id

def test_user_opt_in(authenticated_client):
    """Test opting a user back into a shift."""
    # Create a user
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "optin@example.com", "username": "optinuser"}
    )
    user_id = user_response.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Opt-In Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # First opt the user out
    authenticated_client.post(
        "/shifts/user-opt-out",
        json={
            "user_id": user_id,
            "shift_id": shift_id
        }
    )
    
    # Now opt the user back in
    response = authenticated_client.post(
        "/shifts/user-opt-in",
        json={
            "user_id": user_id,
            "shift_id": shift_id
        }
    )
    assert response.status_code == 200
    assert "opted into" in response.json()["message"]
    
    # Check opt-out status (should be False now)
    status_response = authenticated_client.get(f"/shifts/opt-out-status/{shift_id}/{user_id}")
    assert status_response.status_code == 200
    assert status_response.json()["is_opted_out"] is False
    
    # Get all shifts the user is opted out of (should be empty)
    shifts_response = authenticated_client.get(f"/shifts/user-opt-outs/{user_id}")
    assert shifts_response.status_code == 200
    shifts = shifts_response.json()
    assert len(shifts) == 0

def test_user_in_group_cannot_have_individual_opt_outs(authenticated_client):
    """Test that a user in a group cannot have individual opt-outs."""
    # Create a group
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "No Individual Opt-Outs Group"}
    )
    group_id = group_response.json()["id"]
    
    # Create a user and add to group
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "noindividual@example.com", "username": "noindividual"}
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
            "title": "No Individual Opt-Outs Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Try to opt the user out individually (should fail)
    response = authenticated_client.post(
        "/shifts/user-opt-out",
        json={
            "user_id": user_id,
            "shift_id": shift_id
        }
    )
    assert response.status_code == 400
    assert "group" in response.json()["detail"].lower()

def test_available_users(authenticated_client):
    """Test getting available users for a shift."""
    # Create users
    user1_response = authenticated_client.post(
        "/users/",
        json={"email": "available1@example.com", "username": "available1"}
    )
    user1_id = user1_response.json()["id"]
    
    user2_response = authenticated_client.post(
        "/users/",
        json={"email": "available2@example.com", "username": "available2"}
    )
    user2_id = user2_response.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Available Users Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Get available users (should include both users)
    available_before = authenticated_client.get(f"/shifts/available-users/{shift_id}")
    assert available_before.status_code == 200
    users_before = available_before.json()
    user_ids_before = [user["id"] for user in users_before]
    assert user1_id in user_ids_before
    assert user2_id in user_ids_before
    
    # Opt out user1
    authenticated_client.post(
        "/shifts/user-opt-out",
        json={
            "user_id": user1_id,
            "shift_id": shift_id
        }
    )
    
    # Get available users again (should only include user2)
    available_after = authenticated_client.get(f"/shifts/available-users/{shift_id}")
    assert available_after.status_code == 200
    users_after = available_after.json()
    user_ids_after = [user["id"] for user in users_after]
    assert user1_id not in user_ids_after
    assert user2_id in user_ids_after