"""Enforce key rotation policy by flagging keys older than a threshold."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_key_ages(signers_path: Path) -> list[dict]:
    """Parse allowed_signers and estimate key ages using git log."""
    if not signers_path.exists():
        return []

    entries: list[dict] = []
    for line in signers_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        email = parts[0]

        # Try to find when this entry was last added/modified via git log
        result = subprocess.run(
            ["git", "log", "--format=%aI", "--diff-filter=A", "-1", "--", str(signers_path)],
            capture_output=True,
            text=True,
        )
        added_date = result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None

        entries.append({
            "email": email,
            "key_type": parts[1] if len(parts) > 1 else "unknown",
            "added_date": added_date,
        })

    return entries


def check_rotation(entries: list[dict], max_age_days: int) -> dict:
    """Check which keys are overdue for rotation."""
    now = datetime.now(timezone.utc)
    compliant: list[dict] = []
    overdue: list[dict] = []

    for entry in entries:
        if entry["added_date"]:
            added = datetime.fromisoformat(entry["added_date"])
            age_days = (now - added).days
            entry["age_days"] = age_days
            if age_days > max_age_days:
                overdue.append(entry)
            else:
                compliant.append(entry)
        else:
            entry["age_days"] = None
            overdue.append(entry)  # Unknown age treated as overdue

    return {
        "total_keys": len(entries),
        "compliant": len(compliant),
        "overdue": len(overdue),
        "max_age_days": max_age_days,
        "overdue_keys": overdue,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Enforce key rotation policy")
    parser.add_argument("--signers", default=".auths/allowed_signers", help="Path to allowed_signers")
    parser.add_argument("--max-age", type=int, default=90, help="Maximum key age in days (default: 90)")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output as JSON")
    args = parser.parse_args()

    entries = get_key_ages(Path(args.signers))
    report = check_rotation(entries, args.max_age)

    if args.output_json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"Key Rotation Report (max age: {args.max_age} days)")
        print(f"  Total keys: {report['total_keys']}")
        print(f"  Compliant:  {report['compliant']}")
        print(f"  Overdue:    {report['overdue']}")
        if report["overdue_keys"]:
            print("\nOverdue keys:")
            for key in report["overdue_keys"]:
                age = f"{key['age_days']} days" if key["age_days"] is not None else "unknown age"
                print(f"  - {key['email']} ({age})")

    if report["overdue"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
