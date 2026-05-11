#!/usr/bin/env python3
"""Run Codex through app-server so trigger sessions show in Desktop.

The public helper in this file first tries a headless app-server session. If
that path fails before a turn starts, it falls back to the existing
non-interactive `codex exec` path so scheduled triggers can still complete.
"""
import argparse
import json
import selectors
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_TIMEOUT = 1800
STDERR_LIMIT = 40

UNATTENDED_TRIGGER_INSTRUCTIONS = """This request was launched by an unattended trigger.

Complete it to the best of your ability without asking follow-up questions,
requesting confirmation, or waiting for interactive input. If you are blocked,
report the blocker clearly in your final response.

Original trigger prompt:
"""


@dataclass
class CodexRunResult:
    """Result from either app-server or exec fallback execution."""

    success: bool
    output: str
    duration: float
    exit_code: Optional[int]
    runner: str
    thread_id: Optional[str] = None
    app_server_error: Optional[str] = None


class AppServerError(Exception):
    """Base class for app-server runner failures."""


class AppServerUnavailable(AppServerError):
    """Raised when app-server fails before the Codex turn starts."""


class AppServerTurnStartedError(AppServerError):
    """Raised after turn/start has been sent; callers should not retry."""


class _CodexAppServerClient:
    """Minimal JSON-RPC client for `codex app-server --listen stdio://`."""

    def __init__(self, codex_bin: str = "codex") -> None:
        self.codex_bin = codex_bin
        self.process: Optional[subprocess.Popen[str]] = None
        self.selector: Optional[selectors.BaseSelector] = None
        self.next_id = 1
        self.stderr_lines: List[str] = []
        self.agent_deltas: List[str] = []
        self.completed_turns: Dict[str, dict] = {}

    def start(self) -> None:
        try:
            self.process = subprocess.Popen(
                [self.codex_bin, "app-server", "--listen", "stdio://"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as e:
            raise AppServerUnavailable(f"Codex CLI not found: {self.codex_bin}") from e
        except Exception as e:
            raise AppServerUnavailable(f"Could not start codex app-server: {e}") from e

        if not self.process.stdin or not self.process.stdout or not self.process.stderr:
            raise AppServerUnavailable("codex app-server did not expose stdio pipes")

        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ, "stdout")
        self.selector.register(self.process.stderr, selectors.EVENT_READ, "stderr")

    def close(self) -> None:
        if self.selector:
            self.selector.close()
            self.selector = None

        if not self.process:
            return

        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

    def request(self, method: str, params: dict, timeout: float) -> dict:
        request_id = self._send_request(method, params)
        deadline = time.monotonic() + timeout

        while True:
            message = self._read_message(deadline)
            self._handle_notification(message)

            if message.get("id") != request_id:
                continue

            if "error" in message:
                error = message["error"]
                if isinstance(error, dict):
                    error_message = error.get("message") or json.dumps(error)
                else:
                    error_message = str(error)
                raise AppServerError(f"{method} failed: {error_message}")

            result = message.get("result")
            if isinstance(result, dict):
                return result
            return {}

    def wait_for_turn_completed(self, thread_id: str, timeout: float) -> dict:
        if thread_id in self.completed_turns:
            return self.completed_turns[thread_id]

        deadline = time.monotonic() + timeout
        while True:
            message = self._read_message(deadline)
            self._handle_notification(message)
            if thread_id in self.completed_turns:
                return self.completed_turns[thread_id]

    def _send_request(self, method: str, params: dict) -> int:
        if not self.process or not self.process.stdin:
            raise AppServerUnavailable("codex app-server is not running")

        request_id = self.next_id
        self.next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        try:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except BrokenPipeError as e:
            raise AppServerUnavailable(
                f"codex app-server pipe closed before {method}: {self.stderr_summary()}"
            ) from e

        return request_id

    def _read_message(self, deadline: float) -> dict:
        if not self.process or not self.selector:
            raise AppServerUnavailable("codex app-server is not running")

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AppServerError(f"timed out waiting for codex app-server: {self.stderr_summary()}")

            if self.process.poll() is not None:
                raise AppServerUnavailable(
                    f"codex app-server exited with code {self.process.returncode}: "
                    f"{self.stderr_summary()}"
                )

            events = self.selector.select(timeout=min(0.25, remaining))
            if not events:
                continue

            for key, _ in events:
                stream_name = key.data
                line = key.fileobj.readline()
                if not line:
                    try:
                        self.selector.unregister(key.fileobj)
                    except Exception:
                        pass
                    continue

                if stream_name == "stderr":
                    self._remember_stderr(line)
                    continue

                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    self._remember_stderr(f"Non-JSON stdout from app-server: {line}")

    def _handle_notification(self, message: dict) -> None:
        method = message.get("method")
        params = message.get("params") or {}

        if method == "item/agentMessage/delta":
            delta = params.get("delta")
            if delta:
                self.agent_deltas.append(str(delta))
            return

        if method == "turn/completed":
            thread_id = params.get("threadId")
            if thread_id:
                self.completed_turns[str(thread_id)] = params

    def _remember_stderr(self, line: str) -> None:
        line = line.rstrip()
        if not line:
            return
        self.stderr_lines.append(line)
        if len(self.stderr_lines) > STDERR_LIMIT:
            self.stderr_lines = self.stderr_lines[-STDERR_LIMIT:]

    def stderr_summary(self) -> str:
        if not self.stderr_lines:
            return "no stderr output"
        return "\n".join(self.stderr_lines[-10:])


def wrap_unattended_prompt(prompt: str) -> str:
    """Add unattended trigger instructions to the user's prompt."""
    return UNATTENDED_TRIGGER_INSTRUCTIONS + prompt.strip()


def build_thread_name(prompt: str) -> str:
    """Build a short Desktop-visible thread name from the trigger prompt."""
    first_line = next((line.strip() for line in prompt.splitlines() if line.strip()), "")
    if not first_line:
        return "Codex trigger"

    if len(first_line) > 72:
        first_line = first_line[:69].rstrip() + "..."

    return f"Trigger: {first_line}"


def build_codex_exec_command(
    prompt: str,
    working_dir: str,
    codex_bin: str = "codex",
) -> List[str]:
    """Build the fallback `codex exec` command."""
    return [
        codex_bin,
        "--ask-for-approval",
        "never",
        "exec",
        "--cd",
        working_dir,
        "--sandbox",
        "workspace-write",
        prompt,
    ]


def run_codex_exec(
    prompt: str,
    working_dir: str,
    timeout: float = DEFAULT_TIMEOUT,
    codex_bin: str = "codex",
    runner: str = "exec fallback",
) -> CodexRunResult:
    """Run Codex using the existing non-interactive exec path."""
    start_time = time.time()

    try:
        result = subprocess.run(
            build_codex_exec_command(prompt, working_dir, codex_bin=codex_bin),
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - start_time
        output = result.stdout if result.returncode == 0 else (result.stderr or result.stdout)
        return CodexRunResult(
            success=result.returncode == 0,
            output=output or "",
            duration=duration,
            exit_code=result.returncode,
            runner=runner,
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return CodexRunResult(
            success=False,
            output=f"Execution timed out after {timeout:.0f} seconds",
            duration=duration,
            exit_code=None,
            runner=runner,
        )
    except FileNotFoundError:
        duration = time.time() - start_time
        return CodexRunResult(
            success=False,
            output=f"Codex CLI not found in PATH ({codex_bin})",
            duration=duration,
            exit_code=None,
            runner=runner,
        )
    except Exception as e:
        duration = time.time() - start_time
        return CodexRunResult(
            success=False,
            output=str(e),
            duration=duration,
            exit_code=None,
            runner=runner,
        )


def run_codex_app_server(
    prompt: str,
    working_dir: str,
    timeout: float = DEFAULT_TIMEOUT,
    codex_bin: str = "codex",
    thread_name: Optional[str] = None,
) -> CodexRunResult:
    """Run Codex through a headless app-server session."""
    start_time = time.time()
    client = _CodexAppServerClient(codex_bin=codex_bin)
    thread_id: Optional[str] = None
    turn_started = False

    try:
        client.start()
        client.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "sidekick-trigger",
                    "title": "Sidekick Trigger",
                    "version": "1",
                },
                "capabilities": {"experimentalApi": True},
            },
            timeout=30,
        )

        thread_response = client.request(
            "thread/start",
            {
                "approvalPolicy": "never",
                "cwd": working_dir,
                "ephemeral": False,
                "persistExtendedHistory": True,
                "sandbox": "workspace-write",
                "serviceName": "sidekick-trigger",
            },
            timeout=30,
        )
        thread = thread_response.get("thread") or {}
        thread_id = thread.get("id")
        if not thread_id:
            raise AppServerUnavailable("thread/start did not return a thread id")

        if thread_name:
            try:
                client.request(
                    "thread/name/set",
                    {"threadId": thread_id, "name": thread_name},
                    timeout=10,
                )
            except AppServerError:
                pass

        turn_started = True
        client.request(
            "turn/start",
            {
                "threadId": thread_id,
                "approvalPolicy": "never",
                "cwd": working_dir,
                "input": [{"type": "text", "text": wrap_unattended_prompt(prompt)}],
            },
            timeout=30,
        )

        completed = client.wait_for_turn_completed(thread_id, timeout=timeout)
        turn = completed.get("turn") or {}
        status = turn.get("status")
        success = status == "completed"

        output = _read_final_thread_output(client, thread_id) or "".join(client.agent_deltas).strip()
        if not success and not output:
            error = turn.get("error") or {}
            output = error.get("message") or f"Codex turn ended with status: {status or 'unknown'}"

        return CodexRunResult(
            success=success,
            output=output,
            duration=time.time() - start_time,
            exit_code=0 if success else None,
            runner="app-server",
            thread_id=thread_id,
        )
    except AppServerError as e:
        if turn_started:
            raise AppServerTurnStartedError(str(e)) from e
        raise AppServerUnavailable(str(e)) from e
    finally:
        client.close()


