#!/usr/bin/env python3
"""Launch Codex meeting-note drafts from recent calendar events and miclog activity.

This watcher is intended for cron. It looks for the latest timed calendar event
that ended recently or is in its final minutes, confirms that memory/miclog.txt
has transcript lines for that event window, and launches Codex with the
meeting-notes-from-miclog skill.
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(TOOLS_DIR))

from codex_app_runner import CodexRunResult, execute_codex_with_fallback
from sidekick.config import get_google_config
from sidekick.clients.gcalendar import GCalendarClient


DEFAULT_ENDED_WINDOW_MINUTES = 30
DEFAULT_ENDING_WINDOW_MINUTES = 5
DEFAULT_MICLOG_BUFFER_MINUTES = 5
DEFAULT_MAX_MICLOG_CHARS = 60000
DEFAULT_EXECUTION_TIMEOUT = 900
DEFAULT_CALENDAR_LOOKBACK_HOURS = 12

MICLOG_LINE_RE = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*(.*)")
URL_RE = re.compile(r"https?://[^\s<>\"]+")


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer")
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch Google Calendar and memory/miclog.txt for meetings ready to summarize."
    )
    parser.add_argument("--calendar-id", default="primary")
    parser.add_argument(
        "--miclog-path",
        default=str(REPO_ROOT / "memory" / "miclog.txt"),
        help="Path to miclog.txt.",
    )
    parser.add_argument(
        "--state-path",
        default=str(REPO_ROOT / "cache" / "miclog_meeting_notes_watcher_state.json"),
        help="Path to duplicate-prevention state.",
    )
    parser.add_argument(
        "--window-ended-minutes",
        type=positive_int,
        default=DEFAULT_ENDED_WINDOW_MINUTES,
        help="Include meetings that ended within this many minutes.",
    )
    parser.add_argument(
        "--window-ending-minutes",
        type=positive_int,
        default=DEFAULT_ENDING_WINDOW_MINUTES,
        help="Include meetings ending within this many future minutes.",
    )
    parser.add_argument(
        "--miclog-buffer-minutes",
        type=positive_int,
        default=DEFAULT_MICLOG_BUFFER_MINUTES,
        help="Miclog selection buffer before event start and after event end.",
    )
    parser.add_argument(
        "--max-miclog-chars",
        type=positive_int,
        default=DEFAULT_MAX_MICLOG_CHARS,
        help="Maximum miclog excerpt characters to pass to Codex.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selected event and prompt preview without launching Codex or updating state.",
    )
    parser.add_argument(
        "--mark-codex-unread",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Leave Codex Desktop sessions marked unread after trigger runs.",
    )
    parser.add_argument(
        "--now",
        help="Override current time for debugging, in ISO format with optional timezone.",
    )
    return parser.parse_args(argv)


def local_now(now_arg: Optional[str] = None) -> datetime:
    if not now_arg:
        return datetime.now().astimezone()
    parsed = parse_datetime(now_arg)
    if parsed is None:
        raise ValueError(f"Invalid --now datetime: {now_arg}")
    return parsed.astimezone()


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone()


def parse_miclog_datetime(value: str) -> datetime:
    naive = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return naive.astimezone()


def event_start_end(event: dict) -> Tuple[Optional[datetime], Optional[datetime]]:
    start = event.get("start") or {}
    end = event.get("end") or {}
    if start.get("date") or end.get("date"):
        return None, None
    return parse_datetime(start.get("dateTime")), parse_datetime(end.get("dateTime"))


def is_event_eligible(
    event: dict,
    now: datetime,
    ended_window: timedelta,
    ending_window: timedelta,
) -> bool:
    start, end = event_start_end(event)
    if start is None or end is None:
        return False
    if event.get("status") == "cancelled":
        return False
    if end < now - ended_window:
        return False
    if end > now + ending_window:
        return False
    return True


def load_calendar_client() -> GCalendarClient:
    config = get_google_config()
    return GCalendarClient(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        refresh_token=config["refresh_token"],
    )


def load_candidate_events(
    client: GCalendarClient,
    calendar_id: str,
    now: datetime,
    ended_window: timedelta,
    ending_window: timedelta,
) -> List[dict]:
    time_min = now - timedelta(hours=DEFAULT_CALENDAR_LOOKBACK_HOURS)
    time_max = now + ending_window + timedelta(minutes=10)
    events = client.list_events_paginated(
        calendar_id=calendar_id,
        time_min=time_min.isoformat(),
        time_max=time_max.isoformat(),
        max_results=100,
    )
    eligible = [
        event
        for event in events
        if is_event_eligible(event, now, ended_window, ending_window)
    ]
    return sorted(
        eligible,
        key=lambda event: event_start_end(event)[1] or datetime.min.astimezone(),
        reverse=True,
    )


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"events": {}}
    try:
        with path.open("r") as state_file:
            state = json.load(state_file)
    except (OSError, json.JSONDecodeError):
        return {"events": {}}
    if not isinstance(state, dict):
        return {"events": {}}
    if not isinstance(state.get("events"), dict):
        state["events"] = {}
    return state


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w") as state_file:
        json.dump(state, state_file, indent=2, sort_keys=True)
        state_file.write("\n")
    temp_path.replace(path)


def iter_miclog_lines(path: Path) -> Iterable[Tuple[datetime, str, str]]:
    with path.open("r", errors="replace") as miclog:
        for raw_line in miclog:
            match = MICLOG_LINE_RE.search(raw_line)
            if not match:
                continue
            timestamp = parse_miclog_datetime(match.group(1))
            text = match.group(2).strip()
            yield timestamp, text, raw_line.rstrip("\n")


def miclog_excerpt_for_event(
    miclog_path: Path,
    event: dict,
    now: datetime,
    buffer: timedelta,
) -> Tuple[List[Tuple[datetime, str, str]], datetime, datetime]:
    start, end = event_start_end(event)
    if start is None or end is None:
        return [], now, now

    lower = start - buffer
    upper = min(end + buffer, now)
    lines = [
        line
        for line in iter_miclog_lines(miclog_path)
        if lower <= line[0] <= upper
    ]
    return lines, lower, upper


def last_processed_miclog_ts(state: dict, event: dict) -> Optional[datetime]:
    event_id = event.get("id") or ""
    event_state = state.get("events", {}).get(event_id) or {}
    return parse_datetime(event_state.get("miclog_last_ts"))


def has_new_miclog_activity(
    state: dict,
    event: dict,
    miclog_lines: List[Tuple[datetime, str, str]],
) -> bool:
    if not miclog_lines:
        return False
    previous = last_processed_miclog_ts(state, event)
    if previous is None:
        return True
    latest = miclog_lines[-1][0]
    return latest > previous


def clean_description(description: str) -> str:
    if not description:
        return ""
    text = html.unescape(description)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def attendee_label(attendee: dict) -> str:
    name = attendee.get("displayName")
    email = attendee.get("email")
    status = attendee.get("responseStatus")
    label = name or email or "(unknown attendee)"
    if email and name:
        label = f"{name} <{email}>"
    if status:
        label = f"{label} ({status})"
    return label


def event_links(event: dict) -> List[str]:
    values = [
        event.get("description") or "",
        event.get("location") or "",
        event.get("hangoutLink") or "",
    ]
    conference_data = event.get("conferenceData") or {}
    for entry in conference_data.get("entryPoints") or []:
        uri = entry.get("uri")
        if uri:
            values.append(uri)

    links: List[str] = []
    seen = set()
    for value in values:
        for match in URL_RE.finditer(value):
            url = match.group(0).rstrip(").,;")
            if url not in seen:
                seen.add(url)
                links.append(url)
    return links


def format_time_range(start: Optional[datetime], end: Optional[datetime]) -> str:
    if not start or not end:
        return "(unknown time)"
    return f"{start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%H:%M %Z')}"


def truncate_excerpt(text: str, max_chars: int) -> Tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    head_chars = max_chars // 2
    tail_chars = max_chars - head_chars
    omitted = len(text) - max_chars
    return (
        text[:head_chars].rstrip()
        + f"\n\n[... {omitted} characters omitted from the middle; read memory/miclog.txt if needed ...]\n\n"
        + text[-tail_chars:].lstrip(),
        True,
    )


def build_prompt(
    event: dict,
    miclog_lines: List[Tuple[datetime, str, str]],
    miclog_path: Path,
    excerpt_lower: datetime,
    excerpt_upper: datetime,
    max_miclog_chars: int,
) -> str:
    start, end = event_start_end(event)
    attendees = [attendee_label(attendee) for attendee in event.get("attendees") or []]
    description = clean_description(event.get("description") or "")
    links = event_links(event)
    raw_excerpt = "\n".join(raw_line for _, _, raw_line in miclog_lines)
    excerpt, truncated = truncate_excerpt(raw_excerpt, max_miclog_chars)
    truncation_note = (
        "\nThe miclog excerpt was truncated; read the source file and the stated time window if more detail is needed."
        if truncated
        else ""
    )

    return f"""Use $meeting-notes-from-miclog to produce draft-only meeting notes.

