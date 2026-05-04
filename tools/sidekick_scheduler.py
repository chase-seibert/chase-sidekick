#!/usr/bin/env python3
"""Dispatch scheduled Sidekick tasks from a human-readable TOML file.

Cron should call this script at each configured slot. The script exits without
starting Codex unless an enabled task is scheduled for the current day and slot.
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only relevant on old Python.
    tomllib = None  # type: ignore[assignment]


TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(TOOLS_DIR))

from codex_app_runner import CodexRunResult, execute_codex_with_fallback


DEFAULT_SCHEDULE_PATH = REPO_ROOT / "local" / "sidekick_schedule.toml"
DEFAULT_TIMEOUT = 1800
DEFAULT_WINDOW_MINUTES = 20
DEFAULT_SLOTS = {
    "morning": "08:00",
    "midday": "13:00",
    "evening": "17:00",
}

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
WEEKENDS = ["sat", "sun"]
ALL_DAYS = WEEKDAYS + WEEKENDS


class ScheduleError(Exception):
    """Raised when the schedule file is malformed."""


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run due Sidekick scheduled tasks without starting Codex when no work is due."
    )
    parser.add_argument(
        "--schedule",
        default=str(DEFAULT_SCHEDULE_PATH),
        help=f"TOML schedule file (default: {DEFAULT_SCHEDULE_PATH}).",
    )
    parser.add_argument(
        "--slot",
        help="Force a slot name instead of detecting one from the current time.",
    )
    parser.add_argument(
        "--now",
        help="Override the current local datetime for testing, e.g. 2026-05-04T08:00.",
    )
    parser.add_argument(
        "--window-minutes",
        type=positive_int,
        default=DEFAULT_WINDOW_MINUTES,
        help=(
            "Minutes after a configured slot time that still count as that slot "
            f"(default: {DEFAULT_WINDOW_MINUTES})."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=positive_int,
        default=DEFAULT_TIMEOUT,
        help=f"Per-task Codex timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print due tasks and prompts without invoking Codex.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the configured slots and tasks, then exit.",
    )
    parser.add_argument(
        "--mark-codex-unread",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Leave completed Codex Desktop sessions marked unread (default: enabled).",
    )
    return parser.parse_args(argv)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer")
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def parse_now(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now().astimezone()

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as e:
        raise ScheduleError(f"--now must be ISO format, e.g. 2026-05-04T08:00: {value}") from e
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed.astimezone()


def load_schedule(path: Path) -> Dict[str, Any]:
    if tomllib is None:
        raise ScheduleError("Python 3.11+ is required because this tool uses stdlib tomllib.")
    if not path.exists():
        return {
            "slots": DEFAULT_SLOTS.copy(),
            "tasks": [],
            "_missing_path": str(path),
        }
    with path.open("rb") as handle:
        schedule = tomllib.load(handle)
    if not isinstance(schedule, dict):
        raise ScheduleError("Schedule file must contain a TOML table.")
    return schedule


def load_slots(schedule: Dict[str, Any]) -> Dict[str, str]:
    raw_slots = schedule.get("slots") or DEFAULT_SLOTS
    if not isinstance(raw_slots, dict):
        raise ScheduleError("[slots] must be a TOML table.")

    slots = {}
    for name, slot_time in raw_slots.items():
        if not isinstance(name, str) or not isinstance(slot_time, str):
            raise ScheduleError("Slot names and times must be strings.")
        parse_slot_time(slot_time)
        slots[name.strip().lower()] = slot_time.strip()

    if not slots:
        raise ScheduleError("At least one slot must be configured.")
    return slots


def parse_slot_time(value: str) -> Tuple[int, int]:
    parts = value.split(":")
    if len(parts) != 2:
        raise ScheduleError(f"Slot time must be HH:MM, got {value!r}.")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as e:
        raise ScheduleError(f"Slot time must be HH:MM, got {value!r}.") from e
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ScheduleError(f"Slot time out of range: {value!r}.")
    return hour, minute


def detect_slot(
    slots: Dict[str, str],
    now: datetime,
    forced_slot: Optional[str],
    window_minutes: int,
) -> Optional[str]:
    if forced_slot:
        normalized = forced_slot.strip().lower()
        if normalized not in slots:
            raise ScheduleError(
                f"Unknown slot {forced_slot!r}. Available slots: {', '.join(sorted(slots))}"
            )
        return normalized

    candidates = []
    for name, slot_time in slots.items():
        hour, minute = parse_slot_time(slot_time)
        slot_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        delta = now - slot_datetime
        if timedelta(0) <= delta < timedelta(minutes=window_minutes):
            candidates.append((delta, name))

    if not candidates:
        return None

    candidates.sort()
    return candidates[0][1]


def local_day_name(now: datetime) -> str:
    return ALL_DAYS[now.weekday()]


def configured_tasks(schedule: Dict[str, Any]) -> List[Dict[str, Any]]:
    tasks = schedule.get("tasks") or []
    if not isinstance(tasks, list):
        raise ScheduleError("[[tasks]] entries must be an array of TOML tables.")
    for task in tasks:
        if not isinstance(task, dict):
            raise ScheduleError("Each [[tasks]] entry must be a TOML table.")
    return tasks


def normalize_days(values: Any) -> List[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        raise ScheduleError("Task days must be a string or list of strings.")

    days = []
    for value in values:
        if not isinstance(value, str):
            raise ScheduleError("Task days must be strings.")
        normalized = value.strip().lower()
        if normalized == "all":
            days.extend(ALL_DAYS)
        elif normalized == "weekday":
            days.extend(WEEKDAYS)
        elif normalized == "weekend":
            days.extend(WEEKENDS)
        elif normalized in ALL_DAYS:
            days.append(normalized)
        else:
            raise ScheduleError(f"Unknown day {value!r}.")

    return sorted(set(days), key=ALL_DAYS.index)


def task_slots(task: Dict[str, Any]) -> List[str]:
    if "slots" in task:
        raw_slots = task["slots"]
    elif "slot" in task:
        raw_slots = task["slot"]
    else:
        raise ScheduleError(f"Task {task_name(task)!r} must include slot or slots.")

    if isinstance(raw_slots, str):
        raw_slots = [raw_slots]
    if not isinstance(raw_slots, list):
        raise ScheduleError(f"Task {task_name(task)!r} slot must be a string or list of strings.")

    slots = []
    for slot in raw_slots:
        if not isinstance(slot, str):
            raise ScheduleError(f"Task {task_name(task)!r} slot names must be strings.")
        slots.append(slot.strip().lower())
    return slots


def task_enabled(task: Dict[str, Any]) -> bool:
    return bool(task.get("enabled", True))


def task_name(task: Dict[str, Any], index: Optional[int] = None) -> str:
    name = task.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    if index is None:
        return "unnamed task"
    return f"task-{index + 1}"


def due_tasks(
    tasks: Iterable[Dict[str, Any]],
    day: str,
    slot: str,
    slots: Dict[str, str],
) -> List[Tuple[int, Dict[str, Any]]]:
    due = []
    for index, task in enumerate(tasks):
        if not task_enabled(task):
            continue
        days = normalize_days(task.get("days", "all"))
        if day not in days:
            continue
        configured_slots = task_slots(task)
        unknown_slots = sorted(set(configured_slots) - set(slots))
        if unknown_slots:
            raise ScheduleError(
                f"Task {task_name(task, index)!r} references unknown slot(s): "
                f"{', '.join(unknown_slots)}"
            )
        if slot in configured_slots:
            due.append((index, task))
    return due


def build_prompt(task: Dict[str, Any], index: int) -> str:
    name = task_name(task, index)
    pieces = [f"Scheduled Sidekick task: {name}", ""]

    skills = task.get("skills")
    if skills is None and task.get("skill") is not None:
        skills = [task.get("skill")]
    elif isinstance(skills, str):
        skills = [skills]

    if skills is not None:
        if not isinstance(skills, list) or not all(isinstance(skill, str) for skill in skills):
            raise ScheduleError(f"Task {name!r} skill/skills must be string values.")
        normalized_skills = [skill.strip() for skill in skills if skill.strip()]
        if len(normalized_skills) == 1:
            pieces.append(f"Use the {normalized_skills[0]} skill.")
            pieces.append("")
        elif normalized_skills:
            pieces.append("Use these skills: " + ", ".join(normalized_skills) + ".")
            pieces.append("")

    prompt = task.get("prompt")
    if prompt is not None:
        if not isinstance(prompt, str):
            raise ScheduleError(f"Task {name!r} prompt must be a string.")
        stripped_prompt = prompt.strip()
        if stripped_prompt:
            pieces.append(stripped_prompt)
            pieces.append("")

    result = "\n".join(pieces).strip()
    if not result or result == f"Scheduled Sidekick task: {name}":
        raise ScheduleError(f"Task {name!r} must include skill, skills, and/or prompt.")
    return result


def print_schedule(schedule_path: Path, slots: Dict[str, str], tasks: List[Dict[str, Any]]) -> None:
    if not schedule_path.exists():
        log(f"No schedule file found at {schedule_path}")
    print("Slots:")
    for name, slot_time in sorted(slots.items(), key=lambda item: item[1]):
        print(f"  {name}: {slot_time}")

    print("\nTasks:")
    if not tasks:
        print("  (none)")
        return

    for index, task in enumerate(tasks):
        enabled = "enabled" if task_enabled(task) else "disabled"
        days = ", ".join(normalize_days(task.get("days", "all")))
        slots_for_task = ", ".join(task_slots(task))
        print(f"  {task_name(task, index)} [{enabled}] {days} @ {slots_for_task}")


def execute_task(
    task: Dict[str, Any],
    index: int,
    timeout: int,
    mark_codex_unread: bool,
) -> CodexRunResult:
    prompt = build_prompt(task, index)
    name = task_name(task, index)
    log(f"Starting scheduled task: {name}")
    result = execute_codex_with_fallback(
        prompt=prompt,
        working_dir=str(REPO_ROOT),
        timeout=timeout,
        thread_name=f"Scheduled: {name}",
        mark_unread=mark_codex_unread,
    )
    if result.thread_id:
        log(f"Finished {name} via {result.runner}; thread id: {result.thread_id}")
    else:
        log(f"Finished {name} via {result.runner}")
    if not result.success:
        log(f"Task failed: {name}")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    try:
        schedule_path = Path(args.schedule).expanduser()
        now = parse_now(args.now)
        schedule = load_schedule(schedule_path)
        slots = load_slots(schedule)
        tasks = configured_tasks(schedule)

        if args.list:
            print_schedule(schedule_path, slots, tasks)
            return 0

        if schedule.get("_missing_path"):
            log(
                "No schedule file found; nothing to run. "
                f"Create {schedule['_missing_path']} from examples/sidekick_schedule.toml."
            )
            return 0

        slot = detect_slot(slots, now, args.slot, args.window_minutes)
        if not slot:
            log("No configured slot is due right now; nothing to run.")
            return 0

        day = local_day_name(now)
        matching_tasks = due_tasks(tasks, day, slot, slots)
        if not matching_tasks:
            log(f"No tasks scheduled for {day} @ {slot}; nothing to run.")
            return 0

        if args.dry_run:
            log(f"Dry run for {day} @ {slot}; {len(matching_tasks)} task(s) would run.")
            for index, task in matching_tasks:
                print()
                print(f"--- {task_name(task, index)} ---")
                print(build_prompt(task, index))
            return 0

        failures = 0
        for index, task in matching_tasks:
            result = execute_task(
                task=task,
                index=index,
                timeout=args.timeout,
                mark_codex_unread=args.mark_codex_unread,
            )
            if not result.success:
                failures += 1

        return 1 if failures else 0
    except ScheduleError as e:
        log(f"Scheduler error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
