#!/usr/bin/env python3
"""OmniFocus trigger watcher - processes Codex tasks from the Inbox.

This script scans OmniFocus Inbox tasks whose name starts with "Codex",
marks each selected task as processed before execution, runs Codex with the
task prompt, and appends the output to the task note. It never completes tasks.

Usage:
    python3 tools/omnifocus_trigger_watcher.py
    python3 tools/omnifocus_trigger_watcher.py --max-tasks 3
    python3 tools/omnifocus_trigger_watcher.py --dry-run

Expected task formats:
    Codex <your prompt here>
    Codex
        <your prompt here in the note>

Shortcuts:
    Codex 1:1 Alex foo bar bat
    Codex meeting Core Eng LT staffing concerns for hiring IC5s
"""
import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent

# Add project and tools directories to path for imports
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(TOOLS_DIR))

from codex_app_runner import CodexRunResult, execute_codex_with_fallback
from sidekick import config
from sidekick.clients.omnifocus import OmniFocusClient


DEFAULT_TASKS_PER_RUN = 1
DEFAULT_SCAN_LIMIT = 200
EXECUTION_TIMEOUT = 300
PROCESSED_TAG = "processed"
TRIGGER_WORD = "Codex"

ONE_ON_ONE_DOCS_PATH = REPO_ROOT / "local" / "one-on-ones.md"
MEETING_DOCS_PATH = REPO_ROOT / "local" / "meetings.md"


