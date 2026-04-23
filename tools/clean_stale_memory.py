#!/usr/bin/env python3
"""Clean up stale memory files that haven't been updated in 30 days.

This tool scans the memory directory and deletes files that:
1. Have not been modified in the last 30 days
2. Are markdown (.md) or JSON (.json) files

Usage:
    # Dry run (default) - shows what would be deleted
    python3 tools/clean_stale_memory.py

    # Actually delete files
    python3 tools/clean_stale_memory.py --delete

    # Custom age threshold (e.g., 60 days)
    python3 tools/clean_stale_memory.py --days 60 --delete

Output format:
    Shows each file with its age and whether it was deleted or would be deleted.

Safety:
    - Defaults to dry-run mode to preview what would be deleted
    - Ignores MEMORY.md index file
    - Ignores local/ directory (configuration files)
    - Only processes .md and .json files
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone


def get_file_age_days(file_path: Path) -> int:
    """Get the age of a file in days based on modification time.

    Args:
        file_path: Path to the file

    Returns:
        Number of days since last modification
    """
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    age = now - mtime
    return age.days


def should_skip_file(file_path: Path, memory_dir: Path) -> tuple[bool, str]:
    """Determine if a file should be skipped from deletion.

    Args:
        file_path: Path to the file
        memory_dir: Root memory directory

    Returns:
        Tuple of (should_skip, reason)
    """
    # Skip MEMORY.md index file
    if file_path.name == "MEMORY.md":
        return True, "index file"

    # Skip local/ directory (configuration files)
    try:
        relative_path = file_path.relative_to(memory_dir)
        if relative_path.parts[0] == "local":
            return True, "local config"
    except ValueError:
        pass

    # Only process markdown and JSON files
    if file_path.suffix not in [".md", ".json"]:
        return True, "not md/json"

    return False, ""


def find_stale_files(memory_dir: Path, days: int) -> list[tuple[Path, int]]:
    """Find all files older than the specified number of days.

    Args:
        memory_dir: Root memory directory
        days: Age threshold in days

    Returns:
        List of (file_path, age_in_days) tuples
    """
    stale_files = []

    for file_path in memory_dir.rglob("*"):
        if not file_path.is_file():
            continue

        # Check if file should be skipped
        should_skip, reason = should_skip_file(file_path, memory_dir)
        if should_skip:
            continue

        # Check age
        age_days = get_file_age_days(file_path)
        if age_days >= days:
            stale_files.append((file_path, age_days))

    return sorted(stale_files, key=lambda x: x[1], reverse=True)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string like "1.2 KB" or "3.4 MB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up stale memory files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Delete files not modified in this many days (default: 30)"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete files (default: dry-run mode)"
    )
    parser.add_argument(
        "--memory-dir",
        type=Path,
        default=None,
        help="Memory directory path (default: auto-detect from script location)"
    )

    args = parser.parse_args()

    # Determine memory directory
    if args.memory_dir:
        memory_dir = args.memory_dir
    else:
        # Auto-detect: assume script is in tools/ and memory/ is sibling
        script_dir = Path(__file__).parent
        memory_dir = script_dir.parent / "memory"

    if not memory_dir.exists():
        print(f"❌ Memory directory not found: {memory_dir}", file=sys.stderr)
        sys.exit(1)

    # Find stale files
    stale_files = find_stale_files(memory_dir, args.days)

    if not stale_files:
        print(f"✅ No files older than {args.days} days found")
        sys.exit(0)

    # Print header
    mode = "DELETING" if args.delete else "DRY RUN"
    print(f"\n{mode}: Found {len(stale_files)} file(s) older than {args.days} days\n")

    # Process files
    total_size = 0
    deleted_count = 0

    for file_path, age_days in stale_files:
        file_size = file_path.stat().st_size
        total_size += file_size
        relative_path = file_path.relative_to(memory_dir)
        size_str = format_file_size(file_size)

        status = "🗑️  " if args.delete else "📋 "
        print(f"{status} {relative_path}")
        print(f"    Age: {age_days} days | Size: {size_str}")

        if args.delete:
            try:
                file_path.unlink()
                deleted_count += 1
                print(f"    ✅ Deleted")
            except Exception as e:
                print(f"    ❌ Failed to delete: {e}")

        print()

    # Summary
    total_size_str = format_file_size(total_size)
    print(f"{'=' * 60}")

    if args.delete:
        print(f"✅ Deleted {deleted_count} of {len(stale_files)} file(s)")
        print(f"💾 Freed {total_size_str} of disk space")
    else:
        print(f"📊 Would delete {len(stale_files)} file(s)")
        print(f"💾 Would free {total_size_str} of disk space")
        print(f"\nRun with --delete to actually delete these files")

    sys.exit(0)


if __name__ == "__main__":
    main()
