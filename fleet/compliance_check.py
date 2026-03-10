"""Generate compliance report: signing rate, rotation status, policy violations."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_commit_signing_stats(repo_path: str, days: int = 30) -> dict:
    """Check signing rate for recent commits."""
    result = subprocess.run(
        ["git", "-C", repo_path, "log", f"--since={days} days ago", "--format=%H %G?"],
        capture_output=True,
        text=True,
    )

    total = 0
    signed = 0
    verified = 0

    if result.returncode == 0:
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            total += 1
            parts = line.split()
            if len(parts) >= 2:
                status = parts[1]
                if status in ("G", "U", "X", "Y", "R", "E", "B"):
                    signed += 1
                if status == "G":
                    verified += 1

    return {
        "total_commits": total,
        "signed_commits": signed,
        "verified_commits": verified,
        "rate": verified / total if total > 0 else 0,
        "period_days": days,
    }


def count_signers(signers_path: Path) -> int:
    """Count non-comment, non-empty lines in allowed_signers."""
    if not signers_path.exists():
        return 0
    return sum(
        1
        for line in signers_path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def check_policy_violations(signers_path: Path, policy_path: Path) -> list[dict]:
    """Check for policy violations."""
    violations: list[dict] = []

    if not policy_path.exists():
        return violations

    policy = json.loads(policy_path.read_text())

    if policy.get("name") == "ed25519_only" and signers_path.exists():
        for line in signers_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "ssh-ed25519" not in line:
                parts = line.split()
                violations.append({
                    "policy": "ed25519_only",
                    "email": parts[0] if parts else "unknown",
                    "detail": "Key type is not Ed25519",
                })

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate signing compliance report")
    parser.add_argument("--repo", default=".", help="Path to git repository")
    parser.add_argument("--signers", default=".auths/allowed_signers", help="Path to allowed_signers")
    parser.add_argument("--policy", default=None, help="Path to policy JSON file")
    parser.add_argument("--days", type=int, default=30, help="Lookback period in days (default: 30)")
    parser.add_argument("--output", default=None, help="Output file (default: stdout)")
    args = parser.parse_args()

    signers_path = Path(args.signers)

    signing_stats = get_commit_signing_stats(args.repo, args.days)
    violations = check_policy_violations(signers_path, Path(args.policy)) if args.policy else []

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo": args.repo,
        "signing_rate": signing_stats,
        "total_signers": count_signers(signers_path),
        "policy_violations": violations,
    }

    output = json.dumps(report, indent=2)

    if args.output:
        Path(args.output).write_text(output + "\n")
        print(f"Report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
