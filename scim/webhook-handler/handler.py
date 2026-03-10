"""SCIM webhook handler: receives IdP events and provisions/deprovisions auths identities."""
from __future__ import annotations

import os
import subprocess
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

SIGNERS_PATH = Path(os.environ.get("AUTHS_SIGNERS_PATH", ".auths/allowed_signers"))
BEARER_TOKEN = os.environ.get("SCIM_BEARER_TOKEN", "")


def require_auth(f):
    """Require bearer token authentication for SCIM endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if BEARER_TOKEN:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {BEARER_TOKEN}":
                return jsonify({"detail": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "signers_path": str(SIGNERS_PATH)})


@app.route("/scim/v2/Users", methods=["POST"])
@require_auth
def create_user():
    """SCIM: Provision a new user's signing keys."""
    data = request.json
    if not data:
        return jsonify({"detail": "Request body required"}), 400

    username = data.get("userName", "")
    if not username:
        return jsonify({"detail": "userName required"}), 400

    # Extract GitHub username from email or userName
    github_username = username.split("@")[0]

    result = subprocess.run(
        ["auths", "signers", "add-from-github", github_username],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return jsonify({
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": github_username,
            "userName": username,
            "active": True,
            "meta": {"resourceType": "User"},
        }), 201
    else:
        return jsonify({"detail": f"Failed to provision: {result.stderr}"}), 500


@app.route("/scim/v2/Users/<user_id>", methods=["DELETE"])
@require_auth
def delete_user(user_id: str):
    """SCIM: Deprovision a user by removing their signing keys."""
    if not SIGNERS_PATH.exists():
        return "", 204

    lines = SIGNERS_PATH.read_text().splitlines()
    email_prefix = f"{user_id}@"
    filtered = [line for line in lines if not line.startswith(email_prefix)]

    if len(filtered) < len(lines):
        SIGNERS_PATH.write_text("\n".join(filtered) + "\n")

    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
