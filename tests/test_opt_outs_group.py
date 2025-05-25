from datetime import datetime, timedelta

def test_group_opt_out(authenticated_client):
    """Test opting a group out of a shift."""
    # Create a group
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Opt-Out Test Group"}
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
            "title": "Group Opt-Out Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Opt the group out
    response = authenticated_client.post(
        "/shifts/group-opt-out",
        json={
            "group_id": group_id,
            "shift_id": shift_id
        }
    )
    assert response.status_code == 200
    assert "opted out" in response.json()["message"]
    
    # Check opt-out status for users in the group
    status_response1 = authenticated_client.get(f"/shifts/opt-out-status/{shift_id}/{user1_id}")
    assert status_response1.status_code == 200
    assert status_response1.json()["is_opted_out"] is True
    
    status_response2 = authenticated_client.get(f"/shifts/opt-out-status/{shift_id}/{user2_id}")
    assert status_response2.status_code == 200
    assert status_response2.json()["is_opted_out"] is True
    
    # Get all shifts the group is opted out of
    shifts_response = authenticated_client.get(f"/shifts/group-opt-outs/{group_id}")
    assert shifts_response.status_code == 200
    shifts = shifts_response.json()
    assert len(shifts) == 1
    assert shifts[0]["id"] == shift_id

def test_group_opt_in(authenticated_client):
    """Test opting a group back into a shift."""
    # Create a group
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Opt-In Test Group"}
    )
    group_id = group_response.json()["id"]
    
    # Create users and add to group
    user1_response = authenticated_client.post(
        "/users/",
        json={"email": "groupoptin1@example.com", "username": "groupoptin1"}
    )
    user1_id = user1_response.json()["id"]
    
    # Add user to group
    authenticated_client.post(f"/groups/{group_id}/users/{user1_id}")
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Group Opt-In Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # First opt the group out
    authenticated_client.post(
        "/shifts/group-opt-out",
        json={
            "group_id": group_id,
            "shift_id": shift_id
        }
    )
    
    # Now opt the group back in
    response = authenticated_client.post(
        "/shifts/group-opt-in",
        json={
            "group_id": group_id,
            "shift_id": shift_id
        }
    )
    assert response.status_code == 200
    assert "opted into" in response.json()["message"]
    
    # Check opt-out status for user in the group (should be False now)
    status_response = authenticated_client.get(f"/shifts/opt-out-status/{shift_id}/{user1_id}")
    assert status_response.status_code == 200
    assert status_response.json()["is_opted_out"] is False
    
    # Get all shifts the group is opted out of (should be empty)
    shifts_response = authenticated_client.get(f"/shifts/group-opt-outs/{group_id}")
    assert shifts_response.status_code == 200
    shifts = shifts_response.json()
    assert len(shifts) == 0

def test_user_inherits_group_opt_outs_when_joining(authenticated_client):
    """Test that a user inherits group opt-outs when joining a group."""
    # Create a group
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Inherit Opt-Outs Group"}
    )
    group_id = group_response.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Inherit Opt-Outs Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Opt the group out of the shift
    authenticated_client.post(
        "/shifts/group-opt-out",
        json={
            "group_id": group_id,
            "shift_id": shift_id
        }
    )
    
    # Create a user
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "inherit@example.com", "username": "inherit"}
    )
    user_id = user_response.json()["id"]
    
    # Check opt-out status before joining group (should be False)
    status_before = authenticated_client.get(f"/shifts/opt-out-status/{shift_id}/{user_id}")
    assert status_before.status_code == 200
    assert status_before.json()["is_opted_out"] is False
    
    # Add user to group
    authenticated_client.post(f"/groups/{group_id}/users/{user_id}")
    
    # Check opt-out status after joining group (should be True)
    status_after = authenticated_client.get(f"/shifts/opt-out-status/{shift_id}/{user_id}")
    assert status_after.status_code == 200
    assert status_after.json()["is_opted_out"] is True

def test_user_loses_group_opt_outs_when_leaving(authenticated_client):
    """Test that a user loses group opt-outs when leaving a group."""
    # Create a group
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Leave Group Opt-Outs"}
    )
    group_id = group_response.json()["id"]
    
    # Create a user and add to group
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "leavegroup@example.com", "username": "leavegroup"}
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
            "title": "Leave Group Opt-Outs Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Opt the group out of the shift
    authenticated_client.post(
        "/shifts/group-opt-out",
        json={
            "group_id": group_id,
            "shift_id": shift_id
        }
    )
    
    # Check opt-out status while in group (should be True)
    status_in_group = authenticated_client.get(f"/shifts/opt-out-status/{shift_id}/{user_id}")
    assert status_in_group.status_code == 200
    assert status_in_group.json()["is_opted_out"] is True
    
    # Remove user from group
    authenticated_client.delete(f"/groups/users/{user_id}")
    
    # Check opt-out status after leaving group (should be False)
    status_after_leaving = authenticated_client.get(f"/shifts/opt-out-status/{shift_id}/{user_id}")
    assert status_after_leaving.status_code == 200
    assert status_after_leaving.json()["is_opted_out"] is False

def test_group_available_users(authenticated_client):
    """Test that users in an opted-out group are not available for a shift."""
    # Create a group
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Available Test Group"}
    )
    group_id = group_response.json()["id"]
    
    # Create a user in the group
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "groupavailable@example.com", "username": "groupavailable"}
    )
    user_id = user_response.json()["id"]
    
    # Add user to group
    authenticated_client.post(f"/groups/{group_id}/users/{user_id}")
    
    # Create a user not in any group
    solo_user_response = authenticated_client.post(
        "/users/",
        json={"email": "soloavailable@example.com", "username": "soloavailable"}
    )
    solo_user_id = solo_user_response.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Group Available Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Get available users before opt-out (should include both users)
    available_before = authenticated_client.get(f"/shifts/available-users/{shift_id}")
    assert available_before.status_code == 200
    users_before = available_before.json()
    user_ids_before = [user["id"] for user in users_before]
    assert user_id in user_ids_before
    assert solo_user_id in user_ids_before
    
    # Opt the group out
    authenticated_client.post(
        "/shifts/group-opt-out",
        json={
            "group_id": group_id,
            "shift_id": shift_id
        }
    )
    
    # Get available users after opt-out (should only include solo user)
    available_after = authenticated_client.get(f"/shifts/available-users/{shift_id}")
    assert available_after.status_code == 200
    users_after = available_after.json()
    user_ids_after = [user["id"] for user in users_after]
    assert user_id not in user_ids_after
    assert solo_user_id in user_ids_after