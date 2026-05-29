#!/usr/bin/env python3
"""Create a sourced OmniFocus TODO for the capture-work-todos skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidekick.clients.omnifocus import OmniFocusClient  # noqa: E402


PRIMARY_TAG = "sidekick-auto-todo"
SKILL_TAG = "capture-work-todos"
SOURCE_TAGS = {
    "slack-dm": "source-slack",
    "one-on-one": "source-oneonone",
    "leadership-meeting": "source-leadership-meeting",
    "other": "source-work-context",
}


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def compact(value: str | None) -> str:
    return (value or "").strip()


def build_note(args: argparse.Namespace, captured_at: str) -> str:
    lines = [
        "Created by capture-work-todos.",
        "",
        "Metadata:",
        f"- skill: {SKILL_TAG}",
        f"- source_type: {args.source_type}",
        f"- source_person: {compact(args.source_person) or 'unknown'}",
        f"- source_title: {compact(args.source_title) or 'unknown'}",
        f"- source_date: {compact(args.source_date) or 'unknown'}",
        f"- source_url: {args.source_url}",
        f"- captured_at: {captured_at}",
    ]

    if args.evidence:
        lines.extend(["", "Evidence:", args.evidence.strip()])

    return "\n".join(lines)


def merged_tags(args: argparse.Namespace) -> list[str]:
    tags: list[str] = [PRIMARY_TAG, SKILL_TAG, SOURCE_TAGS[args.source_type]]
    tags.extend(args.tag or [])

    seen = set()
    unique = []
    for tag in tags:
        tag = tag.strip()
        if tag and tag not in seen:
            unique.append(tag)
            seen.add(tag)
    return unique


def task_label(task: dict[str, Any]) -> str:
    task_id = task.get("id", "unknown")
    name = task.get("name", "untitled")
    return f"{task_id}: {name}"


def safe_query(client: OmniFocusClient, **kwargs: Any) -> list[dict[str, Any]]:
    try:
        return client.query_tasks(**kwargs)
    except Exception as exc:
        print(f"Warning: OmniFocus query failed for {kwargs}: {exc}", file=sys.stderr)
        return []


def find_existing(
    client: OmniFocusClient,
    title: str,
    source_url: str,
    primary_tag: str,
) -> dict[str, Any] | None:
    wanted_title = normalize_title(title)
    seen_ids: set[str] = set()
    candidates: list[dict[str, Any]] = []

    for status in ("active", "inbox", "completed"):
        candidates.extend(safe_query(client, status=status, limit=500))

    for status in ("all", "completed"):
        candidates.extend(safe_query(client, status=status, tag=primary_tag, limit=500))

    for task in candidates:
        task_id = task.get("id")
        if not task_id or task_id in seen_ids:
            continue
        seen_ids.add(task_id)

        if normalize_title(task.get("name", "")) == wanted_title:
            return {"reason": "matching title", "task": task}

        tags = task.get("tags") or []
        tag_names = [tag.get("name", "") if isinstance(tag, dict) else str(tag) for tag in tags]
        if primary_tag not in tag_names:
            continue

        try:
            full_task = client.get_task(task_id)
        except Exception as exc:
            print(f"Warning: could not inspect task note for {task_label(task)}: {exc}", file=sys.stderr)
            continue

        note = full_task.get("note") or ""
        if source_url and source_url in note:
            return {"reason": "matching source URL", "task": full_task}

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True, help="OmniFocus task title to create.")
    parser.add_argument("--source-url", required=True, help="Permalink or document URL for the source evidence.")
    parser.add_argument(
        "--source-type",
        choices=sorted(SOURCE_TAGS),
        required=True,
        help="Type of source evidence.",
    )
    parser.add_argument("--source-person", help="Person who made the ask or owns the source conversation.")
    parser.add_argument("--source-title", help="Document, meeting, or thread title.")
    parser.add_argument("--source-date", help="Evidence date in YYYY-MM-DD form when available.")
    parser.add_argument("--evidence", help="Short excerpt or summary supporting this TODO.")
    parser.add_argument("--project", help="Optional OmniFocus project name.")
    parser.add_argument("--due", help="Optional due date in YYYY-MM-DD form.")
    parser.add_argument("--defer", dest="defer_date", help="Optional defer date in YYYY-MM-DD form.")
    parser.add_argument("--flagged", action="store_true", help="Create the task as flagged.")
    parser.add_argument("--tag", action="append", help="Additional OmniFocus tag. May be supplied more than once.")
    parser.add_argument("--dry-run", action="store_true", help="Print the task payload without touching OmniFocus.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    tags = merged_tags(args)
    note = build_note(args, captured_at)

    payload = {
        "title": args.title,
        "note": note,
        "project": args.project,
        "due": args.due,
        "defer": args.defer_date,
        "flagged": args.flagged,
        "tags": tags,
    }

    if args.dry_run:
        print(json.dumps({"status": "dry-run", "payload": payload}, indent=2))
        return 0

    client = OmniFocusClient()
    existing = find_existing(client, args.title, args.source_url, PRIMARY_TAG)
    if existing:
        result = {
            "status": "skipped",
            "reason": existing["reason"],
            "task": existing["task"],
        }
        print(json.dumps(result, indent=2))
        return 0

    created = client.create_task(
        args.title,
        note=note,
        project=args.project,
        due_date=args.due,
        defer_date=args.defer_date,
        flagged=args.flagged,
        tags=None,
    )

    for tag in tags:
        client.add_task_tag(created["id"], tag, create_missing=True)

    print(json.dumps({"status": "created", "task": created, "tags": tags}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
