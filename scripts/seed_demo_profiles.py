#!/usr/bin/env python3
"""Seed deterministic demo users and groups with distinct shift profiles via the public API."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Literal

import requests

LocationPreference = Literal["both", "weinzelt", "bierwagen"]
ShiftPredicate = Callable[[dict], bool]
DEFAULT_MAX_GROUP_SIZE = 3


@dataclass(frozen=True)
class DemoUserProfile:
    username: str
    email: str
    location_preference: LocationPreference
    is_under_16: bool
    is_available: ShiftPredicate


@dataclass(frozen=True)
class DemoGroupProfile:
    name: str
    members: tuple[DemoUserProfile, ...]
    location_preference: LocationPreference
    is_available: ShiftPredicate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed deterministic demo users, groups, and shift opt-outs via API."
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the app/API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--participant-access-code",
        default=os.getenv("EVENT_CODE", "weinzelt2026"),
        help="Participant access code",
    )
    parser.add_argument(
        "--coordinator-access-code",
        default=os.getenv("COORDINATOR_CODE", "koordination2026"),
        help="Coordinator access code",
    )
    parser.add_argument(
        "--coordinator-name",
        default="Demo Profil Koordination",
        help="Coordinator account name to create or update",
    )
    parser.add_argument(
        "--coordinator-email",
        default="demo-profil-koordination@example.com",
        help="Coordinator account email to create or update",
    )
    return parser.parse_args()


def api_error_detail(error: requests.HTTPError) -> str:
    try:
        payload = error.response.json()
    except Exception:
        return error.response.text
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    return error.response.text


def login(base_url: str, access_code: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{base_url.rstrip('/')}/auth/login",
        json={"access_code": access_code},
        timeout=20,
    )
    response.raise_for_status()
    return session


def lookup_user(session: requests.Session, base_url: str, email: str) -> dict | None:
    response = session.post(
        f"{base_url.rstrip('/')}/users/lookup",
        json={"email": email},
        timeout=20,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def create_user(session: requests.Session, base_url: str, profile: DemoUserProfile) -> dict:
    response = session.post(
        f"{base_url.rstrip('/')}/users/",
        json={
            "username": profile.username,
            "email": profile.email,
            "is_under_16": profile.is_under_16,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def create_or_update_coordinator(
    session: requests.Session,
    base_url: str,
    *,
    email: str,
    username: str,
) -> dict:
    existing = lookup_user(session, base_url, email)
    if existing is None:
        response = session.post(
            f"{base_url.rstrip('/')}/users/",
            json={
                "username": username,
                "email": email,
                "is_under_16": False,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    if not existing.get("is_coordinator"):
        raise ValueError(
            f"Existing user {email} is not a coordinator account. Remove it first or choose another email."
        )

    return update_user(
        session,
        base_url,
        user_id=existing["id"],
        username=username,
        location_preference="both",
    )


def get_user(session: requests.Session, base_url: str, user_id: int) -> dict:
    response = session.get(f"{base_url.rstrip('/')}/users/{user_id}", timeout=20)
    response.raise_for_status()
    return response.json()


def update_user(
    session: requests.Session,
    base_url: str,
    *,
    user_id: int,
    username: str,
    location_preference: LocationPreference,
) -> dict:
    response = session.put(
        f"{base_url.rstrip('/')}/users/{user_id}",
        json={
            "username": username,
            "location_preference": location_preference,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def create_or_lookup_user(
    participant_session: requests.Session,
    coordinator_session: requests.Session,
    base_url: str,
    profile: DemoUserProfile,
) -> dict:
    existing = lookup_user(coordinator_session, base_url, profile.email)
    if existing is None:
        return create_user(participant_session, base_url, profile)

    if existing.get("is_coordinator"):
        raise ValueError(
            f"Existing user {profile.email} is a coordinator account. Pick another email or remove it first."
        )

    if bool(existing.get("is_under_16")) != profile.is_under_16:
        raise ValueError(
            f"Existing user {profile.email} has is_under_16={existing.get('is_under_16')}, "
            f"expected {profile.is_under_16}. Remove the user first or pick another email."
        )

    return update_user(
        coordinator_session,
        base_url,
        user_id=existing["id"],
        username=profile.username,
        location_preference=profile.location_preference,
    )


def read_groups(session: requests.Session, base_url: str) -> list[dict]:
    response = session.get(f"{base_url.rstrip('/')}/groups/", timeout=20)
    response.raise_for_status()
    return response.json()


def create_group(session: requests.Session, base_url: str, name: str) -> dict:
    response = session.post(
        f"{base_url.rstrip('/')}/groups/",
        json={"name": name},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def create_or_lookup_group(session: requests.Session, base_url: str, name: str) -> dict:
    for group in read_groups(session, base_url):
        if group.get("name") == name:
            return group
    return create_group(session, base_url, name)


def read_group(session: requests.Session, base_url: str, group_id: int) -> dict:
    response = session.get(f"{base_url.rstrip('/')}/groups/{group_id}", timeout=20)
    response.raise_for_status()
    return response.json()


def update_group(
    session: requests.Session,
    base_url: str,
    *,
    group_id: int,
    location_preference: LocationPreference,
) -> dict:
    response = session.put(
        f"{base_url.rstrip('/')}/groups/{group_id}",
        json={"location_preference": location_preference},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def remove_user_from_group(session: requests.Session, base_url: str, user_id: int) -> None:
    response = session.delete(f"{base_url.rstrip('/')}/groups/users/{user_id}", timeout=20)
    response.raise_for_status()


def add_user_to_group(
    session: requests.Session,
    base_url: str,
    *,
    group_id: int,
    user_id: int,
) -> None:
    response = session.post(
        f"{base_url.rstrip('/')}/groups/{group_id}/users/{user_id}",
        params={"max_group_size": DEFAULT_MAX_GROUP_SIZE},
        timeout=20,
    )
    response.raise_for_status()


def read_shifts(session: requests.Session, base_url: str) -> list[dict]:
    response = session.get(f"{base_url.rstrip('/')}/shifts/", timeout=20)
    response.raise_for_status()
    shifts = response.json()
    return sorted(shifts, key=lambda shift: shift["start_time"])


def read_user_opt_outs(session: requests.Session, base_url: str, user_id: int) -> list[dict]:
    response = session.get(f"{base_url.rstrip('/')}/shifts/user-opt-outs/{user_id}", timeout=20)
    response.raise_for_status()
    return response.json()


def read_group_opt_outs(session: requests.Session, base_url: str, group_id: int) -> list[dict]:
    response = session.get(
        f"{base_url.rstrip('/')}/shifts/group-opt-outs/{group_id}",
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def opt_out_user(session: requests.Session, base_url: str, *, shift_id: int, user_id: int) -> None:
    response = session.post(
        f"{base_url.rstrip('/')}/shifts/user-opt-out",
        json={"shift_id": shift_id, "user_id": user_id},
        timeout=20,
    )
    response.raise_for_status()


def opt_in_user(session: requests.Session, base_url: str, *, shift_id: int, user_id: int) -> None:
    response = session.post(
        f"{base_url.rstrip('/')}/shifts/user-opt-in",
        json={"shift_id": shift_id, "user_id": user_id},
        timeout=20,
    )
    response.raise_for_status()


def opt_out_group(session: requests.Session, base_url: str, *, shift_id: int, group_id: int) -> None:
    response = session.post(
        f"{base_url.rstrip('/')}/shifts/group-opt-out",
        json={"shift_id": shift_id, "group_id": group_id},
        timeout=20,
    )
    response.raise_for_status()


def opt_in_group(session: requests.Session, base_url: str, *, shift_id: int, group_id: int) -> None:
    response = session.post(
        f"{base_url.rstrip('/')}/shifts/group-opt-in",
        json={"shift_id": shift_id, "group_id": group_id},
        timeout=20,
    )
    response.raise_for_status()


def parse_shift_start(shift: dict) -> datetime:
    return datetime.fromisoformat(shift["start_time"])


def shift_location(shift: dict) -> str:
    title = shift["title"].lower()
    if "weinzelt" in title:
        return "weinzelt"
    if "bierwagen" in title:
        return "bierwagen"
    return "both"


def slot_key(shift: dict) -> tuple[int, int]:
    start = parse_shift_start(shift)
    return start.weekday(), start.hour


def is_evening_or_late(shift: dict) -> bool:
    hour = parse_shift_start(shift).hour
    return hour >= 18 or hour < 6


def is_daytime(shift: dict) -> bool:
    hour = parse_shift_start(shift).hour
    return 12 <= hour < 18


def is_under_16_allowed_slot(shift: dict) -> bool:
    hour = parse_shift_start(shift).hour
    return 12 <= hour < 20


def allow_all(_: dict) -> bool:
    return True


def allow_daytime(shift: dict) -> bool:
    return is_daytime(shift)


def allow_evenings(shift: dict) -> bool:
    return is_evening_or_late(shift)


def allow_selected_slots(allowed_slots: set[tuple[int, int]]) -> ShiftPredicate:
    return lambda shift: slot_key(shift) in allowed_slots


def allow_all_except(blocked_slots: set[tuple[int, int]]) -> ShiftPredicate:
    return lambda shift: slot_key(shift) not in blocked_slots


def build_demo_profiles() -> tuple[list[DemoUserProfile], list[DemoGroupProfile]]:
    users = [
        DemoUserProfile(
            username="Demo Alex Offen",
            email="demo-alex-offen@example.com",
            location_preference="both",
            is_under_16=False,
            is_available=allow_all,
        ),
        DemoUserProfile(
            username="Demo Britta Tag",
            email="demo-britta-tag@example.com",
            location_preference="both",
            is_under_16=False,
            is_available=allow_daytime,
        ),
        DemoUserProfile(
            username="Demo Cem Abend",
            email="demo-cem-abend@example.com",
            location_preference="both",
            is_under_16=False,
            is_available=allow_evenings,
        ),
        DemoUserProfile(
            username="Demo Daria Weinzelt",
            email="demo-daria-weinzelt@example.com",
            location_preference="weinzelt",
            is_under_16=False,
            is_available=allow_all_except({(3, 12), (5, 20), (6, 20)}),
        ),
        DemoUserProfile(
            username="Demo Enno Bierwagen",
            email="demo-enno-bierwagen@example.com",
            location_preference="bierwagen",
            is_under_16=False,
            is_available=allow_all_except({(4, 12), (4, 14), (6, 18)}),
        ),
        DemoUserProfile(
            username="Demo Frieda Knap",
            email="demo-frieda-knapp@example.com",
            location_preference="both",
            is_under_16=False,
            is_available=allow_selected_slots({(4, 18), (4, 20), (5, 18), (6, 14)}),
        ),
        DemoUserProfile(
            username="Demo Greta U16",
            email="demo-greta-u16@example.com",
            location_preference="both",
            is_under_16=True,
            is_available=is_under_16_allowed_slot,
        ),
    ]

    groups = [
        DemoGroupProfile(
            name="Demo Ina & Joris",
            members=(
                DemoUserProfile(
                    username="Demo Ina Team",
                    email="demo-ina-team@example.com",
                    location_preference="both",
                    is_under_16=False,
                    is_available=allow_evenings,
                ),
                DemoUserProfile(
                    username="Demo Joris Team",
                    email="demo-joris-team@example.com",
                    location_preference="both",
                    is_under_16=False,
                    is_available=allow_evenings,
                ),
            ),
            location_preference="bierwagen",
            is_available=allow_selected_slots({(3, 18), (3, 20), (4, 20), (5, 20), (5, 22)}),
        ),
        DemoGroupProfile(
            name="Demo Kira & Lutz",
            members=(
                DemoUserProfile(
                    username="Demo Kira Team",
                    email="demo-kira-team@example.com",
                    location_preference="both",
                    is_under_16=False,
                    is_available=allow_daytime,
                ),
                DemoUserProfile(
                    username="Demo Lutz Team",
                    email="demo-lutz-team@example.com",
                    location_preference="both",
                    is_under_16=False,
                    is_available=allow_daytime,
                ),
            ),
            location_preference="weinzelt",
            is_available=allow_selected_slots({(3, 12), (3, 14), (4, 12), (4, 14), (6, 12), (6, 14)}),
        ),
        DemoGroupProfile(
            name="Demo Mara, Nils & Olga",
            members=(
                DemoUserProfile(
                    username="Demo Mara Team",
                    email="demo-mara-team@example.com",
                    location_preference="both",
                    is_under_16=False,
                    is_available=allow_all,
                ),
                DemoUserProfile(
                    username="Demo Nils Team",
                    email="demo-nils-team@example.com",
                    location_preference="both",
                    is_under_16=False,
                    is_available=allow_all,
                ),
                DemoUserProfile(
                    username="Demo Olga Team",
                    email="demo-olga-team@example.com",
                    location_preference="both",
                    is_under_16=False,
                    is_available=allow_all,
                ),
            ),
            location_preference="both",
            is_available=allow_all_except({(4, 12), (5, 12), (5, 14), (6, 20)}),
        ),
    ]

    return users, groups


def sync_user_profile(
    participant_session: requests.Session,
    coordinator_session: requests.Session,
    base_url: str,
    profile: DemoUserProfile,
    shifts: list[dict],
) -> dict:
    user = create_or_lookup_user(participant_session, coordinator_session, base_url, profile)
    user = get_user(coordinator_session, base_url, user["id"])
    if user.get("group_id") is not None:
        remove_user_from_group(coordinator_session, base_url, user["id"])

    user = update_user(
        coordinator_session,
        base_url,
        user_id=user["id"],
        username=profile.username,
        location_preference=profile.location_preference,
    )

    for shift in read_user_opt_outs(coordinator_session, base_url, user["id"]):
        opt_in_user(coordinator_session, base_url, shift_id=shift["id"], user_id=user["id"])

    opted_out_count = 0
    for shift in shifts:
        if not profile.is_available(shift):
            opt_out_user(coordinator_session, base_url, shift_id=shift["id"], user_id=user["id"])
            opted_out_count += 1

    return {"user": user, "opted_out_count": opted_out_count}


def sync_group_profile(
    participant_session: requests.Session,
    coordinator_session: requests.Session,
    base_url: str,
    group_profile: DemoGroupProfile,
    shifts: list[dict],
) -> dict:
    member_records = []
    for member in group_profile.members:
        user = create_or_lookup_user(participant_session, coordinator_session, base_url, member)
        user = get_user(coordinator_session, base_url, user["id"])
        if user.get("group_id") is not None:
            remove_user_from_group(coordinator_session, base_url, user["id"])
        member_records.append(user)

    group = create_or_lookup_group(coordinator_session, base_url, group_profile.name)
    for user in member_records:
        add_user_to_group(coordinator_session, base_url, group_id=group["id"], user_id=user["id"])

    group = update_group(
        coordinator_session,
        base_url,
        group_id=group["id"],
        location_preference=group_profile.location_preference,
    )
    group = read_group(coordinator_session, base_url, group["id"])

    for shift in read_group_opt_outs(coordinator_session, base_url, group["id"]):
        opt_in_group(coordinator_session, base_url, shift_id=shift["id"], group_id=group["id"])

    opted_out_count = 0
    for shift in shifts:
        if not group_profile.is_available(shift):
            opt_out_group(coordinator_session, base_url, shift_id=shift["id"], group_id=group["id"])
            opted_out_count += 1

    return {"group": group, "opted_out_count": opted_out_count}


def main() -> int:
    args = parse_args()
    participant_session = login(args.api_url, args.participant_access_code)
    coordinator_session = login(args.api_url, args.coordinator_access_code)

    shifts = read_shifts(coordinator_session, args.api_url)
    if not shifts:
        raise ValueError(
            "No shifts found. Create shifts first with scripts/create_production_shifts.py."
        )

    user_profiles, group_profiles = build_demo_profiles()

    coordinator_user = create_or_update_coordinator(
        coordinator_session,
        args.api_url,
        email=args.coordinator_email,
        username=args.coordinator_name,
    )

    print(f"Found {len(shifts)} shifts.")
    print(
        f"Coordinator user ready: {coordinator_user['username']} <{coordinator_user['email']}>"
    )
    print(f"Seeding {len(user_profiles)} solo demo users...")
    for profile in user_profiles:
        result = sync_user_profile(
            participant_session,
            coordinator_session,
            args.api_url,
            profile,
            shifts,
        )
        user = result["user"]
        print(
            f"  user: {user['username']} <{user['email']}>"
            f" | pref={user['location_preference']}"
            f" | under16={user['is_under_16']}"
            f" | opted_out={result['opted_out_count']}"
        )

    print(f"Seeding {len(group_profiles)} demo groups...")
    for group_profile in group_profiles:
        result = sync_group_profile(
            participant_session,
            coordinator_session,
            args.api_url,
            group_profile,
            shifts,
        )
        group = result["group"]
        member_names = ", ".join(user["username"] for user in group["users"])
        print(
            f"  group: {group['name']}"
            f" | pref={group['location_preference']}"
            f" | members={member_names}"
            f" | opted_out={result['opted_out_count']}"
        )

    print()
    print("Demo profiles seeded successfully.")
    print(f"  coordinator email: {args.coordinator_email}")
    print(f"  participant access code: {args.participant_access_code}")
    print(f"  coordinator access code: {args.coordinator_access_code}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as error:
        print(f"HTTP error: {error.response.status_code} {api_error_detail(error)}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
