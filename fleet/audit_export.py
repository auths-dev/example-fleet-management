"""Export commit signing audit trail to CSV or JSON."""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
from pathlib import Path


def get_commit_audit_trail(repo_path: str, count: int = 100) -> list[dict]:
    """Extract signing audit data from git log."""
    result = subprocess.run(
        [
            "git", "-C", repo_path, "log",
            f"-{count}",
            "--format=%H|%aI|%ae|%G?|%GS|%GK|%s",
        ],
        capture_output=True,
        text=True,
    )

    entries: list[dict] = []
    if result.returncode != 0:
        return entries

    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("|", 6)
        if len(parts) < 7:
            continue

        sig_status = parts[3]
        entries.append({
            "commit": parts[0],
            "date": parts[1],
            "author_email": parts[2],
            "signature_status": sig_status,
            "signer": parts[4] or None,
            "key_id": parts[5] or None,
            "subject": parts[6],
            "is_signed": sig_status in ("G", "U", "X", "Y", "R", "E", "B"),
            "is_verified": sig_status == "G",
        })

    return entries


def export_csv(entries: list[dict], output: Path | None) -> None:
    """Export audit trail as CSV."""
    fieldnames = ["commit", "date", "author_email", "signature_status", "signer", "key_id", "subject", "is_signed", "is_verified"]
    buf = io.StringIO() if output is None else None
    f = buf or output.open("w", newline="")

    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(entries)

    if buf:
        print(buf.getvalue())
    else:
        f.close()


def export_json(entries: list[dict], output: Path | None) -> None:
    """Export audit trail as JSON."""
    data = json.dumps(entries, indent=2)
    if output:
        output.write_text(data + "\n")
    else:
        print(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export commit signing audit trail")
    parser.add_argument("--repo", default=".", help="Path to git repository")
    parser.add_argument("--count", type=int, default=100, help="Number of commits to export (default: 100)")
    parser.add_argument("--format", choices=["csv", "json"], default="json", help="Output format")
    parser.add_argument("--output", default=None, help="Output file (default: stdout)")
    args = parser.parse_args()

    entries = get_commit_audit_trail(args.repo, args.count)

    if not entries:
        print("No commits found.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else None

    if args.format == "csv":
        export_csv(entries, output_path)
    else:
        export_json(entries, output_path)

    if output_path:
        print(f"Exported {len(entries)} commits to {output_path}")


if __name__ == "__main__":
    main()
