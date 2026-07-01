#!/usr/bin/env python3
"""Seed a demo roster from demo_liste.txt via the public HTTP API."""

from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from dataclasses import dataclass

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo participants and teams via API.")
    parser.add_argument(
        "--roster",
        default="demo_liste.txt",
        help="Path to the roster text file (default: demo_liste.txt)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost",
        help="Base URL of the app/API (default: http://localhost)",
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
        default="Demo Koordination",
        help="Coordinator account name to create for the demo",
    )
    parser.add_argument(
        "--coordinator-email",
        default="demo-koordination@example.com",
        help="Coordinator account email to create for the demo",
    )
    parser.add_argument(
        "--skip-coordinator-user",
        action="store_true",
        help="Do not create a coordinator user account",
    )
    return parser.parse_args()


def parse_roster_file(path: str) -> tuple[list[str], list[list[str]]]:
    solos: list[str] = []
    teams: list[list[str]] = []
    section: str | None = None

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue

            lower = line.lower()
            if lower == "teilnehmer:":
                section = "participants"
                continue
            if lower == "teams:":
                section = "teams"
                continue

            if section == "participants":
                solos.append(line)
            elif section == "teams":
                teams.append([part.strip() for part in line.split(",") if part.strip()])

    if not solos and not teams:
        raise ValueError("No participants or teams found in roster file.")

    return solos, teams


def slugify_name(value: str) -> str:
    replacements = (
        ("ä", "ae"),
        ("ö", "oe"),
        ("ü", "ue"),
        ("Ä", "Ae"),
        ("Ö", "Oe"),
        ("Ü", "Ue"),
        ("ß", "ss"),
    )
    normalized = value
    for source, target in replacements:
        normalized = normalized.replace(source, target)
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "demo-user"


@dataclass
class AllocatedUser:
    raw_name: str
    display_name: str
    email: str


class UserAllocator:
    def __init__(self) -> None:
        self._name_counts: dict[str, int] = {}
        self._email_counts: dict[str, int] = {}

    def allocate(self, raw_name: str) -> AllocatedUser:
        base_name = raw_name.strip()
        visible_count = self._name_counts.get(base_name, 0) + 1
        self._name_counts[base_name] = visible_count
        display_name = base_name if visible_count == 1 else f"{base_name} {visible_count}"

        email_base = slugify_name(base_name)
        email_count = self._email_counts.get(email_base, 0) + 1
        self._email_counts[email_base] = email_count
        email_local = email_base if email_count == 1 else f"{email_base}-{email_count}"
        email = f"{email_local}@example.com"

        return AllocatedUser(raw_name=base_name, display_name=display_name, email=email)


def login(base_url: str, access_code: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{base_url.rstrip('/')}/auth/login",
        json={"access_code": access_code},
        timeout=15,
    )
    response.raise_for_status()
    return session


def api_error_detail(error: requests.HTTPError) -> str:
    try:
        payload = error.response.json()
    except Exception:
        return error.response.text
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    return error.response.text


def lookup_user(session: requests.Session, base_url: str, email: str) -> dict | None:
    response = session.post(
        f"{base_url.rstrip('/')}/users/lookup",
        json={"email": email},
        timeout=15,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def create_user(session: requests.Session, base_url: str, username: str, email: str) -> dict:
    response = session.post(
        f"{base_url.rstrip('/')}/users/",
        json={"username": username, "email": email},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def create_or_lookup_user(
    session: requests.Session,
    base_url: str,
    *,
    username: str,
    email: str,
) -> dict:
    try:
        return create_user(session, base_url, username, email)
    except requests.HTTPError as error:
        detail = api_error_detail(error)
        if error.response.status_code == 400 and "Email already registered" in detail:
            existing = lookup_user(session, base_url, email)
            if existing:
                return existing
        raise


def create_group(session: requests.Session, base_url: str, group_name: str) -> dict:
    response = session.post(
        f"{base_url.rstrip('/')}/groups/",
        json={"name": group_name},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def create_or_lookup_group(session: requests.Session, base_url: str, group_name: str) -> dict:
    try:
        return create_group(session, base_url, group_name)
    except requests.HTTPError as error:
        detail = api_error_detail(error)
        if error.response.status_code == 400 and "Group with this name already exists" in detail:
            groups_response = session.get(f"{base_url.rstrip('/')}/groups/", timeout=15)
            groups_response.raise_for_status()
            for group in groups_response.json():
                if group.get("name") == group_name:
                    return group
        raise


def add_user_to_group(
    session: requests.Session,
    base_url: str,
    *,
    group_id: int,
    user_id: int,
    max_group_size: int,
) -> None:
    response = session.post(
        f"{base_url.rstrip('/')}/groups/{group_id}/users/{user_id}",
        params={"max_group_size": max_group_size},
        timeout=15,
    )
    response.raise_for_status()


def format_group_name(member_names: list[str]) -> str:
    if len(member_names) == 2:
        return f"{member_names[0]} & {member_names[1]}"
    if len(member_names) > 2:
        return f"{', '.join(member_names[:-1])} & {member_names[-1]}"
    return member_names[0]


def main() -> int:
    args = parse_args()
    solos, teams = parse_roster_file(args.roster)

    participant_session = login(args.api_url, args.participant_access_code)
    coordinator_session = login(args.api_url, args.coordinator_access_code)

    allocator = UserAllocator()
    created_users: list[AllocatedUser] = []
    team_rows: list[tuple[str, list[AllocatedUser]]] = []

    if not args.skip_coordinator_user:
        coordinator_user = create_or_lookup_user(
            coordinator_session,
            args.api_url,
            username=args.coordinator_name,
            email=args.coordinator_email,
        )
        print(
            f"Coordinator user ready: {coordinator_user['username']} <{coordinator_user['email']}>"
        )

    print(f"Creating {len(solos)} solo participants...")
    for raw_name in solos:
        allocated = allocator.allocate(raw_name)
        create_or_lookup_user(
            participant_session,
            args.api_url,
            username=allocated.display_name,
            email=allocated.email,
        )
        created_users.append(allocated)
        print(f"  user: {allocated.display_name} <{allocated.email}>")

    print(f"Creating {len(teams)} teams...")
    for raw_members in teams:
        allocated_members = [allocator.allocate(name) for name in raw_members]
        user_records = []
        for allocated in allocated_members:
            user = create_or_lookup_user(
                participant_session,
                args.api_url,
                username=allocated.display_name,
                email=allocated.email,
            )
            user_records.append(user)
            created_users.append(allocated)

        group_name = format_group_name([member.raw_name for member in allocated_members])
        group = create_or_lookup_group(coordinator_session, args.api_url, group_name)
        max_group_size = max(4, len(allocated_members))
        for user in user_records:
            add_user_to_group(
                coordinator_session,
                args.api_url,
                group_id=group["id"],
                user_id=user["id"],
                max_group_size=max_group_size,
            )

        team_rows.append((group_name, allocated_members))
        member_summary = ", ".join(member.display_name for member in allocated_members)
        print(f"  group: {group_name} -> {member_summary}")

    print()
    print("Demo roster seeded successfully.")
    print(f"  solo participants: {len(solos)}")
    print(f"  team groups: {len(team_rows)}")
    print(f"  participant accounts: {len(created_users)}")
    if not args.skip_coordinator_user:
        print(
            f"  coordinator login email: {args.coordinator_email} (access code: {args.coordinator_access_code})"
        )
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
