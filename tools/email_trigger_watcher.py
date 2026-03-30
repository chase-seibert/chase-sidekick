#!/usr/bin/env python3
"""Email trigger watcher - monitors Gmail for Claude emails and executes prompts.

This script polls Gmail for unread emails with "Claude" as the first word in the subject,
executes the prompt using Claude Code, and replies with the results.

Usage:
    python3 tools/email_trigger_watcher.py

Expected email format:
    Subject: Claude <your prompt here>
    OR
    Subject: Claude
    Body: <your prompt here>

The script will:
1. Search for unread emails from allowed senders with "Claude" as first word
2. Extract the prompt from subject or body
3. Execute: claude --print "<prompt>" --output-format text
4. Reply to the email with results
5. Mark the email as read and add "PROCESSED" label
"""
import sys
import os
import re
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidekick import config
from sidekick.clients.gmail import GmailClient

# Configuration
TRIGGER_PATTERN = r"^Claude\s+"
MAX_PROMPTS_PER_RUN = 5  # Process max 5 emails per run
CLAUDE_TIMEOUT = 300  # 5 minutes timeout for Claude execution
MAX_HOURLY_EXECUTIONS = 20  # Rate limit

# State tracking file
STATE_FILE = "/tmp/claude_trigger_state.txt"


def log(message: str):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def check_rate_limit() -> bool:
    """Check if we're within rate limits.

    Returns:
        True if we can proceed, False if rate limit exceeded
    """
    try:
        if not os.path.exists(STATE_FILE):
            return True

        # Read execution timestamps from last hour
        with open(STATE_FILE, 'r') as f:
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


def record_execution():
    """Record execution timestamp for rate limiting."""
    try:
        now = time.time()
        one_hour_ago = now - 3600

        # Read existing timestamps
        timestamps = []
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                timestamps = [
                    float(line.strip())
                    for line in f.readlines()
                    if line.strip() and float(line.strip()) > one_hour_ago
                ]

        # Add current timestamp
        timestamps.append(now)

        # Write back
        with open(STATE_FILE, 'w') as f:
            for ts in timestamps:
                f.write(f"{ts}\n")
    except Exception as e:
        log(f"Error recording execution: {e}")


def extract_prompt(subject: str, body: str) -> Optional[str]:
    """Extract prompt from email subject or body.

    Args:
        subject: Email subject line
        body: Email body text

    Returns:
        Extracted prompt or None if not found
    """
    # Try to extract from subject first - "Claude <prompt>"
    match = re.match(r'^Claude\s+(.+)', subject, re.IGNORECASE)
    if match:
        prompt = match.group(1).strip()
        if prompt:
            return prompt

    # If subject is just "Claude" with no text, use body
    if re.match(r'^Claude\s*$', subject, re.IGNORECASE):
        body = body.strip()
        if body:
            return body

    return None


def execute_claude(prompt: str, working_dir: str) -> Tuple[bool, str, float]:
    """Execute Claude Code with the given prompt.

    Args:
        prompt: The prompt to execute
        working_dir: Working directory for Claude Code

    Returns:
        Tuple of (success, output, duration_seconds)
    """
    start_time = time.time()

    try:
        log(f"Executing Claude Code with prompt: {prompt[:100]}...")

        result = subprocess.run(
            ["claude", "--print", prompt, "--output-format", "text"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            log(f"Claude Code executed successfully in {duration:.1f}s")
            return True, result.stdout, duration
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            log(f"Claude Code failed with exit code {result.returncode}")
            return False, error_msg, duration

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        log(f"Claude Code timed out after {duration:.1f}s")
        return False, f"Execution timed out after {CLAUDE_TIMEOUT} seconds", duration

    except FileNotFoundError:
        duration = time.time() - start_time
        log("Error: claude command not found")
        return False, "Claude Code CLI not found in PATH", duration

    except Exception as e:
        duration = time.time() - start_time
        log(f"Error executing Claude Code: {e}")
        return False, str(e), duration


def format_reply(success: bool, output: str, duration: float, prompt: str, working_dir: str) -> str:
    """Format reply email body.

    Args:
        success: Whether execution succeeded
        output: Claude Code output or error message
        duration: Execution duration in seconds
        prompt: The original prompt
        working_dir: Working directory used

    Returns:
        Formatted reply body
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if success:
        return f"""✅ Executed at: {timestamp}

=== Results ===
{output}

=== Execution Details ===
Duration: {duration:.1f}s
Working Directory: {working_dir}
Exit Code: 0
"""
    else:
        return f"""❌ Execution failed at: {timestamp}

Error: {output}

Prompt attempted: {prompt}

Check /tmp/claude_trigger.log for details.

=== Execution Details ===
Duration: {duration:.1f}s
Working Directory: {working_dir}
"""


def process_trigger_email(client: GmailClient, message: dict, working_dir: str) -> bool:
    """Process a single trigger email.

    Args:
        client: Gmail client instance
        message: Email message dict
        working_dir: Working directory for Claude Code

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

        # Extract prompt
        prompt = extract_prompt(subject, body)
        if not prompt:
            log("Warning: Could not extract prompt from email")
            # Mark as read anyway to avoid reprocessing
            client.modify_labels(message_id, remove_labels=["UNREAD"])
            return False

        log(f"Extracted prompt: {prompt[:100]}...")

        # Record execution for rate limiting
        record_execution()

        # Execute Claude Code
        success, output, duration = execute_claude(prompt, working_dir)

        # Format reply
        reply_body = format_reply(success, output, duration, prompt, working_dir)
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

        # Mark as read
        log("Marking email as read...")
        client.modify_labels(message_id, remove_labels=["UNREAD"])

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


def main():
    """Main entry point."""
    log("=== Email Trigger Watcher Starting ===")

    # Check rate limit
    if not check_rate_limit():
        log("Rate limit exceeded, skipping this run")
        return

    # Load configuration
    try:
        google_config = config.get_google_config()
        trigger_config = config.get_claude_trigger_config()
        sender_emails = trigger_config["sender_emails"]
    except ValueError as e:
        log(f"Configuration error: {e}")
        sys.exit(1)

    # Create Gmail client
    client = GmailClient(
        client_id=google_config["client_id"],
        client_secret=google_config["client_secret"],
        refresh_token=google_config["refresh_token"]
    )

    # Search for trigger emails from any allowed sender
    from_query = " OR ".join([f"from:{email}" for email in sender_emails])
    query = f"is:unread ({from_query}) subject:Claude"
    log(f"Searching for emails: {query}")

    try:
        messages = client.search_messages(query, max_results=MAX_PROMPTS_PER_RUN)
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
            if process_trigger_email(client, message, working_dir):
                processed_count += 1

        log(f"\n=== Completed: {processed_count}/{len(messages)} emails processed successfully ===")

    except Exception as e:
        log(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