def execute_codex_with_fallback(
    prompt: str,
    working_dir: str,
    timeout: float = DEFAULT_TIMEOUT,
    codex_bin: str = "codex",
    thread_name: Optional[str] = None,
) -> CodexRunResult:
    """Run app-server first, then exec fallback if no turn was started."""
    start_time = time.time()

    try:
        return run_codex_app_server(
            prompt=prompt,
            working_dir=working_dir,
            timeout=timeout,
            codex_bin=codex_bin,
            thread_name=thread_name or build_thread_name(prompt),
        )
    except AppServerUnavailable as e:
        app_server_error = str(e)
        fallback = run_codex_exec(
            prompt=wrap_unattended_prompt(prompt),
            working_dir=working_dir,
            timeout=timeout,
            codex_bin=codex_bin,
            runner="exec fallback",
        )
        fallback.duration = time.time() - start_time
        fallback.app_server_error = app_server_error
        fallback.output = _format_fallback_output(app_server_error, fallback.output)
        return fallback
    except AppServerTurnStartedError as e:
        return CodexRunResult(
            success=False,
            output=(
                "Codex app-server failed after the turn started, so exec fallback was "
                f"not attempted to avoid duplicate side effects.\n\nApp-server error:\n{e}"
            ),
            duration=time.time() - start_time,
            exit_code=None,
            runner="app-server",
        )


