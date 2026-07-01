from datetime import datetime, timedelta
from types import SimpleNamespace

from app.routes.shift import get_shift_day_key, is_priority_evening_shift


def login_as_participant(client):
    response = client.post("/auth/login", json={"access_code": "weinzelt2026"})
    assert response.status_code == 200


def login_as_coordinator(client):
    response = client.post("/auth/login", json={"access_code": "koordination2026"})
    assert response.status_code == 200


def create_participant_user(client, email, username, *, is_under_16=False):
    login_as_participant(client)
    response = client.post(
        "/users/",
        json={"email": email, "username": username, "is_under_16": is_under_16},
    )
    assert response.status_code == 201
    return response.json()

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
    user_id1 = create_participant_user(
        authenticated_client,
        "planuser1@example.com",
        "planuser1",
    )["id"]
    user_id2 = create_participant_user(
        authenticated_client,
        "planuser2@example.com",
        "planuser2",
    )["id"]
    login_as_coordinator(authenticated_client)
    
    # Create shifts for the festival period
    festival_start = datetime(2026, 8, 5, 10, 0)
    
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


def test_generate_shift_plan_excludes_coordinator_accounts(client):
    """Coordinator accounts should never appear in generated assignments."""
    client.post("/auth/login", json={"access_code": "koordination2026"})
    coordinator_response = client.post(
        "/users/",
        json={"email": "excluded-coordinator@example.com", "username": "excludedcoordinator"},
    )
    coordinator_id = coordinator_response.json()["id"]

    client.post("/auth/login", json={"access_code": "weinzelt2026"})
    participant_response = client.post(
        "/users/",
        json={"email": "included-participant@example.com", "username": "includedparticipant"},
    )
    participant_id = participant_response.json()["id"]

    client.post("/auth/login", json={"access_code": "koordination2026"})
    start_time = datetime(2026, 8, 6, 16, 0)
    end_time = start_time + timedelta(hours=2)
    shift_response = client.post(
        "/shifts/",
        json={
            "title": "Coordinator Exclusion Shift",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 1,
        },
    )
    shift_id = shift_response.json()["id"]

    response = client.post("/shifts/generate-plan?max_shifts_per_user=1&planner_seed=5")
    assert response.status_code == 200

    assignments = response.json()["assignments"]
    assigned_user_ids = {assignment["user_id"] for assignment in assignments}
    assigned_shift_ids = {assignment["shift_id"] for assignment in assignments}

    assert shift_id in assigned_shift_ids
    assert participant_id in assigned_user_ids
    assert coordinator_id not in assigned_user_ids


def test_generate_shift_plan_does_not_split_groups(authenticated_client):
    """Groups should only be assigned as a whole planning unit."""
    group_response = authenticated_client.post("/groups/", json={"name": "Night Owls"})
    group_id = group_response.json()["id"]

    user_id1 = create_participant_user(
        authenticated_client,
        "groupmember1@example.com",
        "groupmember1",
    )["id"]
    user_id2 = create_participant_user(
        authenticated_client,
        "groupmember2@example.com",
        "groupmember2",
    )["id"]
    login_as_coordinator(authenticated_client)

    authenticated_client.post(f"/groups/{group_id}/users/{user_id1}")
    authenticated_client.post(f"/groups/{group_id}/users/{user_id2}")

    shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Too Small For Group",
            "start_time": datetime(2026, 8, 6, 14, 0).isoformat(),
            "end_time": datetime(2026, 8, 6, 16, 0).isoformat(),
            "capacity": 1,
        },
    )
    shift_id = shift_response.json()["id"]

    response = authenticated_client.post("/shifts/generate-plan")
    assert response.status_code == 200
    data = response.json()

    assert data["assignments"] == []

    shift_data = authenticated_client.get(f"/shifts/{shift_id}").json()
    assert shift_data["users"] == []
    assert shift_data["groups"] == []


def test_generate_shift_plan_spreads_assignments_across_days(authenticated_client):
    """A flexible user should be distributed across festival days before stacking one day."""
    user_id = create_participant_user(
        authenticated_client,
        "daybalance@example.com",
        "daybalance",
    )["id"]
    login_as_coordinator(authenticated_client)

    shifts = [
        ("Day 1 Early", datetime(2026, 8, 6, 14, 0), datetime(2026, 8, 6, 16, 0)),
        ("Day 1 Late", datetime(2026, 8, 6, 16, 0), datetime(2026, 8, 6, 18, 0)),
        ("Day 2 Early", datetime(2026, 8, 7, 14, 0), datetime(2026, 8, 7, 16, 0)),
        ("Day 2 Late", datetime(2026, 8, 7, 16, 0), datetime(2026, 8, 7, 18, 0)),
    ]

    created_shift_ids = []
    for title, start_time, end_time in shifts:
        response = authenticated_client.post(
            "/shifts/",
            json={
                "title": title,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "capacity": 1,
            },
        )
        created_shift_ids.append(response.json()["id"])

    response = authenticated_client.post("/shifts/generate-plan?max_shifts_per_user=2")
    assert response.status_code == 200
    data = response.json()

    user_assignments = [assignment for assignment in data["assignments"] if assignment["user_id"] == user_id]
    assert len(user_assignments) == 2

    assigned_dates = {
        authenticated_client.get(f"/shifts/{assignment['shift_id']}").json()["start_time"].split("T")[0]
        for assignment in user_assignments
    }
    assert len(assigned_dates) == 2


