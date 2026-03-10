"""Provision auths identities for all members of a GitHub org."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

import requests


def get_org_members(org_name: str, token: str) -> list[dict]:
    """Fetch all members of a GitHub organization."""
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "auths-fleet"}
    members: list[dict] = []
    page = 1

    while True:
        resp = requests.get(
            f"https://api.github.com/orgs/{org_name}/members",
            headers=headers,
            params={"per_page": 100, "page": page},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        members.extend(batch)
        page += 1

    return members


def provision_member(username: str) -> bool:
    """Add a GitHub user's SSH keys to allowed_signers via auths CLI."""
    result = subprocess.run(
        ["auths", "signers", "add-from-github", username],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision signing identities from GitHub org")
    parser.add_argument("--org", required=True, help="GitHub organization name")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub token (or set GITHUB_TOKEN)")
    parser.add_argument("--dry-run", action="store_true", help="List members without provisioning")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub token required. Set GITHUB_TOKEN or use --token.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching members of {args.org}...")
    members = get_org_members(args.org, args.token)
    print(f"Found {len(members)} members.")

    if args.dry_run:
        for m in members:
            print(f"  {m['login']}")
        return

    added = 0
    for member in members:
        username = member["login"]
        print(f"  Provisioning {username}...", end=" ")
        if provision_member(username):
            print("OK")
            added += 1
        else:
            print("FAILED (no Ed25519 keys?)")

    print(f"\nProvisioned {added}/{len(members)} members.")


if __name__ == "__main__":
    main()
