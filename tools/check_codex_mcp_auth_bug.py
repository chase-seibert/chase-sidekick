#!/usr/bin/env python3
"""Watch Codex MCP auth bug reports and notify when they look fixed.

The checker is intentionally small and non-interactive so it can run from cron.
It polls the public GitHub API, records state under memory/, and sends one
email notification per newly fixed-looking issue state.
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
DEFAULT_STATE_PATH = REPO_ROOT / "memory" / "codex-mcp-auth-bug-watch.json"
DEFAULT_RECIPIENT = "cseibert@dropbox.com"

WATCHED_ISSUES = [
    {
        "owner": "openai",
        "repo": "codex",
        "number": 17265,
        "role": "primary",
        "note": "Codex stores MCP refresh_token but does not auto-refresh expired access tokens.",
    },
    {
        "owner": "openai",
        "repo": "codex",
        "number": 23866,
        "role": "related",
        "note": "Codex Desktop MCP auth does not stay authenticated for Linear/Notion.",
    },
    {
        "owner": "openai",
        "repo": "codex",
        "number": 27165,
        "role": "related",
        "note": "Codex Desktop sends expired MCP bearer token and does not call /oauth/token.",
    },
]

FIXED_LABEL_MARKERS = (
    "fixed",
    "resolved",
    "complete",
    "completed",
    "released",
    "done",
)
NEGATIVE_FIXED_MARKERS = ("not fixed", "unfixed")


class WatchError(Exception):
    """Raised for expected automation failures."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise WatchError(f"Could not parse {relative_path(path)}: {e}") from e


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fetch_issue(issue_ref: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    owner = issue_ref["owner"]
    repo = issue_ref["repo"]
    number = issue_ref["number"]
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "chase-sidekick-codex-mcp-auth-watch",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise WatchError(f"GitHub API returned {e.code} for {url}: {body[:500]}") from e
    except urllib.error.URLError as e:
        raise WatchError(f"Could not reach GitHub API for {url}: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise WatchError(f"GitHub API returned invalid JSON for {url}: {e}") from e


def label_suggests_fixed(label_name: str) -> bool:
    normalized = label_name.strip().lower().replace("_", " ").replace("-", " ")
    if any(marker in normalized for marker in NEGATIVE_FIXED_MARKERS):
        return False
    return any(marker in normalized for marker in FIXED_LABEL_MARKERS)


def classify_issue(issue_ref: Dict[str, Any], issue: Dict[str, Any]) -> Dict[str, Any]:
    labels = sorted(
        label.get("name", "")
        for label in issue.get("labels", [])
        if isinstance(label, dict) and label.get("name")
    )
    fixed_labels = [label for label in labels if label_suggests_fixed(label)]
    state = issue.get("state") or "unknown"
    state_reason = issue.get("state_reason") or ""

    fixed_reasons: List[str] = []
    if fixed_labels:
        fixed_reasons.append("fixed-looking label: " + ", ".join(fixed_labels))
    if state == "closed" and state_reason == "completed":
        fixed_reasons.append("closed with state_reason=completed")
    elif state == "closed" and state_reason != "not_planned":
        fixed_reasons.append("closed without a not_planned state reason")

    fixed = bool(fixed_reasons)
    fingerprint_parts = {
        "number": issue_ref["number"],
        "state": state,
        "state_reason": state_reason,
        "closed_at": issue.get("closed_at"),
        "labels": labels,
    }

    return {
        "owner": issue_ref["owner"],
        "repo": issue_ref["repo"],
        "number": issue_ref["number"],
        "role": issue_ref["role"],
        "watch_note": issue_ref["note"],
        "title": issue.get("title") or "(untitled)",
        "url": issue.get("html_url")
        or f"https://github.com/{issue_ref['owner']}/{issue_ref['repo']}/issues/{issue_ref['number']}",
        "state": state,
        "state_reason": state_reason,
        "labels": labels,
        "updated_at": issue.get("updated_at"),
        "closed_at": issue.get("closed_at"),
        "fixed": fixed,
        "fixed_reasons": fixed_reasons,
        "fingerprint": json.dumps(fingerprint_parts, sort_keys=True),
    }


def summarize_status(status: Dict[str, Any]) -> str:
    state = status["state"]
    reason = status.get("state_reason")
    suffix = f" ({reason})" if reason else ""
    fixed = "fixed-looking" if status["fixed"] else "not fixed yet"
    return f"#{status['number']} {state}{suffix}, {fixed}: {status['title']}"


def build_email_body(statuses: List[Dict[str, Any]], state_path: Path) -> str:
    fixed_statuses = [status for status in statuses if status["fixed"]]
    lines = [
        "One or more watched Codex MCP authentication bug reports now look fixed.",
        "",
        "Fixed-looking issue(s):",
    ]

    for status in fixed_statuses:
        lines.extend(
            [
                f"- openai/codex#{status['number']}: {status['title']}",
                f"  Status: {status['state']}"
                + (f" ({status['state_reason']})" if status["state_reason"] else ""),
                f"  Closed at: {status['closed_at'] or '(not closed)'}",
                f"  Matched because: {'; '.join(status['fixed_reasons'])}",
                f"  URL: {status['url']}",
                f"  Watch note: {status['watch_note']}",
                "",
            ]
        )

    lines.extend(
        [
            "Full watch status:",
            *(f"- {summarize_status(status)}" for status in statuses),
            "",
            f"State file: {relative_path(state_path)}",
            "This automation will not email again for the same fixed issue state.",
        ]
    )
    return "\n".join(lines)


def send_email(recipient: str, subject: str, body: str) -> None:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from sidekick.clients.gmail import GmailClient
        from sidekick.config import get_google_config, get_user_config

        google_config = get_google_config()
        try:
            user_config = get_user_config()
            recipient = user_config.get("email") or recipient
        except ValueError:
            pass

        client = GmailClient(
            client_id=google_config["client_id"],
            client_secret=google_config["client_secret"],
            refresh_token=google_config["refresh_token"],
        )
        client.send_message(to=recipient, subject=subject, body=body)
    except Exception as e:
        raise WatchError(f"Could not send Gmail notification: {e}") from e


def send_desktop_notification(title: str, message: str) -> None:
    script = (
        "display notification "
        + json.dumps(message)
        + " with title "
        + json.dumps(title)
    )
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except Exception as e:
        raise WatchError(f"Could not send desktop notification: {e}") from e


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Codex MCP OAuth bug reports and notify when fixed."
    )
    parser.add_argument(
        "--state",
        default=str(DEFAULT_STATE_PATH),
        help=f"State JSON path (default: {relative_path(DEFAULT_STATE_PATH)}).",
    )
    parser.add_argument(
        "--recipient",
        default=DEFAULT_RECIPIENT,
        help="Fallback email recipient if USER_EMAIL is not configured.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Per-request GitHub API timeout in seconds.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print current status without saving state or sending notifications.",
    )
    parser.add_argument(
        "--force-notify",
        action="store_true",
        help="Send a notification even if the fixed state was already reported.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state_path = Path(args.state).expanduser()

    statuses = []
    for issue_ref in WATCHED_ISSUES:
        issue = fetch_issue(issue_ref, timeout=args.timeout)
        statuses.append(classify_issue(issue_ref, issue))

    checked_at = utc_now()
    print(f"[{checked_at}] Codex MCP auth bug watch")
    for status in statuses:
        print("  " + summarize_status(status))

    if args.dry_run:
        if any(status["fixed"] for status in statuses):
            print()
            print("Dry run: fixed-looking status would notify with this email body:")
            print(build_email_body(statuses, state_path))
        return 0

    state = load_json(state_path)
    notified_fixed = state.get("notified_fixed") or {}
    if not isinstance(notified_fixed, dict):
        notified_fixed = {}

    pending = []
    for status in statuses:
        if not status["fixed"]:
            continue
        key = str(status["number"])
        if args.force_notify or notified_fixed.get(key) != status["fingerprint"]:
            pending.append(status)

    if pending:
        subject = "[Sidekick] Codex MCP auth bug looks fixed"
        body = build_email_body(statuses, state_path)
        try:
            send_email(args.recipient, subject, body)
            print(f"  Sent Gmail notification to {args.recipient}")
        except WatchError as email_error:
            print(f"  Email notification failed: {email_error}", file=sys.stderr)
            try:
                send_desktop_notification(
                    "Codex MCP auth bug looks fixed",
                    ", ".join(f"openai/codex#{status['number']}" for status in pending),
                )
                print("  Sent desktop notification fallback")
            except WatchError as desktop_error:
                print(f"  Desktop notification failed: {desktop_error}", file=sys.stderr)
                return 1

        for status in pending:
            notified_fixed[str(status["number"])] = status["fingerprint"]
    else:
        print("  No new fixed-looking status to notify.")

    state.update(
        {
            "last_checked_at": checked_at,
            "notified_fixed": notified_fixed,
            "statuses": statuses,
        }
    )
    save_json(state_path, state)
    print(f"  Updated state: {relative_path(state_path)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except WatchError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
