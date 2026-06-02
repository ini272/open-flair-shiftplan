from datetime import datetime, timedelta


def test_user_and_group_location_preference_defaults_and_updates(authenticated_client):
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "location-pref-user@example.com", "username": "locationprefuser"},
    )
    assert user_response.status_code == 201
    user_data = user_response.json()
    assert user_data["location_preference"] == "both"

    updated_user_response = authenticated_client.put(
        f"/users/{user_data['id']}",
        json={"location_preference": "bierwagen"},
    )
    assert updated_user_response.status_code == 200
    assert updated_user_response.json()["location_preference"] == "bierwagen"

    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Location Preference Group"},
    )
    assert group_response.status_code == 201
    group_data = group_response.json()
    assert group_data["location_preference"] == "both"

    updated_group_response = authenticated_client.put(
        f"/groups/{group_data['id']}",
        json={"location_preference": "weinzelt"},
    )
    assert updated_group_response.status_code == 200
    assert updated_group_response.json()["location_preference"] == "weinzelt"


def test_get_available_users_uses_timeslot_availability(authenticated_client):
    user_response = authenticated_client.post(
        "/users/",
        json={"email": "slot-available@example.com", "username": "slotavailable"},
    )
    user_id = user_response.json()["id"]

    start_time = datetime(2026, 8, 6, 18, 0)
    end_time = start_time + timedelta(hours=2)

    weinzelt_shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Weinzelt Abend",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 1,
        },
    )
    weinzelt_shift_id = weinzelt_shift_response.json()["id"]

    bierwagen_shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Bierwagen Abend",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 1,
        },
    )
    bierwagen_shift_id = bierwagen_shift_response.json()["id"]

    opt_out_response = authenticated_client.post(
        "/shifts/user-opt-out",
        json={"shift_id": weinzelt_shift_id, "user_id": user_id},
    )
    assert opt_out_response.status_code == 200

    available_users_response = authenticated_client.get(f"/shifts/available-users/{weinzelt_shift_id}")
    assert available_users_response.status_code == 200
    available_user_ids = {user["id"] for user in available_users_response.json()}

    assert bierwagen_shift_id != weinzelt_shift_id
    assert user_id in available_user_ids


def test_generate_shift_plan_prefers_location_without_requiring_it(authenticated_client):
    user1_response = authenticated_client.post(
        "/users/",
        json={"email": "pref-wz@example.com", "username": "prefwz"},
    )
    user1_id = user1_response.json()["id"]

    user2_response = authenticated_client.post(
        "/users/",
        json={"email": "pref-bw@example.com", "username": "prefbw"},
    )
    user2_id = user2_response.json()["id"]

    authenticated_client.put(
        f"/users/{user1_id}",
        json={"location_preference": "weinzelt"},
    )
    authenticated_client.put(
        f"/users/{user2_id}",
        json={"location_preference": "bierwagen"},
    )

    start_time = datetime(2026, 8, 7, 16, 0)
    end_time = start_time + timedelta(hours=2)

    weinzelt_shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Weinzelt Nachmittagsdienst",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 1,
        },
    )
    weinzelt_shift_id = weinzelt_shift_response.json()["id"]

    bierwagen_shift_response = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Bierwagen Nachmittagsdienst",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 1,
        },
    )
    bierwagen_shift_id = bierwagen_shift_response.json()["id"]

    authenticated_client.post(
        "/shifts/user-opt-out",
        json={"shift_id": bierwagen_shift_id, "user_id": user1_id},
    )
    authenticated_client.post(
        "/shifts/user-opt-out",
        json={"shift_id": weinzelt_shift_id, "user_id": user2_id},
    )

    response = authenticated_client.post("/shifts/generate-plan")
    assert response.status_code == 200

    assignments = response.json()["assignments"]
    assigned_user_by_shift = {
        assignment["shift_id"]: assignment["user_id"]
        for assignment in assignments
    }

    assert assigned_user_by_shift[weinzelt_shift_id] == user1_id
    assert assigned_user_by_shift[bierwagen_shift_id] == user2_id