def log(message: str) -> None:
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def positive_int(value: str) -> int:
    """Parse a positive integer argument."""
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer")

    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")

    return parsed


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Monitor OmniFocus Inbox tasks for Codex trigger prompts."
    )
    parser.add_argument(
        "--max-tasks",
        type=positive_int,
        default=DEFAULT_TASKS_PER_RUN,
        help=(
            "Maximum trigger tasks to process this run, in Inbox order "
            f"(default: {DEFAULT_TASKS_PER_RUN})."
        ),
    )
    parser.add_argument(
        "--scan-limit",
        type=positive_int,
        default=DEFAULT_SCAN_LIMIT,
        help=(
            "Maximum Inbox tasks to scan for trigger tasks "
            f"(default: {DEFAULT_SCAN_LIMIT})."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview matching tasks and prompt expansion without mutating or running Codex.",
    )
    return parser.parse_args(argv)


def execute_codex(prompt: str, working_dir: str) -> CodexRunResult:
    """Execute Codex with the given prompt."""
    log(f"Executing Codex with Desktop-visible app-server runner: {prompt[:100]}...")
    result = execute_codex_with_fallback(
        prompt=prompt,
        working_dir=working_dir,
        timeout=EXECUTION_TIMEOUT,
    )
    if result.thread_id:
        log(f"Codex runner: {result.runner}; thread id: {result.thread_id}")
    else:
        log(f"Codex runner: {result.runner}")

    if result.success:
        log(f"Codex executed successfully in {result.duration:.1f}s")
    else:
        log(f"Codex failed via {result.runner}")

    return result


def normalize_tag_names(task: dict) -> List[str]:
    """Return task tag names from either summary or detailed task shape."""
    tags = task.get("tags", []) or []
    tag_names = []

    for tag in tags:
        if isinstance(tag, dict):
            name = tag.get("name")
        else:
            name = tag
        if name:
            tag_names.append(str(name))

    return tag_names


def task_has_tag(task: dict, tag_name: str) -> bool:
    """Check whether a task already has a tag, case-insensitively."""
    expected = tag_name.lower()
    return any(name.lower() == expected for name in normalize_tag_names(task))


def is_trigger_task(task: dict) -> bool:
    """Return True when a task name starts with the Codex trigger word."""
    name = task.get("name", "") or ""
    return re.match(rf"^{re.escape(TRIGGER_WORD)}(\s+|$)", name, re.IGNORECASE) is not None


def extract_prompt(task_name: str, task_note: str) -> Optional[str]:
    """Extract a Codex prompt from task name or note."""
    match = re.match(
        rf"^{re.escape(TRIGGER_WORD)}(?:\s+(.+))?$",
        task_name or "",
        re.IGNORECASE,
    )
    if not match:
        return None

    prompt = (match.group(1) or "").strip()
    if prompt:
        return prompt

    note_prompt = (task_note or "").strip()
    if note_prompt:
        return note_prompt

    return None


def load_omnifocus_client() -> OmniFocusClient:
    """Create an OmniFocus client with optional repo configuration."""
    default_project = None
    default_tag = None

    try:
        omnifocus_config = config.get_omnifocus_config()
        default_project = omnifocus_config.get("default_project")
        default_tag = omnifocus_config.get("default_tag")
    except ValueError:
        pass

    return OmniFocusClient(
        default_project=default_project,
        default_tag=default_tag,
    )


def load_one_on_one_docs(path: Path = ONE_ON_ONE_DOCS_PATH) -> Dict[str, str]:
    """Load 1:1 doc links keyed by visible person name."""
    docs = {}
    link_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")

    content = path.read_text()
    for match in link_pattern.finditer(content):
        docs[match.group(1).strip().lower()] = match.group(2).strip()

    return docs


def load_meeting_docs(path: Path = MEETING_DOCS_PATH) -> List[dict]:
    """Load meeting doc links from heading blocks in local/meetings.md."""
    meetings = []
    current_title = None
    current_url = None
    heading_pattern = re.compile(r"^#{2,}\s+(.+?)\s*$")
    url_pattern = re.compile(r"https?://\S+")

    def flush_current() -> None:
        if current_title and current_url:
            meetings.append({
                "title": current_title,
                "url": current_url.rstrip(").,"),
            })

    for line in path.read_text().splitlines():
        heading_match = heading_pattern.match(line)
        if heading_match:
            flush_current()
            current_title = heading_match.group(1).strip()
            current_url = None
            continue

        if current_title and not current_url:
            url_match = url_pattern.search(line)
            if url_match:
                current_url = url_match.group(0)

    flush_current()
    return meetings


def build_one_on_one_prompt(person_name: str, topic: str, page_url: str) -> str:
    """Build the Codex prompt for adding a 1:1 agenda topic."""
    return f"""Use the confluence-meeting-notes-update skill to add this topic to the next agenda section of my 1:1 document.

Person: {person_name}
Document: {page_url}
Topic: {topic}
"""


def build_meeting_prompt(meeting_name: str, topic: str, page_url: str) -> str:
    """Build the Codex prompt for adding a meeting agenda topic."""
    return f"""Use the confluence-meeting-notes-update skill to add this topic to the next agenda section of this meeting notes document.

Meeting: {meeting_name}
Document: {page_url}
Topic: {topic}
"""


def expand_prompt(prompt: str) -> Tuple[str, str]:
    """Expand shortcut prompts into the full Codex prompt."""
    one_on_one_match = re.match(r"^1:1\s+(\S+)(?:\s+(.+))?$", prompt, re.IGNORECASE)
    if one_on_one_match:
        person_name = one_on_one_match.group(1).strip()
        topic = (one_on_one_match.group(2) or "").strip()
        if not topic:
            raise ValueError(f"Missing agenda topic for 1:1 shortcut: {prompt}")

        one_on_one_docs = load_one_on_one_docs()
        page_url = one_on_one_docs.get(person_name.lower())
        if not page_url:
            available = ", ".join(sorted(one_on_one_docs.keys()))
            raise ValueError(
                f"No 1:1 doc found for '{person_name}' in {ONE_ON_ONE_DOCS_PATH.relative_to(REPO_ROOT)}. "
                f"Available names: {available}"
            )

        return (
            build_one_on_one_prompt(person_name, topic, page_url),
            f"1:1 shortcut for {person_name}",
        )

    meeting_match = re.match(r"^meeting\s+(.+)$", prompt, re.IGNORECASE)
    if meeting_match:
        meeting_text = meeting_match.group(1).strip()
        if not meeting_text:
            raise ValueError(f"Missing meeting name and topic for meeting shortcut: {prompt}")

        meetings = sorted(
            load_meeting_docs(),
            key=lambda item: len(item["title"]),
            reverse=True,
        )

        for meeting in meetings:
            title = meeting["title"]
            title_match = re.match(
                rf"^{re.escape(title)}(?:\s+(.+))?$",
                meeting_text,
                re.IGNORECASE,
            )
            if not title_match:
                continue

            topic = (title_match.group(1) or "").strip()
            if not topic:
                raise ValueError(f"Missing agenda topic for meeting shortcut: {prompt}")

            return (
                build_meeting_prompt(title, topic, meeting["url"]),
                f"meeting shortcut for {title}",
            )

        available = ", ".join(meeting["title"] for meeting in meetings)
        raise ValueError(
            f"No meeting doc heading matched '{meeting_text}' in {MEETING_DOCS_PATH.relative_to(REPO_ROOT)}. "
            f"Available meetings: {available}"
        )

    return prompt, "generic Codex prompt"


def format_started_note(task_name: str) -> str:
    """Format the note block added before Codex execution."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""=== Codex Processing Started ===
Started: {timestamp}
Task: {task_name}
Tag Applied: {PROCESSED_TAG}
"""


def format_result_note(
    success: bool,
    output: str,
    duration: float,
    original_prompt: str,
    executed_prompt: str,
    working_dir: str,
    exit_code: Optional[int],
    prompt_kind: str,
    runner: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> str:
    """Format the final result note block."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "success" if success else "failed"
    exit_code_text = str(exit_code) if exit_code is not None else "n/a"
    runner_text = runner or "n/a"
    thread_id_text = thread_id or "n/a"
    output = output if output else "(no output)"

    executed_prompt_section = ""
    if executed_prompt != original_prompt:
        executed_prompt_section = f"""
Executed Prompt:
{executed_prompt}
"""

    return f"""=== Codex Processing Result ===
Finished: {timestamp}
Status: {status}
Prompt Type: {prompt_kind}
Runner: {runner_text}
Codex Thread ID: {thread_id_text}
Duration: {duration:.1f}s
Working Directory: {working_dir}
Exit Code: {exit_code_text}

Original Prompt:
{original_prompt}
{executed_prompt_section}
Output:
{output}
"""


def find_trigger_tasks(
    client: OmniFocusClient,
    scan_limit: int,
    max_tasks: int,
) -> List[dict]:
    """Find unprocessed Codex trigger tasks in the OmniFocus Inbox."""
    inbox_tasks = client.get_inbox_tasks(limit=scan_limit)
    trigger_tasks = []

    for task in inbox_tasks:
        if not is_trigger_task(task):
            continue
        if task_has_tag(task, PROCESSED_TAG):
            log(f"Skipping already processed task: {task.get('name', '')}")
            continue
        trigger_tasks.append(task)

    if len(trigger_tasks) > max_tasks:
        log(f"Processing first {max_tasks} of {len(trigger_tasks)} trigger task(s)")

    return trigger_tasks[:max_tasks]


def process_task(
    client: OmniFocusClient,
    task_summary: dict,
    working_dir: str,
    dry_run: bool = False,
) -> bool:
    """Process a single OmniFocus trigger task."""
    task_id = task_summary.get("id")
    if not task_id:
        log("Skipping task without an ID")
        return False

    try:
        task = client.get_task(task_id)
    except Exception as e:
        log(f"Could not read task {task_id}: {e}")
        return False

    task_name = task.get("name", "") or task_summary.get("name", "")
    task_note = task.get("note", "") or ""

    log(f"Processing task: {task_name}")
    log(f"Task ID: {task_id}")

    original_prompt = ""
    executed_prompt = ""
    prompt_kind = "unresolved prompt"
    process_start = time.time()

    if dry_run:
        try:
            original_prompt = extract_prompt(task_name, task_note) or ""
            if not original_prompt:
                raise ValueError("Could not extract prompt from task name or note")
            executed_prompt, prompt_kind = expand_prompt(original_prompt)
            log(f"[dry-run] Would mark task as {PROCESSED_TAG} and append start/result notes")
            log(f"[dry-run] Prompt type: {prompt_kind}")
            log(f"[dry-run] Original prompt: {original_prompt}")
            if executed_prompt != original_prompt:
                log(f"[dry-run] Expanded prompt: {executed_prompt}")
            return True
        except Exception as e:
            log(f"[dry-run] Would mark task processed, then record failure: {e}")
            return False

    started_note = format_started_note(task_name)
    try:
        log(f"Adding {PROCESSED_TAG} tag and start note before execution...")
        client.mark_task_processed(task_id, started_note)
    except Exception as e:
        log(f"Failed to mark task as processed; Codex will not run: {e}")
        return False

    try:
        original_prompt = extract_prompt(task_name, task_note) or ""
        if not original_prompt:
            raise ValueError("Could not extract prompt from task name or note")

        executed_prompt, prompt_kind = expand_prompt(original_prompt)
        result = execute_codex(executed_prompt, working_dir)
        result_note = format_result_note(
            success=result.success,
            output=result.output,
            duration=result.duration,
            original_prompt=original_prompt,
            executed_prompt=executed_prompt,
            working_dir=working_dir,
            exit_code=result.exit_code,
            prompt_kind=prompt_kind,
            runner=result.runner,
            thread_id=result.thread_id,
        )
        client.append_task_note(task_id, result_note)
        return result.success

    except Exception as e:
        duration = time.time() - process_start
        failure_note = format_result_note(
            success=False,
            output=str(e),
            duration=duration,
            original_prompt=original_prompt or "(not extracted)",
            executed_prompt=executed_prompt or original_prompt or "(not executed)",
            working_dir=working_dir,
            exit_code=None,
            prompt_kind=prompt_kind,
            runner="not run",
            thread_id=None,
        )
        try:
            client.append_task_note(task_id, failure_note)
        except Exception as append_error:
            log(f"Failed to append failure note to processed task {task_id}: {append_error}")
        log(f"Failed to process task {task_id}: {e}")
        return False


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    args = parse_args(argv)
    log("=== OmniFocus Trigger Watcher Starting ===")
    log(f"Max tasks to process this run: {args.max_tasks}")
    log(f"Scan limit: {args.scan_limit}")
    if args.dry_run:
        log("Dry run enabled: no tasks will be mutated and Codex will not run")

    try:
        client = load_omnifocus_client()
        tasks = find_trigger_tasks(
            client=client,
            scan_limit=args.scan_limit,
            max_tasks=args.max_tasks,
        )
        log(f"Found {len(tasks)} unprocessed Codex trigger task(s)")

        if not tasks:
            log("No trigger tasks found")
            return

        working_dir = str(REPO_ROOT)
        log(f"Working directory: {working_dir}")

        processed_count = 0
        for index, task in enumerate(tasks, 1):
            log(f"\n--- Processing task {index}/{len(tasks)} ---")
            if process_task(client, task, working_dir, dry_run=args.dry_run):
                processed_count += 1

        log(f"\n=== Completed: {processed_count}/{len(tasks)} task(s) processed successfully ===")

    except Exception as e:
        log(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
