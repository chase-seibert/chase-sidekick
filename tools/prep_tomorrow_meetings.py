#!/usr/bin/env python3
"""Prep tomorrow meetings tool - opens meeting docs in Chrome for next business day.

Usage:
    python3 tools/prep_tomorrow_meetings.py

Example:
    python3 tools/prep_tomorrow_meetings.py
"""
import sys
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from html import unescape

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidekick import config
from sidekick.clients.gcalendar import GCalendarClient


def calculate_next_business_day() -> tuple:
    """Calculate next business day date.

    Returns:
        Tuple of (date_string, start_timestamp, end_timestamp)
        - date_string: YYYY-MM-DD format
        - start_timestamp: RFC3339 timestamp for 00:00:00Z
        - end_timestamp: RFC3339 timestamp for 23:59:59Z
    """
    today = datetime.now()
    weekday = today.weekday()  # Monday=0, Sunday=6

    # If Friday (4), Saturday (5), or Sunday (6), next business day is Monday
    if weekday >= 4:
        days_ahead = 7 - weekday  # Days until next Monday
    else:
        days_ahead = 1  # Tomorrow

    next_day = today + timedelta(days=days_ahead)

    date_string = next_day.strftime("%Y-%m-%d")
    start_timestamp = f"{date_string}T00:00:00Z"
    end_timestamp = f"{date_string}T23:59:59Z"

    return date_string, start_timestamp, end_timestamp


def extract_urls_from_html(html_text: str) -> list:
    """Extract document URLs from HTML content.

    Args:
        html_text: HTML content (from event description)

    Returns:
        List of document URLs (Confluence, Paper, Google Docs)
    """
    if not html_text:
        return []

    urls = []

    doc_patterns = [
        'atlassian.net/wiki',  # Confluence
        'dropbox.com/scl/fi',  # Paper docs
        'dropbox.com/paper',   # Paper docs (old format)
        'docs.google.com/document',  # Google Docs
        'docs.google.com/spreadsheets',  # Google Sheets
        'docs.google.com/presentation',  # Google Slides
    ]

    # Extract href attributes from anchor tags
    # Pattern: <a href="URL">
    href_pattern = r'<a\s+[^>]*href=["\']([^"\']+)["\']'

    for match in re.finditer(href_pattern, html_text, re.IGNORECASE):
        url = match.group(1)

        # Only include document URLs (not calendar, zoom, etc.)
        if any(pattern in url for pattern in doc_patterns):
            # Unescape HTML entities (e.g., &amp; -> &)
            url = unescape(url)
            if url not in urls:
                urls.append(url)

    # Also extract bare URLs (not in anchor tags)
    # Pattern: https://... followed by one of our doc patterns
    bare_url_pattern = r'https://[^\s<>"\']+(?:' + '|'.join(re.escape(p) for p in doc_patterns) + r')[^\s<>"\']*'

    for match in re.finditer(bare_url_pattern, html_text):
        url = match.group(0)
        # Remove trailing HTML tags or entities
        url = re.sub(r'<[^>]*>.*$', '', url)
        # Unescape HTML entities
        url = unescape(url)
        if url not in urls:
            urls.append(url)

    return urls


def is_real_meeting(event: dict) -> bool:
    """Determine if calendar event is a real meeting (not habit/focus time).

    Args:
        event: Calendar event dict

    Returns:
        True if this is a real meeting, False otherwise
    """
    summary = event.get('summary', '')

    # Skip all-day events (typically not meetings)
    start = event.get('start', {})
    if 'date' in start and 'dateTime' not in start:
        return False

    # Skip events with habit/focus indicators in title
    skip_keywords = [
        '💪', '🚶', '📖', '🔒', '🥗', '👨‍💻', '✍️',  # Emoji indicators
        'DNS', 'Flexible', 'Heads Down', 'Focus',  # Focus time
        'Gym', 'Lunch', 'Walking', 'Reading',  # Personal habits
    ]

    for keyword in skip_keywords:
        if keyword in summary:
            return False

    # Must have a description OR attendees (real meetings have one or both)
    has_description = bool(event.get('description', '').strip())
    has_attendees = len(event.get('attendees', [])) > 1  # More than just you

    return has_description or has_attendees


