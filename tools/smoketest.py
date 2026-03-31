#!/usr/bin/env python3
"""Smoketest tool - checks that basic reading of common files is working.

Tests access to:
- Paper docs by URL (via DropboxClient)
- Confluence docs by URL (via ConfluenceClient)
- Slack channels (requires Dash MCP - not available in standalone mode)

This is a standalone tool that doesn't invoke Claude agents.

Usage:
    python3 tools/smoketest.py

Or:
    ./tools/smoketest.py

The tool will test access to the files specified in CLAUDE.local.md under
"Smoketest files" and report success/failure for each type.

Note: Slack testing requires the Dash MCP server or /slack skill which are
only available when running within Claude Code, not from standalone Python.
"""
import sys
import os
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add sidekick to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidekick.clients.dropbox import DropboxClient
from sidekick.clients.confluence import ConfluenceClient
from sidekick.config import get_dropbox_config, get_atlassian_config


def truncate_text(text: str, max_lines: int = 500) -> str:
    """Truncate text to max_lines."""
    lines = text.split('\n')
    if len(lines) <= max_lines:
        return text
    return '\n'.join(lines[:max_lines]) + f'\n\n[... truncated {len(lines) - max_lines} lines]'


def get_tldr(text: str, max_lines: int = 10) -> str:
    """Get a TL;DR of the text (first few non-empty lines)."""
    lines = [line for line in text.split('\n') if line.strip()]
    if not lines:
        return "[Empty content]"

    preview_lines = lines[:max_lines]
    result = '\n'.join(preview_lines)

    if len(lines) > max_lines:
        result += f'\n[... {len(lines) - max_lines} more lines]'

    return result


def test_paper_doc(url: str) -> dict:
    """Test reading a Paper doc from URL.

    Returns dict with:
        - success: bool
        - method: str describing how it was accessed
        - content: str with the content (or error message)
        - tldr: str with preview of content
    """
    try:
        config = get_dropbox_config()
        client = DropboxClient(
            access_token=config.get("access_token"),
            refresh_token=config.get("refresh_token"),
            app_key=config.get("app_key"),
            app_secret=config.get("app_secret")
        )

        # Get paper contents in markdown format
        content = client.get_paper_contents_from_link(url, export_format="markdown")

        # Truncate to 500 lines
        truncated = truncate_text(content, max_lines=500)

        return {
            "success": True,
            "method": "DropboxClient.get_paper_contents_from_link() with markdown format",
            "content": truncated,
            "tldr": get_tldr(content)
        }
    except Exception as e:
        return {
            "success": False,
            "method": "DropboxClient.get_paper_contents_from_link()",
            "content": f"Error: {str(e)}",
            "tldr": f"Error: {str(e)}"
        }


def test_confluence_doc(url: str) -> dict:
    """Test reading a Confluence doc from URL.

    Returns dict with:
        - success: bool
        - method: str describing how it was accessed
        - content: str with the content (or error message)
        - tldr: str with preview of content
    """
    try:
        config = get_atlassian_config()
        client = ConfluenceClient(
            base_url=config["url"],
            email=config["email"],
            api_token=config["api_token"]
        )

        # Get confluence content in markdown format (default)
        content = client.get_content_from_link(url, return_markdown=True)

        # Truncate to 500 lines
        truncated = truncate_text(content, max_lines=500)

        return {
            "success": True,
            "method": "ConfluenceClient.get_content_from_link() with markdown format",
            "content": truncated,
            "tldr": get_tldr(content)
        }
    except Exception as e:
        return {
            "success": False,
            "method": "ConfluenceClient.get_content_from_link()",
            "content": f"Error: {str(e)}",
            "tldr": f"Error: {str(e)}"
        }


def test_slack_channel(channel: str) -> dict:
    """Test reading a Slack channel.

    For Slack, we need to use the Dash MCP or /slack skill.
    This is not available from standalone Python scripts - it requires
    running within Claude Code.

    Returns dict with:
        - success: bool (always False in standalone mode)
        - method: str describing how it should be accessed
        - content: str with instructions
        - tldr: str with preview
    """
    # Calculate date for 10 days ago
    ten_days_ago = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    return {
        "success": False,
        "method": "Requires Dash MCP (not available in standalone Python)",
        "content": (
            f"Slack testing requires Dash MCP or /slack skill, which are only "
            f"available when running within Claude Code.\n\n"
            f"To test Slack manually:\n"
            f"1. Use /slack skill in Claude Code\n"
            f"2. Or use Dash MCP slack_search_messages tool\n"
            f"3. Search: channel:{channel} after:{ten_days_ago}\n"
        ),
        "tldr": "⚠️  Slack requires Dash MCP (Claude Code only) - cannot test in standalone mode"
    }


def format_result(name: str, result: dict) -> str:
    """Format a test result for display."""
    emoji = "✅" if result["success"] else "🛑"

    output = [
        f"\n{emoji} {name}",
        f"Method: {result['method']}",
        "",
        "TL;DR:",
        result['tldr'],
        ""
    ]

    return '\n'.join(output)


def main():
    """Run smoketest on all configured sources."""
    # Test files from CLAUDE.local.md (can be overridden via command line)
    paper_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.dropbox.com/scl/fi/ydtb7jfymn82lbiuyrezm/Chase-Agentic-Scratch.paper?rlkey=sqm8vwef8f93stm1ih9t1papb&st=k430v6w2&dl=0"
    confluence_url = sys.argv[2] if len(sys.argv) > 2 else "https://dropbox.atlassian.net/wiki/spaces/TNC/pages/3247802141/Chase+Nandan+1+1"
    slack_channel = sys.argv[3] if len(sys.argv) > 3 else "#core-eng-lt"

    print("=" * 70)
    print("SMOKETEST - Testing access to common file types")
    print("=" * 70)
    print(f"Paper URL: {paper_url[:50]}...")
    print(f"Confluence URL: {confluence_url[:50]}...")
    print(f"Slack Channel: {slack_channel}")
    print("=" * 70)

    # Test Paper doc
    print("\n[1/3] Testing Paper doc access...")
    paper_result = test_paper_doc(paper_url)
    print(format_result("Paper Doc", paper_result))

    # Test Confluence doc
    print("\n[2/3] Testing Confluence doc access...")
    confluence_result = test_confluence_doc(confluence_url)
    print(format_result("Confluence Doc", confluence_result))

    # Test Slack channel
    print("\n[3/3] Testing Slack channel access...")
    slack_result = test_slack_channel(slack_channel)
    print(format_result("Slack Channel", slack_result))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    results = [
        ("Paper", paper_result),
        ("Confluence", confluence_result),
        ("Slack", slack_result)
    ]

    for name, result in results:
        emoji = "✅" if result["success"] else "🛑"
        print(f"{emoji} {name}: {result['method']}")

    # Exit with error code if any test failed
    all_success = all(r["success"] for _, r in results)
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
