from datetime import datetime, timedelta


def login_as_participant(client):
    response = client.post("/auth/login", json={"access_code": "weinzelt2026"})
    assert response.status_code == 200


def login_as_coordinator(client):
    response = client.post("/auth/login", json={"access_code": "koordination2026"})
    assert response.status_code == 200


def create_participant_user(client, email, username):
    login_as_participant(client)
    response = client.post(
        "/users/",
        json={"email": email, "username": username},
    )
    assert response.status_code == 201
    return response.json()


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


def test_group_member_can_update_group_location_preference(authenticated_client):
    group_id = authenticated_client.post(
        "/groups/",
        json={"name": "Shared Preference Group"},
    ).json()["id"]

    user_data = create_participant_user(
        authenticated_client,
        "group-location-member@example.com",
        "grouplocationmember",
    )
    user_id = user_data["id"]

    login_as_coordinator(authenticated_client)
    add_response = authenticated_client.post(f"/groups/{group_id}/users/{user_id}")
    assert add_response.status_code == 200

    login_as_participant(authenticated_client)
    lookup_response = authenticated_client.post(
        "/users/lookup",
        json={"email": "group-location-member@example.com"},
    )
    assert lookup_response.status_code == 200

    update_response = authenticated_client.put(
        f"/groups/{group_id}",
        json={"location_preference": "bierwagen"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["location_preference"] == "bierwagen"


def test_slot_opt_out_is_mirrored_to_parallel_shifts(authenticated_client):
    user_id = create_participant_user(
        authenticated_client,
        "slot-available@example.com",
        "slotavailable",
    )["id"]
    login_as_coordinator(authenticated_client)

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

    login_as_participant(authenticated_client)
    authenticated_client.post(
        "/users/lookup",
        json={"email": "slot-available@example.com"},
    )
    opt_out_response = authenticated_client.post(
        "/shifts/user-opt-out",
        json={"shift_id": weinzelt_shift_id, "user_id": user_id},
    )
    assert opt_out_response.status_code == 200

    login_as_coordinator(authenticated_client)
    user_opt_outs_response = authenticated_client.get(f"/shifts/user-opt-outs/{user_id}")
    assert user_opt_outs_response.status_code == 200
    opted_out_shift_ids = {shift["id"] for shift in user_opt_outs_response.json()}

    weinzelt_available_response = authenticated_client.get(f"/shifts/available-users/{weinzelt_shift_id}")
    assert weinzelt_available_response.status_code == 200
    weinzelt_available_user_ids = {user["id"] for user in weinzelt_available_response.json()}

    bierwagen_available_response = authenticated_client.get(f"/shifts/available-users/{bierwagen_shift_id}")
    assert bierwagen_available_response.status_code == 200
    bierwagen_available_user_ids = {user["id"] for user in bierwagen_available_response.json()}

    assert bierwagen_shift_id != weinzelt_shift_id
    assert opted_out_shift_ids == {weinzelt_shift_id, bierwagen_shift_id}
    assert user_id not in weinzelt_available_user_ids
    assert user_id not in bierwagen_available_user_ids


def test_generate_shift_plan_prefers_location_without_requiring_it(authenticated_client):
    user1_id = create_participant_user(
        authenticated_client,
        "pref-wz@example.com",
        "prefwz",
    )["id"]
    user2_id = create_participant_user(
        authenticated_client,
        "pref-bw@example.com",
        "prefbw",
    )["id"]

    login_as_coordinator(authenticated_client)
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

    response = authenticated_client.post("/shifts/generate-plan?max_shifts_per_user=1&planner_seed=17")
    assert response.status_code == 200

    assignments = response.json()["assignments"]
    assigned_user_by_shift = {
        assignment["shift_id"]: assignment["user_id"]
        for assignment in assignments
    }

    assert assigned_user_by_shift[weinzelt_shift_id] == user1_id
    assert assigned_user_by_shift[bierwagen_shift_id] == user2_id


def test_generate_shift_plan_respects_slot_opt_outs_for_parallel_shifts(authenticated_client):
    user_id = create_participant_user(
        authenticated_client,
        "parallel-opt-out@example.com",
        "paralleloptout",
    )["id"]
    login_as_coordinator(authenticated_client)

    start_time = datetime(2026, 8, 7, 18, 0)
    end_time = start_time + timedelta(hours=2)

    weinzelt_shift_id = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Weinzelt Parallel",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 1,
        },
    ).json()["id"]

    bierwagen_shift_id = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Bierwagen Parallel",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 1,
        },
    ).json()["id"]

    login_as_participant(authenticated_client)
    authenticated_client.post(
        "/users/lookup",
        json={"email": "parallel-opt-out@example.com"},
    )
    opt_out_response = authenticated_client.post(
        "/shifts/user-opt-out",
        json={"shift_id": weinzelt_shift_id, "user_id": user_id},
    )
    assert opt_out_response.status_code == 200

    login_as_coordinator(authenticated_client)
    response = authenticated_client.post("/shifts/generate-plan?max_shifts_per_user=1")
    assert response.status_code == 200

    assignments = response.json()["assignments"]
    assigned_shift_ids = {
        assignment["shift_id"]
        for assignment in assignments
        if assignment["user_id"] == user_id
    }

    assert weinzelt_shift_id not in assigned_shift_ids
    assert bierwagen_shift_id not in assigned_shift_ids


def test_group_slot_opt_out_is_idempotent_for_parallel_shifts(authenticated_client):
    group_id = authenticated_client.post(
        "/groups/",
        json={"name": "Parallel Slot Group"},
    ).json()["id"]

    user_id = create_participant_user(
        authenticated_client,
        "parallel-group@example.com",
        "parallelgroup",
    )["id"]

    login_as_coordinator(authenticated_client)
    add_to_group_response = authenticated_client.post(f"/groups/{group_id}/users/{user_id}")
    assert add_to_group_response.status_code == 200

    start_time = datetime(2026, 8, 7, 20, 0)
    end_time = start_time + timedelta(hours=2)

    weinzelt_shift_id = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Weinzelt Gruppen-Slot",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 2,
        },
    ).json()["id"]

    bierwagen_shift_id = authenticated_client.post(
        "/shifts/",
        json={
            "title": "Bierwagen Gruppen-Slot",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 2,
        },
    ).json()["id"]

    login_as_participant(authenticated_client)
    authenticated_client.post(
        "/users/lookup",
        json={"email": "parallel-group@example.com"},
    )

    first_response = authenticated_client.post(
        "/shifts/group-opt-out",
        json={"shift_id": weinzelt_shift_id, "group_id": group_id},
    )
    second_response = authenticated_client.post(
        "/shifts/group-opt-out",
        json={"shift_id": bierwagen_shift_id, "group_id": group_id},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    login_as_coordinator(authenticated_client)
    group_opt_outs_response = authenticated_client.get(f"/shifts/group-opt-outs/{group_id}")
    opted_out_shift_ids = {shift["id"] for shift in group_opt_outs_response.json()}

    assert opted_out_shift_ids == {weinzelt_shift_id, bierwagen_shift_id}
