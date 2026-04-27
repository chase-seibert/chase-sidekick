#!/usr/bin/env python3
"""Email trigger watcher - monitors Gmail for agent emails and executes prompts.

This script polls Gmail for unread emails with an agent name as the first word
in the subject, executes the prompt using that agent's CLI, and replies with
the results.

Usage:
    python3 tools/email_trigger_watcher.py

Expected email format:
    Subject: Claude <your prompt here>
    OR
    Subject: Claude
    Body: <your prompt here>

    Subject: Codex <your prompt here>
    OR
    Subject: Codex
    Body: <your prompt here>

The script will:
1. Search for unread emails from allowed senders with the agent name as first word
2. Extract the prompt from subject or body
3. Execute the configured agent CLI command
4. Reply to the email with results
5. Mark the email as read
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from email.utils import parseaddr
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidekick import config
from sidekick.clients.gmail import GmailClient

# Configuration
MAX_PROMPTS_PER_RUN = 5  # Process max 5 emails per run
EXECUTION_TIMEOUT = 300  # 5 minutes timeout for agent execution
MAX_HOURLY_EXECUTIONS = 20  # Rate limit


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
    },
}


def log(message: str):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


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


def execute_agent(prompt: str, working_dir: str, agent_config: dict) -> Tuple[bool, str, float]:
    """Execute the configured agent CLI with the given prompt.

    Args:
        prompt: The prompt to execute
        working_dir: Working directory for agent CLI
        agent_config: Agent configuration

    Returns:
        Tuple of (success, output, duration_seconds)
    """
    start_time = time.time()
    display_name = agent_config["display_name"]

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
            return True, result.stdout, duration
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            log(f"{display_name} failed with exit code {result.returncode}")
            return False, error_msg, duration

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        log(f"{display_name} timed out after {duration:.1f}s")
        return False, f"Execution timed out after {EXECUTION_TIMEOUT} seconds", duration

    except FileNotFoundError:
        duration = time.time() - start_time
        cli_name = agent_config["cli_name"]
        log(f"Error: {cli_name} command not found")
        return False, f"{display_name} CLI not found in PATH ({cli_name})", duration

    except Exception as e:
        duration = time.time() - start_time
        log(f"Error executing {display_name}: {e}")
        return False, str(e), duration


def format_reply(
    success: bool,
    output: str,
    duration: float,
    prompt: str,
    working_dir: str,
    agent_config: dict
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

    if success:
        return f"""✅ {display_name} executed at: {timestamp}

=== Results ===
{output}

=== Execution Details ===
Agent: {display_name}
Duration: {duration:.1f}s
Working Directory: {working_dir}
Exit Code: 0
"""
    else:
        log_file = agent_config["log_file"]
        return f"""❌ {display_name} execution failed at: {timestamp}

Error: {output}

Prompt attempted: {prompt}

Check {log_file} for details.

=== Execution Details ===
Agent: {display_name}
Duration: {duration:.1f}s
Working Directory: {working_dir}
"""


def process_trigger_email(
    client: GmailClient,
    message: dict,
    working_dir: str,
    active_agent_configs: List[dict]
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

        # Mark as read immediately to prevent reprocessing
        # (even if agent execution or reply fails)
        log("Marking email as read...")
        client.modify_labels(message_id, remove_labels=["UNREAD"])

        # Record execution for rate limiting
        record_execution(agent_config["state_file"])

        # Execute agent CLI
        success, output, duration = execute_agent(prompt, working_dir, agent_config)

        # Format reply
        reply_body = format_reply(success, output, duration, prompt, working_dir, agent_config)
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


def search_trigger_messages(client: GmailClient, active_agent_configs: List[dict]) -> List[dict]:
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

    messages = client.search_messages(query, max_results=MAX_PROMPTS_PER_RUN)
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

    return list(messages_by_id.values())


def main():
    """Main entry point."""
    log("=== Email Trigger Watcher Starting ===")

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
        messages = search_trigger_messages(client, active_agent_configs)
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
            if process_trigger_email(client, message, working_dir, active_agent_configs):
                processed_count += 1

        log(f"\n=== Completed: {processed_count}/{len(messages)} emails processed successfully ===")

    except Exception as e:
        log(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
