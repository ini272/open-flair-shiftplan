from datetime import datetime, timedelta


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
        json={
            "email": email,
            "username": username,
            "is_under_16": is_under_16,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_shift(client, title, start_time):
    response = client.post(
        "/shifts/",
        json={
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=2)).isoformat(),
            "capacity": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


def opt_out_status(client, shift_id, user_id):
    response = client.get(f"/shifts/opt-out-status/{shift_id}/{user_id}")
    assert response.status_code == 200
    return response.json()["is_opted_out"]


def test_bulk_availability_saves_and_restores_individual_selection(authenticated_client):
    user = create_participant_user(
        authenticated_client,
        "bulk-user@example.com",
        "bulkuser",
    )
    login_as_coordinator(authenticated_client)

    start_time = datetime.utcnow() + timedelta(days=1)
    weinzelt_shift = create_shift(authenticated_client, "Weinzelt", start_time)
    bierwagen_shift = create_shift(authenticated_client, "Bierwagen", start_time)
    later_shift = create_shift(
        authenticated_client,
        "Weinzelt spaeter",
        start_time + timedelta(hours=2),
    )
    shift_ids = [weinzelt_shift["id"], bierwagen_shift["id"], later_shift["id"]]

    opt_out_response = authenticated_client.put(
        "/shifts/availability",
        json={
            "user_id": user["id"],
            "changes": [
                {"shift_id": shift_id, "is_available": False}
                for shift_id in shift_ids
            ],
        },
    )
    assert opt_out_response.status_code == 200
    assert opt_out_response.json()["updated_shift_ids"] == shift_ids
    assert all(opt_out_status(authenticated_client, shift_id, user["id"]) for shift_id in shift_ids)

    opt_in_response = authenticated_client.put(
        "/shifts/availability",
        json={
            "user_id": user["id"],
            "changes": [
                {"shift_id": shift_id, "is_available": True}
                for shift_id in shift_ids
            ],
        },
    )
    assert opt_in_response.status_code == 200
    assert not any(opt_out_status(authenticated_client, shift_id, user["id"]) for shift_id in shift_ids)


def test_bulk_availability_rejects_invalid_request_without_partial_update(authenticated_client):
    user = create_participant_user(
        authenticated_client,
        "bulk-atomic@example.com",
        "bulkatomic",
    )
    login_as_coordinator(authenticated_client)

    shift = create_shift(
        authenticated_client,
        "Atomare Verfuegbarkeit",
        datetime.utcnow() + timedelta(days=1),
    )
    response = authenticated_client.put(
        "/shifts/availability",
        json={
            "user_id": user["id"],
            "changes": [
                {"shift_id": shift["id"], "is_available": False},
                {"shift_id": 999999, "is_available": False},
            ],
        },
    )

    assert response.status_code == 404
    assert opt_out_status(authenticated_client, shift["id"], user["id"]) is False


def test_bulk_availability_updates_all_group_members(authenticated_client):
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Bulk Availability Group"},
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    first_user = create_participant_user(
        authenticated_client,
        "bulk-group-one@example.com",
        "bulkgroupone",
    )
    second_user = create_participant_user(
        authenticated_client,
        "bulk-group-two@example.com",
        "bulkgrouptwo",
    )
    login_as_coordinator(authenticated_client)
    assert authenticated_client.post(f"/groups/{group_id}/users/{first_user['id']}").status_code == 200
    assert authenticated_client.post(f"/groups/{group_id}/users/{second_user['id']}").status_code == 200

    start_time = datetime.utcnow() + timedelta(days=1)
    weinzelt_shift = create_shift(authenticated_client, "Weinzelt", start_time)
    bierwagen_shift = create_shift(authenticated_client, "Bierwagen", start_time)
    shift_ids = [weinzelt_shift["id"], bierwagen_shift["id"]]

    response = authenticated_client.put(
        "/shifts/availability",
        json={
            "group_id": group_id,
            "changes": [
                {"shift_id": shift_id, "is_available": False}
                for shift_id in shift_ids
            ],
        },
    )

    assert response.status_code == 200
    for user in (first_user, second_user):
        assert all(opt_out_status(authenticated_client, shift_id, user["id"]) for shift_id in shift_ids)


def test_bulk_availability_rejects_evening_opt_in_for_under_16(authenticated_client):
    user = create_participant_user(
        authenticated_client,
        "bulk-under16@example.com",
        "bulkunder16",
        is_under_16=True,
    )
    login_as_coordinator(authenticated_client)
    evening_start = (datetime.utcnow() + timedelta(days=1)).replace(
        hour=20,
        minute=0,
        second=0,
        microsecond=0,
    )
    evening_shift = create_shift(authenticated_client, "Abendschicht", evening_start)

    response = authenticated_client.put(
        "/shifts/availability",
        json={
            "user_id": user["id"],
            "changes": [{"shift_id": evening_shift["id"], "is_available": True}],
        },
    )

    assert response.status_code == 400
    assert "under 16" in response.json()["detail"].lower()