def _read_final_thread_output(client: _CodexAppServerClient, thread_id: str) -> str:
    try:
        response = client.request(
            "thread/read",
            {"threadId": thread_id, "includeTurns": True},
            timeout=10,
        )
    except AppServerError:
        return ""

    thread = response.get("thread") or {}
    final_messages: List[str] = []
    agent_messages: List[str] = []

    for turn in thread.get("turns") or []:
        for item in turn.get("items") or []:
            if item.get("type") != "agentMessage":
                continue
            text = (item.get("text") or "").strip()
            if not text:
                continue
            if item.get("phase") == "final_answer":
                final_messages.append(text)
            else:
                agent_messages.append(text)

    return "\n\n".join(final_messages or agent_messages).strip()


def _format_fallback_output(app_server_error: str, fallback_output: str) -> str:
    fallback_output = fallback_output.strip() or "(no fallback output)"
    return f"""App-server runner failed before the Codex turn started; used exec fallback.

Fallback runs do not create Codex Desktop sessions.

App-server error:
{app_server_error}

Fallback output:
{fallback_output}
"""


def positive_float(value: str) -> float:
    """Parse a positive float argument."""
    try:
        parsed = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number")
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for manual smoke testing."""
    parser = argparse.ArgumentParser(description="Run a Codex trigger through app-server.")
    parser.add_argument("prompt", help="Prompt to send to Codex")
    parser.add_argument(
        "--cd",
        default=str(Path.cwd()),
        help="Working directory for Codex (default: current directory).",
    )
    parser.add_argument(
        "--timeout",
        type=positive_float,
        default=DEFAULT_TIMEOUT,
        help=f"Execution timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    args = parser.parse_args(argv)

    result = execute_codex_with_fallback(
        prompt=args.prompt,
        working_dir=args.cd,
        timeout=args.timeout,
    )
    print(f"Runner: {result.runner}")
    if result.thread_id:
        print(f"Thread ID: {result.thread_id}")
    if result.exit_code is not None:
        print(f"Exit Code: {result.exit_code}")
    print()
    print(result.output)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
