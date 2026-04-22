#!/usr/bin/env python3
"""Check Claude Code CLI authentication status.

This tool checks whether Claude Code CLI is authenticated and logs the status
to stdout. It also reports when the authentication token will expire.

Usage:
    python3 tools/check_claude_auth.py

Or:
    ./tools/check_claude_auth.py

Output format (single line):
    [2026-04-22 10:30:00] ✅ Claude authenticated | Expires: 2026-04-22 18:12 UTC (53 minutes)

The tool is designed to run non-interactively and will not trigger any login
prompts or browser flows. It only checks the current authentication state.

Intended for use with cron to monitor authentication status over time:
    */15 * * * * /usr/local/bin/python3 /Users/cseibert/projects/chase-sidekick/tools/check_claude_auth.py >> /tmp/claude_auth.log 2>&1
"""
import sys
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def get_timestamp() -> str:
    """Get current timestamp in log format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def check_claude_status() -> dict:
    """Check Claude Code authentication status.

    Returns dict with:
        - authenticated: bool
        - error: str (if check failed)
    """
    try:
        result = subprocess.run(
            ["claude", "auth", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return {
                "authenticated": False,
                "error": f"claude auth status failed: {result.stderr.strip()}"
            }

        status = json.loads(result.stdout)
        return {
            "authenticated": status.get("loggedIn", False),
            "api_provider": status.get("apiProvider"),
            "auth_method": status.get("authMethod")
        }
    except subprocess.TimeoutExpired:
        return {"authenticated": False, "error": "claude auth status timed out"}
    except json.JSONDecodeError as e:
        return {"authenticated": False, "error": f"Failed to parse auth status: {e}"}
    except FileNotFoundError:
        return {"authenticated": False, "error": "claude CLI not found"}
    except Exception as e:
        return {"authenticated": False, "error": f"Unexpected error: {e}"}


def get_aws_sso_expiration() -> dict:
    """Get AWS SSO token expiration from cache files.

    Returns dict with:
        - expires_at: datetime object (if found)
        - error: str (if failed)
    """
    try:
        # Find AWS SSO cache files
        cache_dir = Path.home() / ".aws" / "sso" / "cache"
        cache_files = list(cache_dir.glob("*.json"))

        if not cache_files:
            return {"error": "No AWS SSO cache files found"}

        # Read all cache files and find the EARLIEST (shortest) expiration
        # This is the access token expiration, not the registration expiration
        earliest_expiry = None
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    if "expiresAt" in data:
                        expires_str = data["expiresAt"]
                        # Parse ISO 8601 format: 2026-07-21T16:14:12Z
                        expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                        # Keep track of the earliest expiration (access token, not registration)
                        if earliest_expiry is None or expires < earliest_expiry:
                            earliest_expiry = expires
            except (json.JSONDecodeError, ValueError, KeyError):
                continue

        if earliest_expiry:
            return {"expires_at": earliest_expiry}
        else:
            return {"error": "No expiration timestamp found in cache"}

    except Exception as e:
        return {"error": f"Failed to read AWS SSO cache: {e}"}


def format_duration(expires_at: datetime) -> str:
    """Format time until expiration as human-readable duration.

    Args:
        expires_at: Expiration timestamp (timezone-aware)

    Returns:
        Human-readable string like "89 days", "3 hours", "expired"
    """
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
    elif hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return "< 1 minute"


def main():
    """Main entry point."""
    timestamp = get_timestamp()

    # Check Claude authentication
    status = check_claude_status()

    if not status["authenticated"]:
        error_msg = status.get("error", "Unknown error")
        print(f"[{timestamp}] 🛑 Claude NOT authenticated | Error: {error_msg}")
        sys.exit(1)

    # Get token expiration (for Bedrock/AWS SSO)
    expiration = get_aws_sso_expiration()

    if "error" in expiration:
        # Authenticated but can't determine expiration
        print(f"[{timestamp}] ✅ Claude authenticated | Expiration: unknown ({expiration['error']})")
        sys.exit(0)

    # Format expiration info
    expires_at = expiration["expires_at"]
    expires_str = expires_at.strftime("%Y-%m-%d %H:%M UTC")
    duration = format_duration(expires_at)

    print(f"[{timestamp}] ✅ Claude authenticated | Expires: {expires_str} ({duration})")
    sys.exit(0)


if __name__ == "__main__":
    main()
