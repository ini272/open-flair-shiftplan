from datetime import datetime, timedelta


def login_as_participant(client):
    response = client.post("/auth/login", json={"access_code": "weinzelt2026"})
    assert response.status_code == 200


def login_as_coordinator(client):
    response = client.post("/auth/login", json={"access_code": "koordination2026"})
    assert response.status_code == 200


def create_participant_user(client, email, username):
    login_as_participant(client)
    response = client.post("/users/", json={"email": email, "username": username})
    assert response.status_code == 201
    return response.json()


def continue_as_participant(client, email):
    login_as_participant(client)
    response = client.post("/users/lookup", json={"email": email})
    assert response.status_code == 200


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


def test_participants_only_see_their_own_assignments_after_plan_release(authenticated_client):
    first_user = create_participant_user(
        authenticated_client,
        "published-first@example.com",
        "publishedfirst",
    )
    second_user = create_participant_user(
        authenticated_client,
        "published-second@example.com",
        "publishedsecond",
    )
    login_as_coordinator(authenticated_client)

    start_time = datetime.utcnow() + timedelta(days=1)
    first_shift = create_shift(authenticated_client, "Weinzelt", start_time)
    second_shift = create_shift(authenticated_client, "Bierwagen", start_time)
    assert authenticated_client.post(
        "/shifts/users/",
        json={"shift_id": first_shift["id"], "user_id": first_user["id"]},
    ).status_code == 200
    assert authenticated_client.post(
        "/shifts/users/",
        json={"shift_id": second_shift["id"], "user_id": second_user["id"]},
    ).status_code == 200

    continue_as_participant(authenticated_client, first_user["email"])
    hidden_response = authenticated_client.get("/shifts/my-assignments")
    assert hidden_response.status_code == 200
    assert hidden_response.json() == {"is_released": False, "assignments": []}
    assert authenticated_client.get("/shifts/plan-publication").status_code == 403
    assert authenticated_client.put(
        "/shifts/plan-publication",
        json={"is_released": True},
    ).status_code == 403

    login_as_coordinator(authenticated_client)
    release_response = authenticated_client.put(
        "/shifts/plan-publication",
        json={"is_released": True},
    )
    assert release_response.status_code == 200
    assert release_response.json() == {"is_released": True}

    continue_as_participant(authenticated_client, first_user["email"])
    visible_response = authenticated_client.get("/shifts/my-assignments")
    assert visible_response.status_code == 200
    assert visible_response.json()["is_released"] is True
    assert visible_response.json()["assignments"] == [{
        "shift_id": first_shift["id"],
        "title": "Weinzelt",
        "start_time": first_shift["start_time"],
        "end_time": first_shift["end_time"],
        "assigned_via": "individual",
        "group_name": None,
    }]

    login_as_coordinator(authenticated_client)
    withdraw_response = authenticated_client.put(
        "/shifts/plan-publication",
        json={"is_released": False},
    )
    assert withdraw_response.status_code == 200

    continue_as_participant(authenticated_client, first_user["email"])
    assert authenticated_client.get("/shifts/my-assignments").json() == {
        "is_released": False,
        "assignments": [],
    }


def test_published_group_assignments_are_visible_to_each_group_member(authenticated_client):
    group_response = authenticated_client.post(
        "/groups/",
        json={"name": "Published Group"},
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    first_user = create_participant_user(
        authenticated_client,
        "published-group-one@example.com",
        "publishedgroupone",
    )
    second_user = create_participant_user(
        authenticated_client,
        "published-group-two@example.com",
        "publishedgrouptwo",
    )
    login_as_coordinator(authenticated_client)
    assert authenticated_client.post(f"/groups/{group_id}/users/{first_user['id']}").status_code == 200
    assert authenticated_client.post(f"/groups/{group_id}/users/{second_user['id']}").status_code == 200

    shift = create_shift(
        authenticated_client,
        "Bierwagen",
        datetime.utcnow() + timedelta(days=1),
    )
    assert authenticated_client.post(
        "/shifts/groups/",
        json={"shift_id": shift["id"], "group_id": group_id},
    ).status_code == 200
    assert authenticated_client.put(
        "/shifts/plan-publication",
        json={"is_released": True},
    ).status_code == 200

    continue_as_participant(authenticated_client, second_user["email"])
    response = authenticated_client.get("/shifts/my-assignments")
    assert response.status_code == 200
    assert response.json()["assignments"] == [{
        "shift_id": shift["id"],
        "title": "Bierwagen",
        "start_time": shift["start_time"],
        "end_time": shift["end_time"],
        "assigned_via": "group",
        "group_name": "Published Group",
    }]


def test_plan_publication_status_is_only_available_to_coordinators(authenticated_client):
    coordinator_response = authenticated_client.get("/shifts/plan-publication")
    assert coordinator_response.status_code == 200
    assert coordinator_response.json() == {"is_released": False}

    login_as_participant(authenticated_client)
    participant_response = authenticated_client.get("/shifts/plan-publication")
    assert participant_response.status_code == 403
