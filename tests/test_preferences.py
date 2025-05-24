from datetime import datetime, timedelta

def test_set_preference(authenticated_client):
    """Test setting a user preference for a shift."""
    # Create a user
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "prefuser@example.com", "username": "prefuser"}
    )
    user_id = user_response.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Preference Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 3
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Set preference (can work)
    response = authenticated_client.post(
        "/preferences/",
        json={
            "user_id": user_id,
            "shift_id": shift_id,
            "can_work": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["shift_id"] == shift_id
    assert data["can_work"] is True

def test_get_user_preferences(authenticated_client):
    """Test getting all preferences for a user."""
    # Create a user
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "prefuser2@example.com", "username": "prefuser2"}
    )
    user_id = user_response.json()["id"]
    
    # Create two shifts
    start_time1 = datetime.utcnow() + timedelta(hours=1)
    end_time1 = start_time1 + timedelta(hours=2)
    
    shift_response1 = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Preference Test Shift 1",
            "start_time": start_time1.isoformat(),
            "end_time": end_time1.isoformat()
        }
    )
    shift_id1 = shift_response1.json()["id"]
    
    start_time2 = datetime.utcnow() + timedelta(hours=3)
    end_time2 = start_time2 + timedelta(hours=2)
    
    shift_response2 = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Preference Test Shift 2",
            "start_time": start_time2.isoformat(),
            "end_time": end_time2.isoformat()
        }
    )
    shift_id2 = shift_response2.json()["id"]
    
    # Set preferences
    authenticated_client.post(
        "/preferences/",
        json={
            "user_id": user_id,
            "shift_id": shift_id1,
            "can_work": True
        }
    )
    
    authenticated_client.post(
        "/preferences/",
        json={
            "user_id": user_id,
            "shift_id": shift_id2,
            "can_work": False
        }
    )
    
    # Get preferences
    response = authenticated_client.get(f"/preferences/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Verify preferences
    assert any(pref["shift_id"] == shift_id1 and pref["can_work"] is True for pref in data)
    assert any(pref["shift_id"] == shift_id2 and pref["can_work"] is False for pref in data)

def test_get_users_for_shift(authenticated_client):
    """Test getting all users who can work a shift."""
    # Create two users
    user_response1 = authenticated_client.post(
        "/users/",
        json={"email": "shiftuser1@example.com", "username": "shiftuser1"}
    )
    user_id1 = user_response1.json()["id"]
    
    user_response2 = authenticated_client.post(
        "/users/",
        json={"email": "shiftuser2@example.com", "username": "shiftuser2"}
    )
    user_id2 = user_response2.json()["id"]
    
    # Create a shift
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)
    
    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Users Test Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    shift_id = shift_response.json()["id"]
    
    # Set preferences
    authenticated_client.post(
        "/preferences/",
        json={
            "user_id": user_id1,
            "shift_id": shift_id,
            "can_work": True
        }
    )
    
    authenticated_client.post(
        "/preferences/",
        json={
            "user_id": user_id2,
            "shift_id": shift_id,
            "can_work": False
        }
    )
    
    # Get users who can work
    response = authenticated_client.get(f"/preferences/shifts/{shift_id}?can_work=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert user_id1 in data
    
    # Get users who cannot work
    response = authenticated_client.get(f"/preferences/shifts/{shift_id}?can_work=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert user_id2 in data

def test_generate_shift_plan(authenticated_client):
    """Test generating a shift plan based on preferences."""
    # Create users
    user_response1 = authenticated_client.post(
        "/users/",
        json={"email": "planuser1@example.com", "username": "planuser1"}
    )
    user_id1 = user_response1.json()["id"]
    
    user_response2 = authenticated_client.post(
        "/users/",
        json={"email": "planuser2@example.com", "username": "planuser2"}
    )
    user_id2 = user_response2.json()["id"]
    
    # Create shifts for the festival period
    festival_start = datetime(2025, 8, 6, 10, 0)
    
    shift_response1 = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Morning Shift",
            "start_time": festival_start.isoformat(),
            "end_time": (festival_start + timedelta(hours=4)).isoformat(),
            "capacity": 1
        }
    )
    shift_id1 = shift_response1.json()["id"]
    
    shift_response2 = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Afternoon Shift",
            "start_time": (festival_start + timedelta(hours=5)).isoformat(),
            "end_time": (festival_start + timedelta(hours=9)).isoformat(),
            "capacity": 1
        }
    )
    shift_id2 = shift_response2.json()["id"]
    
    # Set preferences - both users can work both shifts
    authenticated_client.post(
        "/preferences/",
        json={
            "user_id": user_id1,
            "shift_id": shift_id1,
            "can_work": True
        }
    )
    
    authenticated_client.post(
        "/preferences/",
        json={
            "user_id": user_id1,
            "shift_id": shift_id2,
            "can_work": True
        }
    )
    
    authenticated_client.post(
        "/preferences/",
        json={
            "user_id": user_id2,
            "shift_id": shift_id1,
            "can_work": True
        }
    )
    
    authenticated_client.post(
        "/preferences/",
        json={
            "user_id": user_id2,
            "shift_id": shift_id2,
            "can_work": True
        }
    )
    
    # Generate shift plan
    response = authenticated_client.post("/shifts/generate-plan")
    assert response.status_code == 200
    data = response.json()
    
    # Verify assignments were made
    assert "assignments" in data
    assert len(data["assignments"]) > 0
    
    # Check that each shift has at most one user assigned (due to capacity=1)
    shift1_assignments = [a for a in data["assignments"] if a["shift_id"] == shift_id1]
    shift2_assignments = [a for a in data["assignments"] if a["shift_id"] == shift_id2]
    
    assert len(shift1_assignments) <= 1
    assert len(shift2_assignments) <= 1
    
    # Verify the assignments through the API
    shift1_response = authenticated_client.get(f"/shifts/{shift_id1}")
    shift1_data = shift1_response.json()
    assert len(shift1_data["users"]) <= 1
    
    shift2_response = authenticated_client.get(f"/shifts/{shift_id2}")
    shift2_data = shift2_response.json()
    assert len(shift2_data["users"]) <= 1