#!/usr/bin/env python3
"""Link ignored Sidekick context files into Codex worktrees."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


CONTEXT_PATHS = (
    ".env",
    "AGENTS.override.md",
    "settings.local.json",
    "local",
    "memory",
)


def run_git(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def find_repo_root() -> Path | None:
    try:
        return Path(run_git(["rev-parse", "--show-toplevel"])).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def find_primary_checkout(repo_root: Path) -> Path | None:
    override = os.environ.get("SIDEKICK_CONTEXT_SOURCE_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    try:
        common_git_dir = Path(
            run_git(["rev-parse", "--path-format=absolute", "--git-common-dir"], repo_root)
        ).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    if common_git_dir.name == ".git":
        return common_git_dir.parent.resolve()

    return None


def is_expected_symlink(destination: Path, source: Path) -> bool:
    if not destination.is_symlink():
        return False
    try:
        return destination.resolve(strict=False) == source.resolve(strict=False)
    except OSError:
        return False


def source_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def has_conflict(repo_root: Path, primary_root: Path, relative_path: str) -> bool:
    source = primary_root / relative_path
    destination = repo_root / relative_path

    if is_expected_symlink(destination, source):
        return False

    return source_exists(destination)


def link_context_path(repo_root: Path, primary_root: Path, relative_path: str) -> None:
    source = primary_root / relative_path
    destination = repo_root / relative_path

    if not source_exists(source):
        print(f"sidekick-context: source missing, skipping {source}", file=sys.stderr)
        return

    if is_expected_symlink(destination, source):
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(source, target_is_directory=source.is_dir())
    print(f"sidekick-context: linked {destination} -> {source}", file=sys.stderr)


def main() -> int:
    repo_root = find_repo_root()
    if repo_root is None:
        return 0

    primary_root = find_primary_checkout(repo_root)
    if primary_root is None:
        print(
            "sidekick-context: could not determine primary checkout; set "
            "SIDEKICK_CONTEXT_SOURCE_ROOT to enable linking",
            file=sys.stderr,
        )
        return 0

    if repo_root == primary_root:
        return 0

    conflicts = [
        path for path in CONTEXT_PATHS if has_conflict(repo_root, primary_root, path)
    ]
    if conflicts:
        print(
            "sidekick-context: existing context paths found; leaving worktree unchanged: "
            + ", ".join(conflicts),
            file=sys.stderr,
        )
        return 0

    for relative_path in CONTEXT_PATHS:
        link_context_path(repo_root, primary_root, relative_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
