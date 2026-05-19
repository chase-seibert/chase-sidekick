#!/usr/bin/env python3
"""Generate a local Codex cost and token usage report."""

from __future__ import annotations

import json
import math
import re
import shlex
import shutil
import sqlite3
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

FOOTER = (
    "This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) "
    "and the [codex-cost-report skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/codex-cost-report)."
)
REPO_ROOT = Path.cwd()
CODEX_ROOT = Path.home() / ".codex"
STATE_DB = CODEX_ROOT / "state_5.sqlite"
SESSIONS_ROOT = CODEX_ROOT / "sessions"
REPORT_DIR = REPO_ROOT / "memory"
GENERATED_AT = datetime.now().astimezone()
REPORT_PATH = REPORT_DIR / f"codex-cost-report-{GENERATED_AT.date().isoformat()}.qmd"

# USD prices are standard short-context API rates per 1M tokens.
# Codex credits are token-based credit rates per 1M tokens.
MODEL_RATES = {
    "gpt-5.5": {
        "display": "GPT-5.5",
        "usd": {"input": 5.00, "cached_input": 0.50, "output": 30.00},
        "credits": {"input": 125.0, "cached_input": 12.5, "output": 750.0},
    },
    "gpt-5.4": {
        "display": "GPT-5.4",
        "usd": {"input": 2.50, "cached_input": 0.25, "output": 15.00},
        "credits": {"input": 62.5, "cached_input": 6.25, "output": 375.0},
    },
    "gpt-5.4-mini": {
        "display": "GPT-5.4 Mini",
        "usd": {"input": 0.75, "cached_input": 0.075, "output": 4.50},
        "credits": {"input": 18.75, "cached_input": 1.875, "output": 113.0},
    },
    "gpt-5.3-codex": {
        "display": "GPT-5.3-Codex",
        "usd": None,
        "credits": {"input": 43.75, "cached_input": 4.375, "output": 350.0},
    },
    "gpt-5.2": {
        "display": "GPT-5.2",
        "usd": None,
        "credits": {"input": 43.75, "cached_input": 4.375, "output": 350.0},
    },
}

MODEL_ALIASES = {
    "codex-auto-review": "gpt-5.3-codex",
}

USER_SOURCES = {"vscode", "exec"}
TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")
PATCH_PATH_RE = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File):\s+(.+)$")
PATCH_MOVE_RE = re.compile(r"^\*\*\* Move to:\s+(.+)$")
REDIRECT_RE = re.compile(r"(?:^|\s)(?:\d*)>{1,2}\s*([^\s;&|>]+)")
TEE_RE = re.compile(r"\btee\s+(?:-[a-zA-Z]+\s+)*([^\s;&|]+)")
FORMATTER_WRITE_RE = re.compile(r"\b(?:black|prettier|eslint|ruff|rubocop)\b.*(?:--fix|--write|-w)\b")
PACKAGE_INSTALL_RE = re.compile(r"\b(?:npm|pnpm|yarn|bun)\s+(?:install|add)\b")
GIT_WRITE_RE = re.compile(r"\bgit\s+(?:add|commit|mv)\b")
SHELL_FILE_WRITE_RE = re.compile(r"(?:^|[;&|]\s*)(?:touch|mkdir|cp|mv|install)\b")
NON_REPO_PATH_PREFIXES = (
    "memory/",
    "./memory/",
    "/tmp/",
    "/private/tmp/",
    "/var/folders/",
    "/dev/null",
    "$TMPDIR/",
    "${TMPDIR}/",
)


@dataclass
class SessionUsage:
    session_id: str
    title: str
    source: str
    created_at: datetime
    updated_at: datetime
    project: str
    project_path: str
    models: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    work_type: str = "cowork"
    work_type_reason: str = "no local non-memory write signal"
    usd: float = 0.0
    credits: float = 0.0
    unknown_usd_models: set[str] = field(default_factory=set)


def as_local_datetime(ms: int | None) -> datetime:
    if ms:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()
    return datetime.fromtimestamp(0, tz=timezone.utc).astimezone()


def parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return None


def fmt_money(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "n/a"
    return f"${value:,.2f}"


def fmt_number(value: int | float) -> str:
    return f"{value:,.0f}"


def fmt_percent(numerator: int | float, denominator: int | float) -> str:
    if not denominator:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def md_escape(value: str) -> str:
    return value.replace("|", "\\|")


def fmt_chart_value(value: float) -> str:
    if abs(value) < 0.00005:
        return "0"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def chart_axis_max(values: list[float]) -> float:
    highest = max(values) if values else 0
    if highest <= 0:
        return 1
    raw = highest * 1.1
    magnitude = 10 ** math.floor(math.log10(raw))
    normalized = raw / magnitude
    for step in (1, 2, 5, 10):
        if normalized <= step:
            return step * magnitude
    return 10 * magnitude


def mermaid_list(values: list[str | float]) -> str:
    encoded = []
    for value in values:
        if isinstance(value, str):
            encoded.append(json.dumps(value))
        else:
            encoded.append(fmt_chart_value(value))
    return "[" + ", ".join(encoded) + "]"


def week_label(day) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def monday_for_week(day):
    return day - timedelta(days=day.weekday())


def week_labels_between(first_day, last_day) -> list[str]:
    labels = []
    cursor = monday_for_week(first_day)
    end = monday_for_week(last_day)
    while cursor <= end:
        labels.append(week_label(cursor))
        cursor += timedelta(days=7)
    return labels


def compute_amounts(usage: Counter, model: str) -> tuple[float | None, float | None]:
    canonical_model = MODEL_ALIASES.get(model, model)
    rates = MODEL_RATES.get(canonical_model)
    if not rates:
        return None, None

    input_tokens = usage["input_tokens"]
    cached_tokens = usage["cached_input_tokens"]
    uncached_tokens = max(0, input_tokens - cached_tokens)
    output_tokens = usage["output_tokens"]

    usd = None
    if rates.get("usd"):
        usd_rates = rates["usd"]
        usd = (
            uncached_tokens * usd_rates["input"]
            + cached_tokens * usd_rates["cached_input"]
            + output_tokens * usd_rates["output"]
        ) / 1_000_000

    credits = None
    if rates.get("credits"):
        credit_rates = rates["credits"]
        credits = (
            uncached_tokens * credit_rates["input"]
            + cached_tokens * credit_rates["cached_input"]
            + output_tokens * credit_rates["output"]
        ) / 1_000_000

    return usd, credits


def compact_path(raw_path: str | None) -> str:
    path = (raw_path or "").strip()
    if not path:
        return "(unknown cwd)"
    home = str(Path.home())
    if path == home:
        return "~"
    if path.startswith(home + "/"):
        return "~/" + path[len(home) + 1 :]
    return path


def project_from_origin(raw_origin: str | None) -> str | None:
    origin = (raw_origin or "").strip().rstrip("/")
    if not origin:
        return None

    if origin.endswith(".git"):
        origin = origin[:-4]

    if "://" in origin:
        project_path = urlparse(origin).path.strip("/")
    elif ":" in origin:
        project_path = origin.rsplit(":", 1)[1].strip("/")
    else:
        project_path = origin.strip("/")

    return project_path.rsplit("/", 1)[-1] or None


def project_name(cwd: str | None, git_origin_url: str | None) -> str:
    from_origin = project_from_origin(git_origin_url)
    if from_origin:
        return from_origin

    compact = compact_path(cwd)
    if compact in {"", "~", "(unknown cwd)"}:
        return compact
    return compact.rstrip("/").rsplit("/", 1)[-1] or compact


def clean_path(raw_path: str) -> str:
    path = raw_path.strip().strip("\"'")
    while path.startswith("./"):
        path = path[2:]
    return path


def is_memory_or_temp_path(raw_path: str) -> bool:
    path = clean_path(raw_path)
    if not path:
        return False
    if path.startswith("&") or path.isdigit():
        return True
    return path.startswith(NON_REPO_PATH_PREFIXES)


def non_memory_paths(paths: list[str]) -> list[str]:
    return [clean_path(path) for path in paths if clean_path(path) and not is_memory_or_temp_path(path)]


def patch_paths(patch_text: str) -> list[str]:
    paths = []
    for line in patch_text.splitlines():
        path_match = PATCH_PATH_RE.match(line)
        move_match = PATCH_MOVE_RE.match(line)
        if path_match:
            paths.append(path_match.group(1))
        elif move_match:
            paths.append(move_match.group(1))
    return paths


def parse_call_arguments(arguments) -> dict:
    if isinstance(arguments, dict):
        return arguments
    if not isinstance(arguments, str):
        return {}
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError:
        return {"_raw": arguments}
    return parsed if isinstance(parsed, dict) else {}


def command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def path_candidates(command: str) -> list[str]:
    candidates = []
    for token in command_tokens(command):
        if not token or token.startswith("-"):
            continue
        if "=" in token and not token.startswith(("=", "./", "/")):
            token = token.split("=", 1)[1]
        token = token.rstrip(",")
        if token in {".", ".."} or "/" in token or "." in token:
            candidates.append(token)
    return candidates


def shell_write_reason(command: str) -> str | None:
    if not command:
        return None

    redirected = non_memory_paths([match.group(1) for match in REDIRECT_RE.finditer(command)])
    if redirected:
        return f"shell redirection wrote {redirected[0]}"

    tee_paths = non_memory_paths([match.group(1) for match in TEE_RE.finditer(command)])
    if tee_paths:
        return f"tee wrote {tee_paths[0]}"

    command_paths = non_memory_paths(path_candidates(command))
    if GIT_WRITE_RE.search(command):
        if command_paths:
            return f"git write touched {command_paths[0]}"
        return "git write command"

    if SHELL_FILE_WRITE_RE.search(command) and command_paths:
        return f"shell file command touched {command_paths[0]}"

    if FORMATTER_WRITE_RE.search(command):
        return "formatter write command"

    if PACKAGE_INSTALL_RE.search(command):
        return "package install command"

    return None


def coding_reasons_for_record(record: dict) -> list[str]:
    payload = record.get("payload") or {}
    if not isinstance(payload, dict):
        return []

    reasons = []
    if payload.get("type") == "function_call":
        name = payload.get("name") or ""
        args = parse_call_arguments(payload.get("arguments"))

        if "apply_patch" in name:
            patch_text = args.get("_raw") or args.get("patch") or args.get("cmd") or payload.get("arguments") or ""
            changed_paths = non_memory_paths(patch_paths(str(patch_text)))
            if changed_paths:
                reasons.append(f"apply_patch changed {changed_paths[0]}")
            elif patch_text:
                reasons.append("apply_patch changed local files")

        if name.endswith("exec_command") or name in {"exec_command", "shell", "bash"}:
            reason = shell_write_reason(str(args.get("cmd") or args.get("command") or ""))
            if reason:
                reasons.append(reason)

    return reasons


def read_threads() -> dict[str, dict]:
    if not STATE_DB.exists():
        raise SystemExit(f"Missing Codex state database: {STATE_DB}")

    connection = sqlite3.connect(STATE_DB)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        select id, title, source, model, created_at_ms, updated_at_ms, cwd, git_origin_url
        from threads
        """
    ).fetchall()
    return {row["id"]: dict(row) for row in rows}


def read_session_usage(path: Path) -> tuple[str | None, dict[str, Counter], datetime | None, datetime | None, list[str]]:
    session_id = None
    current_model = None
    usage_by_model: dict[str, Counter] = defaultdict(Counter)
    first_seen = None
    last_seen = None
    coding_reasons = []

    for line in path.read_text(errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        coding_reasons.extend(coding_reasons_for_record(record))

        timestamp = parse_iso_timestamp(record.get("timestamp"))
        first_seen = first_seen or timestamp
        last_seen = timestamp or last_seen

        payload = record.get("payload") or {}
        record_type = record.get("type")

        if record_type == "session_meta":
            session_id = payload.get("id") or session_id
        elif record_type == "turn_context":
            current_model = payload.get("model") or current_model
        elif record_type == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info") or {}
            last_usage = info.get("last_token_usage") or {}
            if not last_usage or not current_model:
                continue
            for key in TOKEN_KEYS:
                value = last_usage.get(key)
                if isinstance(value, int):
                    usage_by_model[current_model][key] += value

    return session_id, usage_by_model, first_seen, last_seen, coding_reasons


def build_sessions() -> tuple[list[SessionUsage], Counter]:
    threads = read_threads()
    counters = Counter()
    sessions: list[SessionUsage] = []

    for path in sorted(SESSIONS_ROOT.glob("**/*.jsonl")):
        session_id, usage_by_model, first_seen, last_seen, coding_reasons = read_session_usage(path)
        if not session_id:
            counters["missing_session_id"] += 1
            continue

        thread = threads.get(session_id)
        if not thread:
            counters["missing_thread_metadata"] += 1
            continue

        source = thread.get("source") or ""
        if source not in USER_SOURCES:
            counters["excluded_internal_sessions"] += 1
            continue

        if not usage_by_model:
            counters["sessions_without_token_usage"] += 1
            continue

        session = SessionUsage(
            session_id=session_id,
            title=thread.get("title") or "(untitled)",
            source=source,
            created_at=as_local_datetime(thread.get("created_at_ms")) if thread.get("created_at_ms") else first_seen,
            updated_at=as_local_datetime(thread.get("updated_at_ms")) if thread.get("updated_at_ms") else last_seen,
            project=project_name(thread.get("cwd"), thread.get("git_origin_url")),
            project_path=compact_path(thread.get("cwd")),
            models=usage_by_model,
            work_type="coding" if coding_reasons else "cowork",
            work_type_reason=coding_reasons[0] if coding_reasons else "no local non-memory write signal",
        )

        for model, usage in usage_by_model.items():
            usd, credits = compute_amounts(usage, model)
            if usd is None:
                session.unknown_usd_models.add(MODEL_ALIASES.get(model, model))
            else:
                session.usd += usd
            if credits is not None:
                session.credits += credits

        sessions.append(session)

    return sessions, counters


def add_table(lines: list[str], headers: list[str], rows: list[list[str]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    if rows:
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")
    else:
        lines.append("| " + " | ".join(["n/a"] * len(headers)) + " |")
    lines.append("")


def add_mermaid(lines: list[str], chart_lines: list[str]) -> None:
    lines.append("```{mermaid}")
    lines.extend(chart_lines)
    lines.append("```")
    lines.append("")


def report() -> str:
    sessions, counters = build_sessions()
    if not sessions:
        raise SystemExit("No user-created Codex sessions with token usage found.")

    model_usage: dict[str, Counter] = defaultdict(Counter)
    model_sessions = Counter()
    by_day = Counter()
    by_week = Counter()
    by_month = Counter()
    by_year = Counter()
    work_type_usd = Counter()
    work_type_sessions = Counter()
    project_usd = Counter()
    project_credits = Counter()
    project_sessions = Counter()
    project_work_type_sessions: dict[str, Counter] = defaultdict(Counter)
    project_usage: dict[str, Counter] = defaultdict(Counter)
    project_paths: dict[str, Counter] = defaultdict(Counter)
    unknown_usd_models = Counter()

    total_usd = 0.0
    total_credits = 0.0
    total_usage = Counter()

    for session in sessions:
        day = session.created_at.date().isoformat()
        week = week_label(session.created_at.date())
        month = session.created_at.strftime("%Y-%m")
        year = session.created_at.strftime("%Y")
        by_day[day] += session.usd
        by_week[week] += session.usd
        by_month[month] += session.usd
        by_year[year] += session.usd
        work_type_usd[session.work_type] += session.usd
        work_type_sessions[session.work_type] += 1
        project_usd[session.project] += session.usd
        project_credits[session.project] += session.credits
        project_sessions[session.project] += 1
        project_work_type_sessions[session.project][session.work_type] += 1
        project_paths[session.project][session.project_path] += 1
        total_usd += session.usd
        total_credits += session.credits
        for model in session.unknown_usd_models:
            unknown_usd_models[model] += 1
        for model, usage in session.models.items():
            canonical_model = MODEL_ALIASES.get(model, model)
            model_sessions[canonical_model] += 1
            model_usage[canonical_model].update(usage)
            project_usage[session.project].update(usage)
            total_usage.update(usage)

    first_day = min(session.created_at.date() for session in sessions)
    last_day = max(session.created_at.date() for session in sessions)
    covered_days = max(1, (last_day - first_day).days + 1)
    average_daily_usd = total_usd / covered_days
    projected_monthly_usd = average_daily_usd * 30
    projected_yearly_usd = average_daily_usd * 365
    average_session_usd = total_usd / len(sessions)
    projected_yearly_credits = (total_credits / covered_days) * 365
    top_sessions = sorted(sessions, key=lambda item: item.usd, reverse=True)[:10]
    projects_by_usd = sorted(project_usd, key=lambda project: project_usd[project], reverse=True)
    top_projects = projects_by_usd[:10]
    week_labels = week_labels_between(first_day, last_day)
    weekly_values = [by_week[label] for label in week_labels]
    top_session_values = [session.usd for session in top_sessions]
    top_project_values = [project_usd[project] for project in top_projects]
    top_project_name = top_projects[0] if top_projects else "n/a"

    lines = [
        "---",
        f'title: "Codex Cost Report - {GENERATED_AT.date().isoformat()}"',
        "format:",
        "  html:",
        "    embed-resources: true",
        "    toc: true",
        "execute:",
        "  enabled: false",
        'prompt: "Generate Codex cost report for local user-created sessions"',
        'client: "codex-cost-report"',
        'command: "python3 .agents/skills/codex-cost-report/scripts/generate_report.py"',
        f'created: "{GENERATED_AT.strftime("%Y-%m-%d %H:%M:%S %Z")}"',
        f'updated: "{GENERATED_AT.strftime("%Y-%m-%d %H:%M:%S %Z")}"',
        "---",
        "",
        f"# Codex Cost Report - {GENERATED_AT.date().isoformat()}",
        "",
        "## Summary",
        f"- Generated: {GENERATED_AT.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- Period covered: {first_day.isoformat()} to {last_day.isoformat()} ({covered_days} days)",
        f"- Sessions included: {len(sessions)} user-created sessions",
        f"- Sessions excluded: {counters['excluded_internal_sessions']} internal/subagent sessions",
        f"- Projects included: {len(project_sessions)}",
        f"- Top project by estimated cost: {top_project_name} ({fmt_money(project_usd[top_project_name])})",
        f"- Estimated API-equivalent total: {fmt_money(total_usd)}",
        f"- Estimated Codex credits: {total_credits:,.1f}",
        f"- Average per included session: {fmt_money(average_session_usd)}",
        f"- Cache hit rate: {fmt_percent(total_usage['cached_input_tokens'], total_usage['input_tokens'])}",
        f"- Projected 30-day run rate: {fmt_money(projected_monthly_usd)}",
        f"- Projected full-year cost at current pace: {fmt_money(projected_yearly_usd)}",
        f"- Projected full-year Codex credits at current pace: {projected_yearly_credits:,.1f}",
        "",
        "## Notes",
        "- Dollar amounts are API-equivalent estimates from local token usage, not invoices.",
        "- Reasoning tokens are shown separately in model tables, but are not added again because they are already included in output tokens.",
        "- Credential material, raw prompts, and transcript content are intentionally omitted.",
        "- Pricing sources checked on 2026-04-30: OpenAI API Pricing and OpenAI Codex rate card.",
        "- Coding versus cowork is a best-effort classification based on local non-memory write signals in the Codex session log.",
        "- Project is derived from the thread git origin repo name when present, otherwise from the thread current working directory.",
        "",
        "## Charts",
        "",
        "### Top Projects By Estimated Cost",
        "",
        "Bars are labeled by rank; the project details table below maps each rank to project name.",
        "",
    ]

    add_mermaid(
        lines,
        [
            "xychart-beta",
            '  title "Top Projects by Estimated Cost"',
            f"  x-axis {mermaid_list([f'P{index}' for index in range(1, len(top_projects) + 1)])}",
            f'  y-axis "USD" 0 --> {fmt_chart_value(chart_axis_max(top_project_values))}',
            f"  bar {mermaid_list(top_project_values)}",
        ],
    )

    lines.extend([
        "### Top Sessions By Estimated Cost",
        "",
        "Bars are labeled by rank; the session details table below maps each rank to title and thread id.",
        "",
    ])

    add_mermaid(
        lines,
        [
            "xychart-beta",
            '  title "Top Sessions by Estimated Cost"',
            f"  x-axis {mermaid_list([f'S{index}' for index in range(1, len(top_sessions) + 1)])}",
            f'  y-axis "USD" 0 --> {fmt_chart_value(chart_axis_max(top_session_values))}',
            f"  bar {mermaid_list(top_session_values)}",
        ],
    )

    lines.extend([
        "### Coding Versus Cowork",
        "",
        "This pie chart splits included estimated cost by the coding/cowork heuristic.",
        "",
    ])
    add_mermaid(
        lines,
        [
            "pie showData",
            '  title "Estimated Cost by Work Type"',
            f'  "Coding" : {fmt_chart_value(work_type_usd["coding"])}',
            f'  "Cowork" : {fmt_chart_value(work_type_usd["cowork"])}',
        ],
    )

    lines.extend([
        "### Cost Per Week",
        "",
        "The line chart uses ISO weeks over the full analyzed period.",
        "",
    ])
    add_mermaid(
        lines,
        [
            "xychart-beta",
            '  title "Estimated Cost Per Week"',
            f"  x-axis {mermaid_list(week_labels)}",
            f'  y-axis "USD" 0 --> {fmt_chart_value(chart_axis_max(weekly_values))}',
            f"  line {mermaid_list(weekly_values)}",
        ],
    )

    lines.extend([
        "## Cost By Day",
    ]
    )

    add_table(
        lines,
        ["Day", "Estimated USD"],
        [[day, fmt_money(by_day[day])] for day in sorted(by_day)],
    )

    lines.append("## Cost By Month")
    add_table(
        lines,
        ["Month", "Estimated USD"],
        [[month, fmt_money(by_month[month])] for month in sorted(by_month)],
    )

    lines.append("## Cost By Year")
    add_table(
        lines,
        ["Year", "Estimated USD"],
        [[year, fmt_money(by_year[year])] for year in sorted(by_year)],
    )

    lines.append("## Cost By Work Type")
    add_table(
        lines,
        ["Work Type", "Sessions", "Estimated USD", "Share"],
        [
            [
                work_type.title(),
                fmt_number(work_type_sessions[work_type]),
                fmt_money(work_type_usd[work_type]),
                fmt_percent(work_type_usd[work_type], total_usd),
            ]
            for work_type in ("coding", "cowork")
        ],
    )

    lines.append("## Cost By Project")
    project_rows = []
    for index, project in enumerate(projects_by_usd, start=1):
        usage = project_usage[project]
        primary_path = project_paths[project].most_common(1)[0][0]
        project_rows.append([
            f"P{index}",
            md_escape(project),
            md_escape(primary_path),
            fmt_number(project_sessions[project]),
            fmt_number(project_work_type_sessions[project]["coding"]),
            fmt_number(project_work_type_sessions[project]["cowork"]),
            fmt_money(project_usd[project]),
            fmt_percent(project_usd[project], total_usd),
            fmt_money(project_usd[project] / project_sessions[project]),
            f"{project_credits[project]:,.1f}",
            fmt_number(usage["total_tokens"]),
            fmt_percent(usage["cached_input_tokens"], usage["input_tokens"]),
        ])
    add_table(
        lines,
        [
            "Rank",
            "Project",
            "Primary CWD",
            "Sessions",
            "Coding",
            "Cowork",
            "Estimated USD",
            "Share",
            "Average Session",
            "Codex Credits",
            "Tokens",
            "Cache %",
        ],
        project_rows,
    )

    lines.append("## Usage By Model")
    model_rows = []
    for model, usage in sorted(model_usage.items(), key=lambda item: item[1]["total_tokens"], reverse=True):
        usd, credits = compute_amounts(usage, model)
        model_rows.append([
            MODEL_RATES.get(model, {}).get("display", model),
            str(model_sessions[model]),
            fmt_number(usage["input_tokens"]),
            fmt_number(usage["cached_input_tokens"]),
            fmt_percent(usage["cached_input_tokens"], usage["input_tokens"]),
            fmt_number(usage["output_tokens"]),
            fmt_number(usage["reasoning_output_tokens"]),
            fmt_money(usd),
            "n/a" if credits is None else f"{credits:,.1f}",
        ])
    add_table(
        lines,
        ["Model", "Sessions", "Input", "Cached Input", "Cache %", "Output", "Reasoning", "Estimated USD", "Codex Credits"],
        model_rows,
    )

    lines.append("## Top 10 Most Expensive Sessions")
    top_rows = []
    for index, session in enumerate(top_sessions, start=1):
        model_list = ", ".join(sorted({MODEL_ALIASES.get(model, model) for model in session.models}))
        total_tokens = sum(usage["total_tokens"] for usage in session.models.values())
        top_rows.append([
            f"S{index}",
            session.created_at.date().isoformat(),
            md_escape(session.project),
            md_escape(session.title),
            model_list,
            session.work_type,
            fmt_money(session.usd),
            f"{session.credits:,.1f}",
            fmt_number(total_tokens),
            session.session_id,
        ])
    add_table(
        lines,
        ["Rank", "Date", "Project", "Session", "Model", "Work Type", "Estimated USD", "Codex Credits", "Tokens", "Thread ID"],
        top_rows,
    )

    lines.append("## Data Gaps")
    if unknown_usd_models:
        for model, count in sorted(unknown_usd_models.items()):
            lines.append(f"- No direct USD API rate configured for `{model}`; excluded from USD totals in {count} session(s).")
    else:
        lines.append("- No unknown USD model rates in included sessions.")
    for key, value in sorted(counters.items()):
        if value and key != "excluded_internal_sessions":
            lines.append(f"- {key.replace('_', ' ').capitalize()}: {value}")
    lines.append("")
    lines.append("## Methodology Executive Summary")
    lines.append("")
    lines.append(
        "The generator reads thread metadata from `~/.codex/state_5.sqlite` and scans "
        "`~/.codex/sessions/**/*.jsonl` for session ids, model changes, token-count events, "
        "and local write signals. It includes user-created Codex Desktop and exec/trigger "
        "threads (`vscode` and `exec`) and excludes internal subagent or guardian sessions. "
        "Project rollups use the thread git origin repo name when available and otherwise "
        "fall back to the thread current working directory name."
    )
    lines.append("")
    lines.append(
        "For each token-count event, the active model comes from the most recent turn context. "
        "Estimated USD is calculated as uncached input tokens times the input rate, cached "
        "input tokens times the cached-input rate, and output tokens times the output rate, "
        "using the script's short-context pricing table. Reasoning tokens are reported "
        "separately but not charged a second time because they are included in output tokens. "
        "The full-year projection multiplies the observed average daily estimated cost by 365."
    )
    lines.append("")
    lines.append(FOOTER)
    return "\n".join(lines) + "\n"


def render_html(report_path: Path) -> Path:
    if not shutil.which("quarto"):
        raise SystemExit(f"Generated {report_path}, but could not render HTML because `quarto` is not installed.")

    result = subprocess.run(
        ["quarto", "render", str(report_path), "--to", "html"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode:
        raise SystemExit(f"Generated {report_path}, but Quarto HTML render failed:\n{result.stdout}")

    return report_path.with_suffix(".html")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report())
    html_path = render_html(REPORT_PATH)
    print(f"Codex cost report generated: {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(f"Codex cost report HTML rendered: {html_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
