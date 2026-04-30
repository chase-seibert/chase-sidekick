#!/usr/bin/env python3
"""Generate a local Codex cost and token usage report."""

from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

FOOTER = "This report generated using https://github.com/chase-seibert/chase-sidekick"
REPO_ROOT = Path.cwd()
CODEX_ROOT = Path.home() / ".codex"
STATE_DB = CODEX_ROOT / "state_5.sqlite"
SESSIONS_ROOT = CODEX_ROOT / "sessions"
REPORT_DIR = REPO_ROOT / "memory"
GENERATED_AT = datetime.now().astimezone()
REPORT_PATH = REPORT_DIR / f"codex-cost-report-{GENERATED_AT.date().isoformat()}.md"

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


@dataclass
class SessionUsage:
    session_id: str
    title: str
    source: str
    created_at: datetime
    updated_at: datetime
    models: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
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


def read_threads() -> dict[str, dict]:
    if not STATE_DB.exists():
        raise SystemExit(f"Missing Codex state database: {STATE_DB}")

    connection = sqlite3.connect(STATE_DB)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        select id, title, source, model, created_at_ms, updated_at_ms
        from threads
        """
    ).fetchall()
    return {row["id"]: dict(row) for row in rows}


def read_session_usage(path: Path) -> tuple[str | None, dict[str, Counter], datetime | None, datetime | None]:
    session_id = None
    current_model = None
    usage_by_model: dict[str, Counter] = defaultdict(Counter)
    first_seen = None
    last_seen = None

    for line in path.read_text(errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

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

    return session_id, usage_by_model, first_seen, last_seen


def build_sessions() -> tuple[list[SessionUsage], Counter]:
    threads = read_threads()
    counters = Counter()
    sessions: list[SessionUsage] = []

    for path in sorted(SESSIONS_ROOT.glob("**/*.jsonl")):
        session_id, usage_by_model, first_seen, last_seen = read_session_usage(path)
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
            models=usage_by_model,
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


def report() -> str:
    sessions, counters = build_sessions()
    if not sessions:
        raise SystemExit("No user-created Codex sessions with token usage found.")

    model_usage: dict[str, Counter] = defaultdict(Counter)
    model_sessions = Counter()
    by_day = Counter()
    by_month = Counter()
    by_year = Counter()
    unknown_usd_models = Counter()

    total_usd = 0.0
    total_credits = 0.0
    total_usage = Counter()

    for session in sessions:
        day = session.created_at.date().isoformat()
        month = session.created_at.strftime("%Y-%m")
        year = session.created_at.strftime("%Y")
        by_day[day] += session.usd
        by_month[month] += session.usd
        by_year[year] += session.usd
        total_usd += session.usd
        total_credits += session.credits
        for model in session.unknown_usd_models:
            unknown_usd_models[model] += 1
        for model, usage in session.models.items():
            canonical_model = MODEL_ALIASES.get(model, model)
            model_sessions[canonical_model] += 1
            model_usage[canonical_model].update(usage)
            total_usage.update(usage)

    first_day = min(session.created_at.date() for session in sessions)
    last_day = max(session.created_at.date() for session in sessions)
    covered_days = max(1, (last_day - first_day).days + 1)
    average_daily_usd = total_usd / covered_days
    projected_monthly_usd = average_daily_usd * 30
    projected_yearly_usd = average_daily_usd * 365
    average_session_usd = total_usd / len(sessions)

    lines = [
        "---",
        "prompt: Generate Codex cost report for local user-created sessions",
        "client: codex-cost-report",
        "command: python3 .agents/skills/codex-cost-report/scripts/generate_report.py",
        f"created: {GENERATED_AT.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"updated: {GENERATED_AT.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "---",
        "",
        f"# Codex Cost Report - {GENERATED_AT.date().isoformat()}",
        "",
        "## Summary",
        f"- Generated: {GENERATED_AT.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- Period covered: {first_day.isoformat()} to {last_day.isoformat()} ({covered_days} days)",
        f"- Sessions included: {len(sessions)} user-created sessions",
        f"- Sessions excluded: {counters['excluded_internal_sessions']} internal/subagent sessions",
        f"- Estimated API-equivalent total: {fmt_money(total_usd)}",
        f"- Estimated Codex credits: {total_credits:,.1f}",
        f"- Average per included session: {fmt_money(average_session_usd)}",
        f"- Cache hit rate: {fmt_percent(total_usage['cached_input_tokens'], total_usage['input_tokens'])}",
        f"- Projected 30-day run rate: {fmt_money(projected_monthly_usd)}",
        f"- Projected annual run rate: {fmt_money(projected_yearly_usd)}",
        "",
        "## Notes",
        "- Dollar amounts are API-equivalent estimates from local token usage, not invoices.",
        "- Reasoning tokens are shown separately in model tables, but are not added again because they are already included in output tokens.",
        "- Credential material, raw prompts, and transcript content are intentionally omitted.",
        "- Pricing sources checked on 2026-04-30: OpenAI API Pricing and OpenAI Codex rate card.",
        "",
        "## Cost By Day",
    ]

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
    for session in sorted(sessions, key=lambda item: item.usd, reverse=True)[:10]:
        model_list = ", ".join(sorted({MODEL_ALIASES.get(model, model) for model in session.models}))
        total_tokens = sum(usage["total_tokens"] for usage in session.models.values())
        top_rows.append([
            session.created_at.date().isoformat(),
            session.title.replace("|", "\\|"),
            model_list,
            fmt_money(session.usd),
            f"{session.credits:,.1f}",
            fmt_number(total_tokens),
            session.session_id,
        ])
    add_table(
        lines,
        ["Date", "Session", "Model", "Estimated USD", "Codex Credits", "Tokens", "Thread ID"],
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
    lines.append(FOOTER)
    return "\n".join(lines) + "\n"


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report())
    print(f"Codex cost report generated: {REPORT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
