#!/usr/bin/env python3
import json
import os
import random
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
load_dotenv(SCRIPT_DIR / ".env")


def sattolo(names: list[str]) -> list[str]:
    """Return a derangement of names (no element maps to itself, single cycle)."""
    lst = list(names)
    for i in range(len(lst) - 1, 0, -1):
        j = random.randint(0, i - 1)
        lst[i], lst[j] = lst[j], lst[i]
    return lst


def build_message(upper: str, lower: str, attendee: str, recipient: str, number: int) -> str:
    upper_text = upper.format(attendee=attendee, number=number)
    lower_text = lower.format(attendee=attendee, number=number)
    return f"{upper_text}\n\n**{recipient}**\n\n{lower_text}"


def push_to_pwpush(payload: str, email: str, token: str) -> str:
    resp = requests.post(
        "https://eu.pwpush.com/p.json",
        headers={
            "X-User-Email": email,
            "X-User-Token": token,
            "Content-Type": "application/json",
        },
        json={
            "password": {
                "payload": payload,
                "expire_after_days": 7,
                "deletable_by_viewer": False,
            }
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"ERROR: pwpush returned {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)
    url_token = resp.json()["url_token"]
    return f"https://eu.pwpush.com/p/{url_token}"


def print_table(challenge: str, rows: list[tuple[int, str, str]]) -> None:
    name_w = max(len(r[1]) for r in rows)
    name_w = max(name_w, len("Attendee"))
    link_w = max(len(r[2]) for r in rows)
    link_w = max(link_w, len("Link"))

    header = f"Secret Santa Draw — {challenge}"
    print(f"\n{header}")
    print("=" * len(header))
    print(f" {'#':>3}  {'Attendee':<{name_w}}  {'Link':<{link_w}}")
    print(f" {'—'*3}  {'—'*name_w}  {'—'*link_w}")
    for num, name, link in rows:
        print(f" {num:>3}  {name:<{name_w}}  {link}")
    print()


def save_results(challenge: str, rows: list[tuple[int, str, str]], assignments: dict[str, str]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    assignments_file = RESULTS_DIR / f"assignments_{challenge}.json"
    assignments_file.write_text(
        json.dumps({"challenge": challenge, "assignments": assignments}, indent=2, ensure_ascii=False) + "\n"
    )

    md_file = RESULTS_DIR / f"results_{challenge}.md"
    lines = [
        f"# Secret Santa Draw — {challenge}\n",
        "| # | Attendee | Link |",
        "|---|----------|------|",
    ]
    for num, name, link in rows:
        lines.append(f"| {num} | {name} | [Open]({link}) |")
    md_file.write_text("\n".join(lines) + "\n")

    return md_file


def load_assignments(challenge: str) -> dict[str, str]:
    assignments_file = RESULTS_DIR / f"assignments_{challenge}.json"
    if not assignments_file.exists():
        print(f"ERROR: No assignments file found at {assignments_file}", file=sys.stderr)
        print("Run the draw first to generate assignments.", file=sys.stderr)
        sys.exit(1)
    return json.loads(assignments_file.read_text())["assignments"]


def update_results_link(challenge: str, attendee: str, new_link: str) -> None:
    md_file = RESULTS_DIR / f"results_{challenge}.md"
    if not md_file.exists():
        return
    lines = md_file.read_text().splitlines()
    updated = []
    for line in lines:
        cols = [c.strip() for c in line.split("|")]
        if len(cols) >= 4 and cols[2] == attendee:
            line = f"| {cols[1]} | {attendee} | [Open]({new_link}) |"
        updated.append(line)
    md_file.write_text("\n".join(updated) + "\n")


def do_repush(name: str, challenge: str, participants: list[str], email: str, token: str) -> None:
    assignments = load_assignments(challenge)

    match = next((a for a in assignments if a.lower() == name.lower()), None)
    if not match:
        print(f"ERROR: '{name}' not found in assignments for {challenge}.", file=sys.stderr)
        print(f"Known attendees: {', '.join(assignments)}", file=sys.stderr)
        sys.exit(1)

    recipient = assignments[match]
    recipient_numbers = {n: i for i, n in enumerate(participants, start=1)}
    number = recipient_numbers[recipient]

    template = json.loads((SCRIPT_DIR / "template.json").read_text())
    message = build_message(template["upper"], template["lower"], match, recipient, number)

    print(f"Re-pushing link for {match} → {recipient}…")
    link = push_to_pwpush(message, email, token)
    print(f"\nNew link for {match}: {link}\n")
    update_results_link(challenge, match, link)
    print("Results file updated.")


def get_credentials() -> tuple[str, str]:
    email = os.environ.get("PWPUSH_EMAIL", "")
    token = os.environ.get("PWPUSH_TOKEN", "")
    if not email or not token:
        print("ERROR: PWPUSH_EMAIL and PWPUSH_TOKEN must be set in secret_santa/.env", file=sys.stderr)
        sys.exit(1)
    return email, token


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    repush_idx = next((i for i, a in enumerate(sys.argv) if a == "--repush"), None)
    repush_name = sys.argv[repush_idx + 1] if repush_idx is not None and repush_idx + 1 < len(sys.argv) else None

    if repush_idx is not None and not repush_name:
        print("ERROR: --repush requires a name argument, e.g. --repush Alice", file=sys.stderr)
        sys.exit(1)

    config = json.loads((SCRIPT_DIR / "config.json").read_text())
    challenge: str = config["challenge"]
    participants: list[str] = config["participants"]

    if len(participants) < 2:
        print("ERROR: Need at least 2 participants.", file=sys.stderr)
        sys.exit(1)

    if repush_name:
        email, token = get_credentials()
        do_repush(repush_name, challenge, participants, email, token)
        return

    assignments = sattolo(participants)

    if dry_run:
        print(f"\nDry run — draw for {challenge} ({len(participants)} participants)\n")
        for attendee, recipient in zip(participants, assignments):
            print(f"  {attendee} → {recipient}")
        print()
        return

    email, token = get_credentials()
    template = json.loads((SCRIPT_DIR / "template.json").read_text())
    rows: list[tuple[int, str, str]] = []

    print(f"Running draw for {len(participants)} participants…")
    recipient_numbers = {name: i for i, name in enumerate(participants, start=1)}
    assignments_dict = dict(zip(participants, assignments))

    for i, (attendee, recipient) in enumerate(zip(participants, assignments), start=1):
        print(f"  [{i}/{len(participants)}] Pushing link for {attendee}…")
        number = recipient_numbers[recipient]
        message = build_message(template["upper"], template["lower"], attendee, recipient, number)
        link = push_to_pwpush(message, email, token)
        rows.append((i, attendee, link))

    print_table(challenge, rows)
    out_file = save_results(challenge, rows, assignments_dict)
    print(f"Results saved to {out_file}")


if __name__ == "__main__":
    main()
