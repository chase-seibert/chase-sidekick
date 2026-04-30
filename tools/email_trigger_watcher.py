#!/usr/bin/env python3
"""Email trigger watcher - monitors Gmail for agent emails and executes prompts.

This script polls Gmail for unread emails with an agent name as the first word
in the subject, executes the prompt using that agent's CLI, and replies with
the results.

Usage:
    python3 tools/email_trigger_watcher.py
    python3 tools/email_trigger_watcher.py --max-emails 3
    python3 tools/email_trigger_watcher.py --no-mark-codex-unread

Expected email format:
    Subject: Claude <your prompt here>
    OR
    Subject: Claude
    Body: <your prompt here>

    Subject: Codex <your prompt here>
    OR
    Subject: Codex
    Body: <your prompt here>

Codex shortcut formats:
    Subject: Codex 1:1 Alex foo bar bat
    Subject: Codex meeting Core Eng LT staffing concerns for hiring IC5s

The script will:
1. Search for unread emails from allowed senders with the agent name as first word
2. Extract the prompt from subject or body
3. Execute the configured agent CLI command
4. Reply to the email with results
5. Mark the email as read
"""
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from email.utils import parseaddr
from typing import Dict, List, Optional, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent

# Add project and tools directories to path for imports
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(TOOLS_DIR))

from codex_app_runner import CodexRunResult, execute_codex_with_fallback
from sidekick import config
from sidekick.clients.gmail import GmailClient

# Configuration
DEFAULT_EMAILS_PER_RUN = 1
SEARCH_PAGE_SIZE = 100
EXECUTION_TIMEOUT = 300  # 5 minutes timeout for agent execution
MAX_HOURLY_EXECUTIONS = 20  # Rate limit

ONE_ON_ONE_DOCS_PATH = REPO_ROOT / "local" / "one-on-ones.md"
MEETING_DOCS_PATH = REPO_ROOT / "local" / "meetings.md"


def build_claude_command(prompt: str, working_dir: str) -> List[str]:
    """Build the Claude Code command for non-interactive execution."""
    return ["claude", "--print", prompt, "--output-format", "text"]


def build_codex_command(prompt: str, working_dir: str) -> List[str]:
    """Build the Codex command for non-interactive execution."""
    return [
        "codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--cd",
        working_dir,
        "--sandbox",
        "workspace-write",
        prompt,
    ]


AGENT_CONFIGS = {
    "claude": {
        "display_name": "Claude Code",
        "trigger_word": "Claude",
        "emails_env_var": "CLAUDE_TRIGGER_EMAILS",
        "fallback_emails_env_var": None,
        "cli_name": "claude",
        "state_file": "/tmp/claude_trigger_state.txt",
        "log_file": "/tmp/claude_trigger.log",
        "command_builder": build_claude_command,
    },
    "codex": {
        "display_name": "Codex",
        "trigger_word": "Codex",
        "emails_env_var": "CODEX_TRIGGER_EMAILS",
        "fallback_emails_env_var": "CLAUDE_TRIGGER_EMAILS",
        "cli_name": "codex",
        "state_file": "/tmp/codex_trigger_state.txt",
        "log_file": "/tmp/codex_trigger.log",
        "command_builder": build_codex_command,
        "use_codex_app_runner": True,
    },
}


def log(message: str):
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
        description="Monitor Gmail for unread Claude/Codex trigger emails."
    )
    parser.add_argument(
        "--max-emails",
        type=positive_int,
        default=DEFAULT_EMAILS_PER_RUN,
        help=(
            "Maximum trigger emails to process this run, starting with the "
            f"oldest matches (default: {DEFAULT_EMAILS_PER_RUN})."
        ),
    )
    parser.add_argument(
        "--mark-codex-unread",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Leave Codex Desktop sessions marked unread after trigger runs (default: enabled).",
    )
    return parser.parse_args(argv)