def test_generate_shift_plan_shares_weekend_evenings(authenticated_client):
    """Friday/Saturday evening shifts should be shared before one user gets both."""
    user_id1 = create_participant_user(
        authenticated_client,
        "evening1@example.com",
        "evening1",
    )["id"]
    user_id2 = create_participant_user(
        authenticated_client,
        "evening2@example.com",
        "evening2",
    )["id"]
    login_as_coordinator(authenticated_client)

    friday_shift = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Friday Main Act",
            "start_time": datetime(2026, 8, 7, 20, 0).isoformat(),
            "end_time": datetime(2026, 8, 7, 22, 0).isoformat(),
            "capacity": 1,
        },
    ).json()["id"]

    saturday_shift = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Saturday Main Act",
            "start_time": datetime(2026, 8, 8, 20, 0).isoformat(),
            "end_time": datetime(2026, 8, 8, 22, 0).isoformat(),
            "capacity": 1,
        },
    ).json()["id"]

    response = authenticated_client.post("/shifts/generate-plan?max_shifts_per_user=2")
    assert response.status_code == 200
    data = response.json()

    evening_assignments = [
        assignment
        for assignment in data["assignments"]
        if assignment["shift_id"] in {friday_shift, saturday_shift}
    ]

    assert len(evening_assignments) == 2
    assert {assignment["user_id"] for assignment in evening_assignments} == {user_id1, user_id2}


def test_generate_shift_plan_allows_three_consecutive_only_when_forced(authenticated_client):
    user_id = create_participant_user(
        authenticated_client,
        "forcedtriple@example.com",
        "forcedtriple",
    )["id"]
    login_as_coordinator(authenticated_client)

    shift_ids = []
    for start_hour in (14, 16, 18):
        shift_ids.append(
            authenticated_client.post(
                "/shifts/",
                json={
                    "title": f"Forced Triple {start_hour}",
                    "start_time": datetime(2026, 8, 6, start_hour, 0).isoformat(),
                    "end_time": datetime(2026, 8, 6, start_hour + 2, 0).isoformat(),
                    "capacity": 1,
                },
            ).json()["id"]
        )

    response = authenticated_client.post("/shifts/generate-plan?max_shifts_per_user=3&planner_seed=11")
    assert response.status_code == 200

    assignments = [
        assignment for assignment in response.json()["assignments"]
        if assignment["user_id"] == user_id and assignment["shift_id"] in shift_ids
    ]

    assert {assignment["shift_id"] for assignment in assignments} == set(shift_ids)


def test_generate_shift_plan_avoids_forced_triple_when_alternative_exists(authenticated_client):
    primary_user_id = create_participant_user(
        authenticated_client,
        "primarytriple@example.com",
        "primarytriple",
    )["id"]
    fallback_user_id = create_participant_user(
        authenticated_client,
        "fallbacktriple@example.com",
        "fallbacktriple",
    )["id"]
    login_as_coordinator(authenticated_client)

    shift_ids = []
    for start_hour in (14, 16, 18):
        shift = authenticated_client.post(
            "/shifts/",
            json={
                "title": f"Triple Avoidance {start_hour}",
                "start_time": datetime(2026, 8, 6, start_hour, 0).isoformat(),
                "end_time": datetime(2026, 8, 6, start_hour + 2, 0).isoformat(),
                "capacity": 1,
            },
        ).json()
        shift_ids.append(shift["id"])

    login_as_participant(authenticated_client)
    lookup_response = authenticated_client.post(
        "/users/lookup",
        json={"email": "fallbacktriple@example.com"},
    )
    assert lookup_response.status_code == 200

    first_two_shift_ids = shift_ids[:2]
    for shift_id in first_two_shift_ids:
        opt_out_response = authenticated_client.post(
            "/shifts/user-opt-out",
            json={"user_id": fallback_user_id, "shift_id": shift_id},
        )
        assert opt_out_response.status_code == 200

    login_as_coordinator(authenticated_client)

    response = authenticated_client.post("/shifts/generate-plan?max_shifts_per_user=3&planner_seed=11")
    assert response.status_code == 200
    assignments = response.json()["assignments"]

    primary_assignments = [
        assignment for assignment in assignments
        if assignment["user_id"] == primary_user_id and assignment["shift_id"] in shift_ids
    ]
    fallback_assignments = [
        assignment for assignment in assignments
        if assignment["user_id"] == fallback_user_id and assignment["shift_id"] in shift_ids
    ]

    assert len(primary_assignments) == 2
    assert len(fallback_assignments) == 1
    assert fallback_assignments[0]["shift_id"] == shift_ids[2]


