"""Revoke signing keys when developers leave the organization."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


def remove_signer(signers_path: Path, email: str) -> bool:
    """Remove a signer entry from allowed_signers by email."""
    if not signers_path.exists():
        print(f"Error: {signers_path} not found.", file=sys.stderr)
        return False

    lines = signers_path.read_text().splitlines()
    original_count = len(lines)
    filtered = [line for line in lines if not line.startswith(email)]

    if len(filtered) == original_count:
        print(f"Warning: no entry found for {email}")
        return False

    signers_path.write_text("\n".join(filtered) + "\n")
    return True


def log_revocation(email: str, log_path: Path) -> None:
    """Append a revocation entry to the audit log."""
    timestamp = datetime.now(timezone.utc).isoformat()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(f"{timestamp}\tREVOKED\t{email}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Revoke signing keys for departing developers")
    parser.add_argument("--email", required=True, help="Email of the developer to deprovision")
    parser.add_argument("--signers", default=".auths/allowed_signers", help="Path to allowed_signers file")
    parser.add_argument("--log", default="fleet/revocations.log", help="Path to revocation log")
    args = parser.parse_args()

    signers_path = Path(args.signers)
    log_path = Path(args.log)

    print(f"Revoking signing key for {args.email}...")
    if remove_signer(signers_path, args.email):
        log_revocation(args.email, log_path)
        print(f"Revoked. Entry removed from {signers_path}.")
        print(f"Revocation logged to {log_path}.")
        print("\nNext steps:")
        print(f"  git add {signers_path} {log_path}")
        print(f'  git commit -m "chore: revoke signing key for {args.email}"')
        print("  git push")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