def check_rate_limit(state_file: str) -> bool:
    """Check if we're within rate limits.

    Args:
        state_file: Path to timestamp state file for this agent

    Returns:
        True if we can proceed, False if rate limit exceeded
    """
    try:
        if not os.path.exists(state_file):
            return True

        # Read execution timestamps from last hour
        with open(state_file, 'r') as f:
            lines = f.readlines()

        now = time.time()
        one_hour_ago = now - 3600

        # Count recent executions
        recent_count = sum(
            1 for line in lines
            if line.strip() and float(line.strip()) > one_hour_ago
        )

        if recent_count >= MAX_HOURLY_EXECUTIONS:
            log(f"Rate limit exceeded: {recent_count} executions in last hour")
            return False

        return True
    except Exception as e:
        log(f"Error checking rate limit: {e}")
        return True  # Fail open


def record_execution(state_file: str):
    """Record execution timestamp for rate limiting."""
    try:
        now = time.time()
        one_hour_ago = now - 3600

        # Read existing timestamps
        timestamps = []
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                timestamps = [
                    float(line.strip())
                    for line in f.readlines()
                    if line.strip() and float(line.strip()) > one_hour_ago
                ]

        # Add current timestamp
        timestamps.append(now)

        # Write back
        with open(state_file, 'w') as f:
            for ts in timestamps:
                f.write(f"{ts}\n")
    except Exception as e:
        log(f"Error recording execution: {e}")


def extract_prompt(subject: str, body: str, trigger_word: str) -> Optional[str]:
    """Extract prompt from email subject or body.

    Args:
        subject: Email subject line
        body: Email body text
        trigger_word: Agent trigger word expected at the start of the subject

    Returns:
        Extracted prompt or None if not found
    """
    escaped_trigger = re.escape(trigger_word)

    # Try to extract from subject first - "<Agent> <prompt>"
    match = re.match(rf"^{escaped_trigger}\s+(.+)", subject, re.IGNORECASE)
    if match:
        prompt = match.group(1).strip()
        if prompt:
            return prompt

    # If subject is just the agent name with no text, use body
    if re.match(rf"^{escaped_trigger}\s*$", subject, re.IGNORECASE):
        body = body.strip()
        if body:
            return body

    return None


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


def expand_codex_prompt(prompt: str) -> Tuple[str, str]:
    """Expand Codex shortcut prompts into the full prompt."""
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


def prepare_agent_prompt(prompt: str, agent_config: dict) -> Tuple[str, str]:
    """Expand agent-specific shortcuts before execution."""
    if agent_config.get("cli_name") == "codex":
        return expand_codex_prompt(prompt)
    return prompt, "generic prompt"


def get_agent_config_for_subject(subject: str, agent_configs: List[dict]) -> Optional[dict]:
    """Return the agent config for a subject with a supported trigger prefix."""
    for agent_config in agent_configs:
        escaped_trigger = re.escape(agent_config["trigger_word"])
        if re.match(rf"^{escaped_trigger}(\s+|$)", subject, re.IGNORECASE):
            return agent_config
    return None


def normalize_email_address(value: str) -> str:
    """Extract and normalize an email address from a header or config value."""
    parsed_email = parseaddr(value or "")[1]
    return (parsed_email or value or "").strip().lower()


def sender_is_allowed(from_addr: str, agent_config: dict) -> bool:
    """Check whether the sender is allowlisted for this specific agent."""
    sender = normalize_email_address(from_addr)
    allowed_senders = {
        normalize_email_address(email)
        for email in agent_config.get("sender_emails", [])
    }
    return sender in allowed_senders