def test_generate_shift_plan_respects_under_16_evening_restriction(authenticated_client):
    under_16_id = create_participant_user(
        authenticated_client,
        "under16-planner@example.com",
        "under16planner",
        is_under_16=True,
    )["id"]
    adult_id = create_participant_user(
        authenticated_client,
        "adult-planner@example.com",
        "adultplanner",
    )["id"]
    login_as_coordinator(authenticated_client)

    day_shift_id = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Day Shift",
            "start_time": datetime(2026, 8, 7, 18, 0).isoformat(),
            "end_time": datetime(2026, 8, 7, 20, 0).isoformat(),
            "capacity": 1,
        },
    ).json()["id"]

    evening_shift_id = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Evening Shift",
            "start_time": datetime(2026, 8, 7, 20, 0).isoformat(),
            "end_time": datetime(2026, 8, 7, 22, 0).isoformat(),
            "capacity": 1,
        },
    ).json()["id"]

    response = authenticated_client.post("/shifts/generate-plan?max_shifts_per_user=2&planner_seed=23")
    assert response.status_code == 200

    assignments = response.json()["assignments"]
    assigned_user_by_shift = {
        assignment["shift_id"]: assignment["user_id"]
        for assignment in assignments
    }

    assert assigned_user_by_shift[evening_shift_id] == adult_id
    assert assigned_user_by_shift[day_shift_id] == under_16_id


def test_generate_shift_plan_seed_is_reproducible(authenticated_client):
    for index in range(3):
        create_participant_user(
            authenticated_client,
            f"seeded-{index}@example.com",
            f"seeded{index}",
        )
    login_as_coordinator(authenticated_client)

    shift_id = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Seeded Tie Breaker",
            "start_time": datetime(2026, 8, 6, 14, 0).isoformat(),
            "end_time": datetime(2026, 8, 6, 16, 0).isoformat(),
            "capacity": 1,
        },
    ).json()["id"]

    first_response = authenticated_client.post("/shifts/generate-plan?planner_seed=12345")
    second_response = authenticated_client.post("/shifts/generate-plan?planner_seed=12345")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    assert first_data["planner"]["seed"] == 12345
    assert second_data["planner"]["seed"] == 12345

    first_assignments = [
        assignment for assignment in first_data["assignments"] if assignment["shift_id"] == shift_id
    ]
    second_assignments = [
        assignment for assignment in second_data["assignments"] if assignment["shift_id"] == shift_id
    ]

    assert first_assignments == second_assignments


def test_generate_shift_plan_uses_seed_to_offer_alternatives(authenticated_client):
    for index in range(3):
        create_participant_user(
            authenticated_client,
            f"alternative-{index}@example.com",
            f"alternative{index}",
        )
    login_as_coordinator(authenticated_client)

    shift_id = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Alternative Tie Breaker",
            "start_time": datetime(2026, 8, 6, 18, 0).isoformat(),
            "end_time": datetime(2026, 8, 6, 20, 0).isoformat(),
            "capacity": 1,
        },
    ).json()["id"]

    assigned_user_ids = set()
    randomized_decision_counts = set()

    for seed in range(1, 6):
        response = authenticated_client.post(f"/shifts/generate-plan?planner_seed={seed}")
        assert response.status_code == 200
        data = response.json()

        shift_assignments = [
            assignment for assignment in data["assignments"] if assignment["shift_id"] == shift_id
        ]
        assert len(shift_assignments) == 1
        assigned_user_ids.add(shift_assignments[0]["user_id"])
        randomized_decision_counts.add(data["planner"]["randomized_decisions"])

    assert len(assigned_user_ids) > 1
    assert randomized_decision_counts == {1}


def test_late_night_shifts_belong_to_previous_festival_night():
    """00:00-02:00 should count as the previous festival night for planner scoring."""
    thursday_night_extension = SimpleNamespace(
        start_time=datetime(2026, 8, 7, 0, 0),
        end_time=datetime(2026, 8, 7, 2, 0),
    )
    friday_night_extension = SimpleNamespace(
        start_time=datetime(2026, 8, 8, 0, 0),
        end_time=datetime(2026, 8, 8, 2, 0),
    )
    saturday_night_extension = SimpleNamespace(
        start_time=datetime(2026, 8, 9, 0, 0),
        end_time=datetime(2026, 8, 9, 2, 0),
    )

    assert get_shift_day_key(thursday_night_extension) == "2026-08-06"
    assert get_shift_day_key(friday_night_extension) == "2026-08-07"
    assert get_shift_day_key(saturday_night_extension) == "2026-08-08"
    assert is_priority_evening_shift(thursday_night_extension) is True
    assert is_priority_evening_shift(friday_night_extension) is True
    assert is_priority_evening_shift(saturday_night_extension) is True