def format_event_time(event: dict) -> str:
    """Format event time for display.

    Args:
        event: Calendar event dict

    Returns:
        Formatted time string (e.g., "9:00 AM", "2:30 PM")
    """
    start = event.get('start', {})

    if 'dateTime' in start:
        # Parse RFC3339 timestamp
        dt_str = start['dateTime']
        # Handle timezone offset or Z
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'

        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime('%I:%M %p').lstrip('0')  # Remove leading zero
        except ValueError:
            return "Unknown time"
    else:
        return "All day"


def open_urls_in_chrome(urls: list):
    """Open URLs in Chrome browser.

    Args:
        urls: List of URLs to open
    """
    if not urls:
        return

    try:
        # macOS: use 'open' command with Chrome
        cmd = ['open', '-a', 'Google Chrome'] + urls
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠ Error opening Chrome: {e}", file=sys.stderr)
        print("Trying default browser...", file=sys.stderr)
        # Fallback: open in default browser
        for url in urls:
            try:
                subprocess.run(['open', url], check=False)
            except Exception:
                pass


def main():
    """Main entry point."""
    try:
        # Calculate next business day
        date_str, start_time, end_time = calculate_next_business_day()
        weekday_name = datetime.fromisoformat(date_str).strftime('%A')

        print(f"Preparing meetings for {weekday_name}, {date_str}\n")

        # Get Google Calendar config
        google_config = config.get_google_config()

        # Create calendar client
        client = GCalendarClient(
            client_id=google_config['client_id'],
            client_secret=google_config['client_secret'],
            refresh_token=google_config['refresh_token']
        )

        # List events for next business day
        events = client.list_events(
            time_min=start_time,
            time_max=end_time,
            max_results=50
        )

        if not events:
            print(f"No events found for {weekday_name}")
            return

        # Filter for real meetings and extract doc URLs
        meetings_with_docs = []
        all_doc_urls = []

        for event in events:
            if not is_real_meeting(event):
                continue

            event_id = event.get('id')
            summary = event.get('summary', 'Untitled')
            description = event.get('description', '')

            # Extract doc URLs from description
            doc_urls = extract_urls_from_html(description)

            if doc_urls:
                time_str = format_event_time(event)
                meetings_with_docs.append({
                    'time': time_str,
                    'summary': summary,
                    'urls': doc_urls
                })
                # Add to all_doc_urls, but deduplicate later
                all_doc_urls.extend(doc_urls)

        # Deduplicate URLs while preserving order
        seen = set()
        unique_doc_urls = []
        for url in all_doc_urls:
            if url not in seen:
                seen.add(url)
                unique_doc_urls.append(url)
        all_doc_urls = unique_doc_urls

        # Report results
        if not meetings_with_docs:
            print(f"Found {len([e for e in events if is_real_meeting(e)])} meetings, but none have attached docs")
            return

        print(f"Found {len(meetings_with_docs)} meetings with docs:\n")

        for meeting in meetings_with_docs:
            print(f"{meeting['time']} - {meeting['summary']}")
            for url in meeting['urls']:
                # Show doc type
                if 'atlassian.net/wiki' in url:
                    doc_type = "Confluence"
                elif 'dropbox.com' in url:
                    doc_type = "Paper"
                elif 'docs.google.com/document' in url:
                    doc_type = "Google Doc"
                elif 'docs.google.com/spreadsheets' in url:
                    doc_type = "Google Sheet"
                elif 'docs.google.com/presentation' in url:
                    doc_type = "Google Slides"
                else:
                    doc_type = "Doc"
                print(f"  - {doc_type}: {url}")
            print()

        # Open all docs in Chrome (already deduplicated)
        print(f"Opening {len(all_doc_urls)} unique docs in Chrome...")
        open_urls_in_chrome(all_doc_urls)

        print("✓ Done")

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("\nMake sure you have set up Google Calendar credentials:", file=sys.stderr)
        print("  python3 tools/get_google_refresh_token.py", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