def execute_agent(
    prompt: str,
    working_dir: str,
    agent_config: dict,
    mark_codex_unread: bool = True,
) -> Tuple[bool, str, float, dict]:
    """Execute the configured agent CLI with the given prompt.

    Args:
        prompt: The prompt to execute
        working_dir: Working directory for agent CLI
        agent_config: Agent configuration

    Returns:
        Tuple of (success, output, duration_seconds, execution_metadata)
    """
    start_time = time.time()
    display_name = agent_config["display_name"]

    if agent_config.get("use_codex_app_runner"):
        log(f"Executing {display_name} with Desktop-visible app-server runner: {prompt[:100]}...")
        result: CodexRunResult = execute_codex_with_fallback(
            prompt=prompt,
            working_dir=working_dir,
            timeout=EXECUTION_TIMEOUT,
            mark_unread=mark_codex_unread,
        )
        if result.thread_id:
            log(f"{display_name} runner: {result.runner}; thread id: {result.thread_id}")
        else:
            log(f"{display_name} runner: {result.runner}")

        if result.success:
            log(f"{display_name} executed successfully in {result.duration:.1f}s")
        else:
            log(f"{display_name} failed via {result.runner}")

        return (
            result.success,
            result.output,
            result.duration,
            {
                "runner": result.runner,
                "thread_id": result.thread_id,
                "exit_code": result.exit_code,
                "app_server_error": result.app_server_error,
            },
        )

    try:
        log(f"Executing {display_name} with prompt: {prompt[:100]}...")
        command = agent_config["command_builder"](prompt, working_dir)

        result = subprocess.run(
            command,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            log(f"{display_name} executed successfully in {duration:.1f}s")
            return True, result.stdout, duration, {
                "runner": "subprocess",
                "thread_id": None,
                "exit_code": result.returncode,
            }
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            log(f"{display_name} failed with exit code {result.returncode}")
            return False, error_msg, duration, {
                "runner": "subprocess",
                "thread_id": None,
                "exit_code": result.returncode,
            }

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        log(f"{display_name} timed out after {duration:.1f}s")
        return False, f"Execution timed out after {EXECUTION_TIMEOUT} seconds", duration, {
            "runner": "subprocess",
            "thread_id": None,
            "exit_code": None,
        }

    except FileNotFoundError:
        duration = time.time() - start_time
        cli_name = agent_config["cli_name"]
        log(f"Error: {cli_name} command not found")
        return False, f"{display_name} CLI not found in PATH ({cli_name})", duration, {
            "runner": "subprocess",
            "thread_id": None,
            "exit_code": None,
        }

    except Exception as e:
        duration = time.time() - start_time
        log(f"Error executing {display_name}: {e}")
        return False, str(e), duration, {
            "runner": "subprocess",
            "thread_id": None,
            "exit_code": None,
        }


def format_reply(
    success: bool,
    output: str,
    duration: float,
    prompt: str,
    working_dir: str,
    agent_config: dict,
    execution_metadata: Optional[dict] = None,
) -> str:
    """Format reply email body.

    Args:
        success: Whether execution succeeded
        output: Agent CLI output or error message
        duration: Execution duration in seconds
        prompt: The original prompt
        working_dir: Working directory used
        agent_config: Agent configuration

    Returns:
        Formatted reply body
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    display_name = agent_config["display_name"]
    execution_metadata = execution_metadata or {}
    runner = execution_metadata.get("runner") or "unknown"
    thread_id = execution_metadata.get("thread_id")
    exit_code = execution_metadata.get("exit_code")
    exit_code_text = str(exit_code) if exit_code is not None else "n/a"
    thread_line = f"Codex Thread ID: {thread_id}\n" if thread_id else ""

    if success:
        return f"""✅ {display_name} executed at: {timestamp}

=== Results ===
{output}

=== Execution Details ===
Agent: {display_name}
Runner: {runner}
{thread_line}Duration: {duration:.1f}s
Working Directory: {working_dir}
Exit Code: {exit_code_text}
"""
    else:
        log_file = agent_config["log_file"]
        return f"""❌ {display_name} execution failed at: {timestamp}

Error: {output}

Prompt attempted: {prompt}

Check {log_file} for details.

=== Execution Details ===
Agent: {display_name}
Runner: {runner}
{thread_line}Duration: {duration:.1f}s
Working Directory: {working_dir}
Exit Code: {exit_code_text}
"""


def process_trigger_email(
    client: GmailClient,
    message: dict,
    working_dir: str,
    active_agent_configs: List[dict],
    mark_codex_unread: bool = True,
) -> bool:
    """Process a single trigger email.

    Args:
        client: Gmail client instance
        message: Email message dict
        working_dir: Working directory for agent CLI
        active_agent_configs: Agent configurations enabled for this run

    Returns:
        True if processed successfully, False otherwise
    """
    message_id = message.get("id")
    thread_id = message.get("threadId")

    try:
        # Get full message details
        full_message = client.get_message(message_id)
        headers = client.get_message_headers(full_message)
        body = client.get_message_body(full_message)

        subject = headers.get("subject", "")
        from_addr = headers.get("from", "")

        log(f"Processing email: {subject}")
        log(f"From: {from_addr}")

        agent_config = get_agent_config_for_subject(subject, active_agent_configs)
        if not agent_config:
            log("Skipping email because subject does not start with an active trigger prefix")
            return False

        if not sender_is_allowed(from_addr, agent_config):
            log(f"Sender is not allowlisted for {agent_config['display_name']}; marking email as read")
            client.modify_labels(message_id, remove_labels=["UNREAD"])
            return False

        if not check_rate_limit(agent_config["state_file"]):
            log(f"Rate limit exceeded for {agent_config['display_name']}, leaving email unread")
            return False

        # Extract prompt
        prompt = extract_prompt(subject, body, agent_config["trigger_word"])
        if not prompt:
            log("Warning: Could not extract prompt from email")
            # Mark as read anyway to avoid reprocessing
            client.modify_labels(message_id, remove_labels=["UNREAD"])
            return False

        log(f"Extracted prompt: {prompt[:100]}...")

        execution_prompt, prompt_kind = prepare_agent_prompt(prompt, agent_config)
        if execution_prompt != prompt:
            log(f"Expanded Codex prompt using {prompt_kind}")

        # Mark as read immediately to prevent reprocessing
        # (even if agent execution or reply fails)
        log("Marking email as read...")
        client.modify_labels(message_id, remove_labels=["UNREAD"])

        # Record execution for rate limiting
        record_execution(agent_config["state_file"])

        # Execute agent CLI
        success, output, duration, execution_metadata = execute_agent(
            execution_prompt,
            working_dir,
            agent_config,
            mark_codex_unread=mark_codex_unread,
        )

        # Format reply
        reply_body = format_reply(
            success,
            output,
            duration,
            execution_prompt,
            working_dir,
            agent_config,
            execution_metadata,
        )
        reply_subject = f"Re: {subject}"

        # Get Message-ID for threading
        message_id_header = headers.get("message-id", "")

        # Send reply
        log("Sending reply email...")
        client.send_message(
            to=from_addr,
            subject=reply_subject,
            body=reply_body,
            thread_id=thread_id,
            in_reply_to=message_id_header,
            references=message_id_header
        )

        log(f"✅ Successfully processed email {message_id}")
        return True

    except Exception as e:
        log(f"❌ Error processing email {message_id}: {e}")

        # Try to send error reply
        try:
            error_body = f"""❌ Processing failed at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Error: {str(e)}

The trigger email could not be processed. Please check the logs.
"""
            client.send_message(
                to=from_addr,
                subject=f"Re: {subject}",
                body=error_body,
                thread_id=thread_id
            )

            # Mark as read to avoid reprocessing
            client.modify_labels(message_id, remove_labels=["UNREAD"])
        except Exception as send_error:
            log(f"Failed to send error reply: {send_error}")

        return False


def load_active_agent_configs() -> List[dict]:
    """Load sender allowlists for all configured agents."""
    active_agent_configs = []

    for agent_config in AGENT_CONFIGS.values():
        display_name = agent_config["display_name"]
        try:
            trigger_config = config.get_email_trigger_config(
                env_var=agent_config["emails_env_var"],
                display_name=display_name,
                fallback_env_var=agent_config["fallback_emails_env_var"],
            )
        except ValueError as e:
            log(f"Configuration warning for {display_name}: {e}")
            continue

        active_agent_config = dict(agent_config)
        active_agent_config["sender_emails"] = trigger_config["sender_emails"]
        active_agent_config["sender_source_env_var"] = trigger_config["source_env_var"]
        active_agent_configs.append(active_agent_config)

    return active_agent_configs


def message_internal_date(message: dict) -> int:
    """Return Gmail internalDate as an integer timestamp in milliseconds."""
    try:
        return int(message.get("internalDate", 0))
    except (TypeError, ValueError):
        return 0


def search_all_messages(client: GmailClient, query: str) -> List[dict]:
    """Search Gmail for all messages matching a query."""
    messages = []
    next_page_token = None

    while True:
        params = {
            "q": query,
            "maxResults": SEARCH_PAGE_SIZE,
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        result = client._request("GET", "/users/me/messages", params=params)
        page_messages = result.get("messages", [])

        for message in page_messages:
            try:
                messages.append(client.get_message(message["id"]))
            except Exception:
                messages.append(message)

        next_page_token = result.get("nextPageToken")
        if not next_page_token:
            break

    return messages


def search_trigger_messages(
    client: GmailClient,
    active_agent_configs: List[dict],
    max_emails: int
) -> List[dict]:
    """Search once for unread trigger messages for every active agent."""
    messages_by_id: Dict[str, dict] = {}
    searchable_agent_configs = []

    for agent_config in active_agent_configs:
        display_name = agent_config["display_name"]
        if not check_rate_limit(agent_config["state_file"]):
            log(f"Rate limit exceeded for {display_name}, skipping search")
            continue
        searchable_agent_configs.append(agent_config)

    if not searchable_agent_configs:
        return []

    sender_emails = []
    seen_senders = set()
    for agent_config in searchable_agent_configs:
        for email in agent_config["sender_emails"]:
            normalized_email = normalize_email_address(email)
            if normalized_email not in seen_senders:
                sender_emails.append(email)
                seen_senders.add(normalized_email)

    trigger_words = [
        agent_config["trigger_word"]
        for agent_config in searchable_agent_configs
    ]

    from_query = " OR ".join([f"from:{email}" for email in sender_emails])
    subject_query = " OR ".join([f"subject:{trigger_word}" for trigger_word in trigger_words])
    query = f"is:unread ({from_query}) ({subject_query})"
    log(f"Searching for trigger emails: {query}")

    messages = search_all_messages(client, query)
    log(f"Found {len(messages)} possible trigger email(s)")

    for message in messages:
        headers = client.get_message_headers(message) if "payload" in message else {}
        subject = headers.get("subject", "")
        if subject and not get_agent_config_for_subject(subject, searchable_agent_configs):
            log(f"Skipping possible trigger result without trigger prefix: {subject}")
            continue

        message_id = message.get("id")
        if message_id and message_id not in messages_by_id:
            messages_by_id[message_id] = message

    trigger_messages = sorted(messages_by_id.values(), key=message_internal_date)

    if len(trigger_messages) > max_emails:
        log(f"Processing oldest {max_emails} of {len(trigger_messages)} trigger email(s)")

    return trigger_messages[:max_emails]


def main(argv: Optional[List[str]] = None):
    """Main entry point."""
    args = parse_args(argv)
    log("=== Email Trigger Watcher Starting ===")
    log(f"Max emails to process this run: {args.max_emails}")
    log(f"Mark Codex Desktop sessions unread: {args.mark_codex_unread}")

    # Load configuration
    try:
        google_config = config.get_google_config()
    except ValueError as e:
        log(f"Configuration error: {e}")
        sys.exit(1)

    active_agent_configs = load_active_agent_configs()
    if not active_agent_configs:
        log("Configuration error: no active email trigger configurations found")
        sys.exit(1)

    # Create Gmail client
    client = GmailClient(
        client_id=google_config["client_id"],
        client_secret=google_config["client_secret"],
        refresh_token=google_config["refresh_token"]
    )

    try:
        messages = search_trigger_messages(client, active_agent_configs, args.max_emails)
        log(f"Found {len(messages)} trigger email(s)")

        if not messages:
            log("No trigger emails found")
            return

        # Get working directory
        working_dir = str(Path(__file__).parent.parent)
        log(f"Working directory: {working_dir}")

        # Process each message
        processed_count = 0
        for i, message in enumerate(messages, 1):
            log(f"\n--- Processing email {i}/{len(messages)} ---")
            if process_trigger_email(
                client,
                message,
                working_dir,
                active_agent_configs,
                mark_codex_unread=args.mark_codex_unread,
            ):
                processed_count += 1

        log(f"\n=== Completed: {processed_count}/{len(messages)} emails processed successfully ===")

    except Exception as e:
        log(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
