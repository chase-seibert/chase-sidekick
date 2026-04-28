#!/usr/bin/env python3
"""Check Codex CLI authentication status.

This tool checks whether Codex CLI is authenticated and logs the status to
stdout. When Codex is authenticated with ChatGPT tokens, it also reports when
the current access token will expire.

Usage:
    python3 tools/check_codex_auth.py

Or:
    ./tools/check_codex_auth.py

Output format (single line):
    [2026-04-22 10:30:00] ✅ Codex authenticated | Expires: 2026-05-04 16:23 UTC (9 days)

The tool is designed to run non-interactively and will not trigger login
prompts or browser flows. It only checks the current authentication state.

Intended for use with cron to monitor authentication status over time:
    */15 * * * * /usr/local/bin/python3 /Users/cseibert/projects/chase-sidekick/tools/check_codex_auth.py >> /tmp/codex_auth.log 2>&1
"""
import base64
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"


def get_timestamp() -> str:
    """Get current timestamp in log format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_codex_login_status() -> dict:
    """Check Codex authentication status with the CLI.

    Returns dict with:
        - authenticated: bool
        - auth_method: str (if authenticated and reported by Codex)
        - error: str (if check failed)
    """
    try:
        result = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return {"authenticated": False, "error": "codex login status timed out"}
    except FileNotFoundError:
        return {"authenticated": False, "error": "codex CLI not found"}
    except Exception as e:
        return {"authenticated": False, "error": f"Unexpected error: {e}"}

    status_lines = [
        line.strip()
        for stream in (result.stdout, result.stderr)
        for line in stream.splitlines()
        if line.strip()
    ]
    status_text = " | ".join(status_lines)

    auth_method = parse_auth_method(status_lines)
    is_authenticated = auth_method is not None or any(
        line.lower() == "logged in" for line in status_lines
    )

    if result.returncode != 0 and not is_authenticated:
        return {
            "authenticated": False,
            "error": f"codex login status failed: {status_text or 'no output'}",
        }

    if not is_authenticated:
        return {
            "authenticated": False,
            "error": status_text or "codex login status did not report a login",
        }

    return {
        "authenticated": True,
        "auth_method": auth_method,
    }


def parse_auth_method(status_lines):
    """Extract a compact auth method from Codex status output."""
    prefix = "Logged in using "
    for line in status_lines:
        if line.startswith(prefix):
            return line[len(prefix):].strip().rstrip(".")
    return None


def read_codex_auth() -> dict:
    """Read Codex auth metadata without exposing token values."""
    try:
        with CODEX_AUTH_PATH.open("r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"error": f"{CODEX_AUTH_PATH} not found"}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse {CODEX_AUTH_PATH}: {e}"}
    except Exception as e:
        return {"error": f"Failed to read {CODEX_AUTH_PATH}: {e}"}

    return {"auth": data}


def decode_jwt_payload(token: str) -> dict:
    """Decode a JWT payload without validating the signature."""
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("token is not a JWT")

    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))


def get_token_expiration(auth_data: dict) -> dict:
    """Get the most useful Codex token expiration from auth metadata.

    Returns dict with:
        - expires_at: datetime object (if found)
        - token_name: str (which token supplied the expiration)
        - error: str (if no expiration could be determined)
    """
    tokens = auth_data.get("tokens")
    if isinstance(tokens, dict):
        for token_name in ("access_token", "id_token"):
            token = tokens.get(token_name)
            if not token:
                continue

            try:
                payload = decode_jwt_payload(token)
                expires_at = payload.get("exp")
                if expires_at is not None:
                    return {
                        "expires_at": datetime.fromtimestamp(
                            int(expires_at), timezone.utc
                        ),
                        "token_name": token_name,
                    }
            except (ValueError, TypeError, json.JSONDecodeError, OSError):
                continue

    if os.environ.get("OPENAI_API_KEY") or auth_data.get("OPENAI_API_KEY"):
        return {"error": "API key authentication does not expose an expiration"}

    return {"error": "No expiration timestamp found in Codex auth tokens"}


def format_duration(expires_at: datetime) -> str:
    """Format time until expiration as a human-readable duration."""
    now = datetime.now(timezone.utc)
    delta = expires_at - now

    if delta.total_seconds() < 0:
        return "expired"

    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    if days > 0:
        return f"{days} day{'s' if days != 1 else ''}"
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    return "< 1 minute"


def main() -> int:
    """Main entry point."""
    timestamp = get_timestamp()
    status = run_codex_login_status()

    if not status["authenticated"]:
        error_msg = status.get("error", "Unknown error")
        print(f"[{timestamp}] 🛑 Codex NOT authenticated | Error: {error_msg}")
        return 1

    auth_file = read_codex_auth()
    if "error" in auth_file:
        print(
            f"[{timestamp}] ✅ Codex authenticated | "
            f"Expiration: unknown ({auth_file['error']})"
        )
        return 0

    expiration = get_token_expiration(auth_file["auth"])
    if "error" in expiration:
        print(
            f"[{timestamp}] ✅ Codex authenticated | "
            f"Expiration: unknown ({expiration['error']})"
        )
        return 0

    expires_at = expiration["expires_at"]
    expires_str = expires_at.strftime("%Y-%m-%d %H:%M UTC")
    duration = format_duration(expires_at)

    print(f"[{timestamp}] ✅ Codex authenticated | Expires: {expires_str} ({duration})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