Return only copy/paste-ready Markdown notes. Do not write files, update Confluence, send email, post to Slack, or create external drafts.

The watcher selected this calendar event. Do not switch to a different meeting unless the provided metadata is clearly inconsistent with the transcript.

Meeting:
- Title: {event.get("summary") or "(No title)"}
- Event ID: {event.get("id") or "(unknown)"}
- Time: {format_time_range(start, end)}
- Calendar link: {event.get("htmlLink") or "(none)"}
- Attendees: {", ".join(attendees) if attendees else "(none listed)"}

Event description:
{description or "(none)"}

Event links:
{chr(10).join(f"- {link}" for link in links) if links else "- (none found)"}

Miclog source:
- Path: {miclog_path.relative_to(REPO_ROOT) if miclog_path.is_relative_to(REPO_ROOT) else miclog_path}
- Selected window: {excerpt_lower.strftime('%Y-%m-%d %H:%M:%S %Z')} to {excerpt_upper.strftime('%Y-%m-%d %H:%M:%S %Z')}
- Lines selected: {len(miclog_lines)}{truncation_note}

Miclog excerpt:
```text
{excerpt}
```
"""


def select_event_with_miclog(
    events: List[dict],
    miclog_path: Path,
    now: datetime,
    buffer: timedelta,
    state: dict,
) -> Optional[Tuple[dict, List[Tuple[datetime, str, str]], datetime, datetime]]:
    for event in events:
        lines, lower, upper = miclog_excerpt_for_event(miclog_path, event, now, buffer)
        if not lines:
            log(f"Skipping '{event.get('summary', '(No title)')}' because no miclog lines overlap")
            continue
        if not has_new_miclog_activity(state, event, lines):
            log(f"Skipping '{event.get('summary', '(No title)')}' because miclog activity was already processed")
            continue
        return event, lines, lower, upper
    return None


def update_state_for_success(
    state: dict,
    event: dict,
    miclog_lines: List[Tuple[datetime, str, str]],
    result: CodexRunResult,
) -> None:
    event_id = event.get("id") or ""
    if not event_id or not miclog_lines:
        return
    state.setdefault("events", {})[event_id] = {
        "summary": event.get("summary") or "",
        "miclog_last_ts": miclog_lines[-1][0].isoformat(),
        "processed_at": datetime.now().astimezone().isoformat(),
        "runner": result.runner,
        "thread_id": result.thread_id,
    }


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    now = local_now(args.now)
    miclog_path = Path(args.miclog_path).expanduser()
    state_path = Path(args.state_path).expanduser()

    log("=== Miclog Meeting Notes Watcher Starting ===")
    log(f"Now: {now.isoformat()}")
    log(f"Miclog path: {miclog_path}")
    log(f"Dry run: {args.dry_run}")

    if not miclog_path.exists():
        log(f"No miclog file found at {miclog_path}")
        return 0

    state = load_state(state_path)
    ended_window = timedelta(minutes=args.window_ended_minutes)
    ending_window = timedelta(minutes=args.window_ending_minutes)
    buffer = timedelta(minutes=args.miclog_buffer_minutes)

    client = load_calendar_client()
    events = load_candidate_events(
        client=client,
        calendar_id=args.calendar_id,
        now=now,
        ended_window=ended_window,
        ending_window=ending_window,
    )
    log(f"Found {len(events)} eligible calendar event(s)")

    selected = select_event_with_miclog(
        events=events,
        miclog_path=miclog_path,
        now=now,
        buffer=buffer,
        state=state,
    )
    if not selected:
        log("No meeting with new miclog activity found")
        return 0

    event, miclog_lines, excerpt_lower, excerpt_upper = selected
    prompt = build_prompt(
        event=event,
        miclog_lines=miclog_lines,
        miclog_path=miclog_path,
        excerpt_lower=excerpt_lower,
        excerpt_upper=excerpt_upper,
        max_miclog_chars=args.max_miclog_chars,
    )
    log(f"Selected event: {event.get('summary') or '(No title)'}")
    log(f"Selected miclog lines: {len(miclog_lines)}")

    if args.dry_run:
        log("Dry run enabled; Codex will not be launched and state will not be updated")
        print("\n--- Prompt Preview ---\n")
        print(prompt[:4000])
        if len(prompt) > 4000:
            print(f"\n[Prompt preview truncated; full prompt is {len(prompt)} characters]")
        return 0

    result = execute_codex_with_fallback(
        prompt=prompt,
        working_dir=str(REPO_ROOT),
        timeout=DEFAULT_EXECUTION_TIMEOUT,
        thread_name=f"Meeting notes: {event.get('summary') or 'recent meeting'}",
        mark_unread=args.mark_codex_unread,
    )
    log(f"Codex runner: {result.runner}")
    if result.thread_id:
        log(f"Codex thread id: {result.thread_id}")
    log(f"Codex success: {result.success}")
    log(f"Codex duration: {result.duration:.1f}s")

    if not result.success:
        log(result.output or "Codex failed without output")
        return 1

    update_state_for_success(state, event, miclog_lines, result)
    save_state(state_path, state)
    log(f"Updated state: {state_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
