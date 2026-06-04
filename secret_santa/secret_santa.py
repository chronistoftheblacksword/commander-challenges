#!/usr/bin/env python3
import json
import os
import random
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
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
                "expire_after_views": 3,
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


def write_markdown(challenge: str, rows: list[tuple[int, str, str]], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"results_{challenge}.md"
    lines = [
        f"# Secret Santa Draw — {challenge}\n",
        "| # | Attendee | Link |",
        "|---|----------|------|",
    ]
    for num, name, link in rows:
        lines.append(f"| {num} | {name} | [Open]({link}) |")
    out_file.write_text("\n".join(lines) + "\n")
    return out_file


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    config = json.loads((SCRIPT_DIR / "config.json").read_text())
    challenge: str = config["challenge"]
    participants: list[str] = config["participants"]

    if len(participants) < 2:
        print("ERROR: Need at least 2 participants.", file=sys.stderr)
        sys.exit(1)

    assignments = sattolo(participants)

    if dry_run:
        print(f"\nDry run — draw for {challenge} ({len(participants)} participants)\n")
        for attendee, recipient in zip(participants, assignments):
            print(f"  {attendee} → {recipient}")
        print()
        return

    email = os.environ.get("PWPUSH_EMAIL", "")
    token = os.environ.get("PWPUSH_TOKEN", "")
    if not email or not token:
        print("ERROR: PWPUSH_EMAIL and PWPUSH_TOKEN must be set in secret_santa/.env", file=sys.stderr)
        sys.exit(1)

    template = json.loads((SCRIPT_DIR / "template.json").read_text())
    rows: list[tuple[int, str, str]] = []

    print(f"Running draw for {len(participants)} participants…")
    recipient_numbers = {name: i for i, name in enumerate(participants, start=1)}

    for i, (attendee, recipient) in enumerate(zip(participants, assignments), start=1):
        print(f"  [{i}/{len(participants)}] Pushing link for {attendee}…")
        number = recipient_numbers[recipient]
        message = build_message(template["upper"], template["lower"], attendee, recipient, number)
        link = push_to_pwpush(message, email, token)
        rows.append((i, attendee, link))

    print_table(challenge, rows)
    out_file = write_markdown(challenge, rows, SCRIPT_DIR / "results")
    print(f"Results saved to {out_file}")


if __name__ == "__main__":
    main()
