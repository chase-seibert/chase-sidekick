"""Chrome History Client - single file implementation with CLI support."""

import os
import sys
import sqlite3
import shutil
import tempfile
import time
from datetime import datetime, timezone
from typing import Optional, List


# Chrome timestamp constant
CHROME_EPOCH_OFFSET = 11644473600  # Seconds between 1601-01-01 and 1970-01-01


class ChromeClient:
    """Chrome History API client using native Python stdlib."""

    def __init__(self, profile_path: Optional[str] = None, timeout: int = 30):
        """Initialize Chrome client.

        Args:
            profile_path: Path to Chrome profile directory
                         (defaults to OS-specific Default profile)
            timeout: Database operation timeout in seconds
        """
        self.profile_path = profile_path or self._get_default_profile_path()
        self.timeout = timeout
        self.query_count = 0  # Track queries for debugging

    def _get_default_profile_path(self) -> str:
        """Get default Chrome profile path for current OS.

        Returns:
            Path to Chrome Default profile directory

        Raises:
            RuntimeError: If Chrome profile not found
        """
        home = os.path.expanduser("~")

        if sys.platform == "darwin":  # macOS
            path = os.path.join(home, "Library", "Application Support", "Google", "Chrome", "Default")
        elif sys.platform.startswith("linux"):  # Linux
            path = os.path.join(home, ".config", "google-chrome", "Default")
        elif sys.platform == "win32":  # Windows
            path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data", "Default")
        else:
            raise RuntimeError(f"Unsupported platform: {sys.platform}")

        if not os.path.exists(path):
            raise RuntimeError(
                f"Chrome profile not found at: {path}\n"
                f"Expected location ({sys.platform}): {path}\n"
                f"Specify custom profile with --profile or provide profile_path parameter"
            )

        return path

    def _get_history_db_path(self) -> str:
        """Get path to Chrome History database.

        Returns:
            Path to History database file
        """
        return os.path.join(self.profile_path, "History")

    def _copy_database(self) -> str:
        """Copy History database to temp location (Chrome locks it while running).

        Returns:
            Path to temporary database copy

        Raises:
            FileNotFoundError: If History database doesn't exist
            RuntimeError: If copy fails
        """
        history_path = self._get_history_db_path()

        if not os.path.exists(history_path):
            raise FileNotFoundError(
                f"Chrome History database not found: {history_path}\n"
                "Make sure Chrome has been run at least once and browsing history is enabled."
            )

        try:
            # Create temp file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
            os.close(temp_fd)

            # Copy database
            shutil.copy2(history_path, temp_path)

            return temp_path
        except Exception as e:
            raise RuntimeError(f"Failed to copy History database: {e}")

    def _chrome_timestamp_to_datetime(self, timestamp: int) -> datetime:
        """Convert Chrome timestamp to Python datetime.

        Chrome uses microseconds since 1601-01-01 00:00:00 UTC (WebKit epoch).

        Args:
            timestamp: Chrome timestamp (microseconds since 1601-01-01)

        Returns:
            Python datetime object in UTC
        """
        unix_timestamp = (timestamp / 1_000_000) - CHROME_EPOCH_OFFSET
        return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime as human-readable string in local timezone.

        Args:
            dt: datetime object (UTC)

        Returns:
            Formatted string: "2026-02-04 14:30:00 PST"
        """
        # Convert to local timezone
        local_dt = dt.astimezone()

        # Format: YYYY-MM-DD HH:MM:SS TZ
        # Get timezone abbreviation (e.g., PST, EST)
        tz_name = local_dt.strftime("%Z")

        return f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"

    def _parse_date_to_chrome_timestamp(self, date_str: str) -> int:
        """Parse ISO date string to Chrome timestamp.

        Args:
            date_str: ISO date string (YYYY-MM-DD)

        Returns:
            Chrome timestamp (microseconds since 1601-01-01)

        Raises:
            ValueError: If date format invalid
        """
        try:
            # Parse as date at midnight UTC
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            dt = dt.replace(tzinfo=timezone.utc)

            # Convert to Chrome timestamp
            unix_timestamp = dt.timestamp()
            chrome_timestamp = int((unix_timestamp + CHROME_EPOCH_OFFSET) * 1_000_000)

            return chrome_timestamp
        except ValueError as e:
            raise ValueError(
                f"Invalid date format: {date_str}\n"
                "Use ISO format: YYYY-MM-DD (e.g., 2026-02-04)"
            )

    def _query_history(
        self,
        sql: str,
        params: tuple = ()
    ) -> List[dict]:
        """Execute SQL query on History database.

        Args:
            sql: SQL query string
            params: Query parameters (for parameterized queries)

        Returns:
            List of result dicts

        Raises:
            RuntimeError: If database query fails
        """
        temp_path = None
        try:
            # Copy database to temp location
            temp_path = self._copy_database()

            # Connect to database
            conn = sqlite3.connect(temp_path, timeout=self.timeout)
            conn.row_factory = sqlite3.Row  # Return rows as dicts

            cursor = conn.cursor()
            cursor.execute(sql, params)
            self.query_count += 1

            # Fetch all results and convert to dicts
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))

            conn.close()

            return results
        except sqlite3.Error as e:
            raise RuntimeError(f"Database query failed: {e}")
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass  # Best effort cleanup

    def list_history(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100,
        url_filter: Optional[str] = None
    ) -> List[dict]:
        """Query Chrome history within date/time range.

        Args:
            start_date: Start date (ISO format YYYY-MM-DD) or None for beginning
            end_date: End date (ISO format YYYY-MM-DD) or None for now
            max_results: Maximum number of results
            url_filter: Optional URL filter (SQL LIKE pattern, e.g., "%jira%")

        Returns:
            List of history dicts with keys:
            - url: URL string
            - title: Page title
            - visit_count: Number of visits
            - last_visit_time: Human-readable timestamp (local timezone)
            - last_visit_iso: ISO 8601 timestamp
            - last_visit_chrome: Raw Chrome timestamp
        """
        # Build WHERE clause dynamically based on optional parameters
        where_clauses = ["hidden = 0"]  # Always exclude hidden entries
        params = []

        if start_date:
            chrome_start = self._parse_date_to_chrome_timestamp(start_date)
            where_clauses.append("last_visit_time >= ?")
            params.append(chrome_start)

        if end_date:
            chrome_end = self._parse_date_to_chrome_timestamp(end_date)
            # Add one day to include the entire end date
            chrome_end += 86400 * 1_000_000  # 86400 seconds = 1 day
            where_clauses.append("last_visit_time <= ?")
            params.append(chrome_end)

        if url_filter:
            where_clauses.append("url LIKE ?")
            params.append(url_filter)

        where_clause = " AND ".join(where_clauses)
        params.append(max_results)

        sql = f"""
            SELECT url, title, visit_count, last_visit_time
            FROM urls
            WHERE {where_clause}
            ORDER BY last_visit_time DESC
            LIMIT ?
        """

        results = self._query_history(sql, tuple(params))

        # Post-process results to add formatted timestamps
        for result in results:
            chrome_ts = result['last_visit_time']
            dt = self._chrome_timestamp_to_datetime(chrome_ts)
            result['last_visit_time'] = self._format_datetime(dt)
            result['last_visit_iso'] = dt.isoformat()
            result['last_visit_chrome'] = chrome_ts

        return results

    def search_history(
        self,
        query: str,
        max_results: int = 100
    ) -> List[dict]:
        """Search history by URL or title.

        Args:
            query: Search string (matches URL or title)
            max_results: Maximum results

        Returns:
            List of history dicts (same format as list_history)
        """
        sql = """
            SELECT url, title, visit_count, last_visit_time
            FROM urls
            WHERE (url LIKE ? OR title LIKE ?)
                AND hidden = 0
            ORDER BY last_visit_time DESC
            LIMIT ?
        """

        search_pattern = f"%{query}%"
        results = self._query_history(sql, (search_pattern, search_pattern, max_results))

        # Post-process results to add formatted timestamps
        for result in results:
            chrome_ts = result['last_visit_time']
            dt = self._chrome_timestamp_to_datetime(chrome_ts)
            result['last_visit_time'] = self._format_datetime(dt)
            result['last_visit_iso'] = dt.isoformat()
            result['last_visit_chrome'] = chrome_ts

        return results

    def list_confluence_pages(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100
    ) -> List[dict]:
        """List Confluence pages visited.

        Args:
            start_date: Start date (ISO format YYYY-MM-DD) or None
            end_date: End date (ISO format YYYY-MM-DD) or None
            max_results: Maximum results

        Returns:
            List of history dicts
        """
        return self.list_history(
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
            url_filter="%atlassian.net/wiki%"
        )

    def list_paper_docs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100
    ) -> List[dict]:
        """List Dropbox Paper docs visited.

        Args:
            start_date: Start date (ISO format YYYY-MM-DD) or None
            end_date: End date (ISO format YYYY-MM-DD) or None
            max_results: Maximum results

        Returns:
            List of history dicts
        """
        # Match both new format (/scl/fi/) and old format (paper in URL)
        # Note: We can only use one LIKE pattern in SQL, so we'll filter for the common pattern
        # and then do post-filtering in Python for full accuracy
        results = self.list_history(
            start_date=start_date,
            end_date=end_date,
            max_results=max_results * 2,  # Get extra to account for filtering
            url_filter="%dropbox.com%"
        )

        # Filter for Paper docs specifically
        paper_results = [
            r for r in results
            if "/scl/fi/" in r['url'] or "paper" in r['url'].lower()
        ]

        return paper_results[:max_results]

    def list_jira_issues(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100
    ) -> List[dict]:
        """List JIRA issues visited.

        Args:
            start_date: Start date (ISO format YYYY-MM-DD) or None
            end_date: End date (ISO format YYYY-MM-DD) or None
            max_results: Maximum results

        Returns:
            List of history dicts
        """
        return self.list_history(
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
            url_filter="%atlassian.net/browse/%"
        )

    def list_google_sheets(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100
    ) -> List[dict]:
        """List Google Sheets visited.

        Args:
            start_date: Start date (ISO format YYYY-MM-DD) or None
            end_date: End date (ISO format YYYY-MM-DD) or None
            max_results: Maximum results

        Returns:
            List of history dicts
        """
        return self.list_history(
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
            url_filter="%docs.google.com/spreadsheets%"
        )

    def list_google_searches(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100
    ) -> List[dict]:
        """List Google searches performed.

        Args:
            start_date: Start date (ISO format YYYY-MM-DD) or None
            end_date: End date (ISO format YYYY-MM-DD) or None
            max_results: Maximum results

        Returns:
            List of history dicts
        """
        # Match google.com/search or any google domain with /search
        results = self.list_history(
            start_date=start_date,
            end_date=end_date,
            max_results=max_results * 2,  # Get extra to account for filtering
            url_filter="%google.%/search%"
        )

        # Filter more precisely (handle google.com, google.ca, etc.)
        search_results = [
            r for r in results
            if "/search" in r['url'] and "google." in r['url']
        ]

        return search_results[:max_results]


def _format_history_entry(entry: dict) -> str:
    """Format history entry as microformat line.

    Args:
        entry: History entry dict

    Returns:
        Formatted string: "timestamp | title | url (visited N times)"
    """
    timestamp = entry['last_visit_time']
    title = entry.get('title') or 'No title'
    url = entry['url']
    visit_count = entry['visit_count']

    # Truncate title if too long
    if len(title) > 60:
        title = title[:57] + "..."

    # Truncate URL if too long
    if len(url) > 80:
        url = url[:77] + "..."

    visits = f"visited {visit_count} time" if visit_count == 1 else f"visited {visit_count} times"
    return f"{timestamp} | {title} | {url} ({visits})"


def _print_history_details(entry: dict) -> None:
    """Print detailed history entry information."""
    print(f"URL: {entry['url']}")
    print(f"Title: {entry.get('title') or 'No title'}")
    print(f"Visit Count: {entry['visit_count']}")
    print(f"Last Visit: {entry['last_visit_time']}")
    print(f"Last Visit ISO: {entry['last_visit_iso']}")


def main():
    """CLI entry point for Chrome client.

    Usage:
        python3 -m sidekick.clients.chrome list-history [options]
        python3 -m sidekick.clients.chrome search <query> [options]
        python3 -m sidekick.clients.chrome list-confluence [options]
        python3 -m sidekick.clients.chrome list-paper [options]
        python3 -m sidekick.clients.chrome list-jira [options]
        python3 -m sidekick.clients.chrome list-sheets [options]
        python3 -m sidekick.clients.chrome list-searches [options]

    Options:
        --start-date YYYY-MM-DD    Start date (optional)
        --end-date YYYY-MM-DD      End date (optional)
        --max-results N            Maximum results (default: 100)
        --profile PATH             Chrome profile path (optional)
    """

    if len(sys.argv) < 2:
        print("Usage: python3 -m sidekick.clients.chrome <command> [args...]")
        print("\nCommands:")
        print("  list-history [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N] [--profile PATH]")
        print("  search <query> [--max-results N] [--profile PATH]")
        print("  list-confluence [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N] [--profile PATH]")
        print("  list-paper [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N] [--profile PATH]")
        print("  list-jira [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N] [--profile PATH]")
        print("  list-sheets [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N] [--profile PATH]")
        print("  list-searches [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N] [--profile PATH]")
        sys.exit(1)

    try:
        start_time = time.time()

        # Parse command
        command = sys.argv[1]

        # Parse options
        profile_path = None
        start_date = None
        end_date = None
        max_results = 100
        query = None

        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]

            if arg == "--profile" and i + 1 < len(sys.argv):
                profile_path = sys.argv[i + 1]
                i += 2
            elif arg == "--start-date" and i + 1 < len(sys.argv):
                start_date = sys.argv[i + 1]
                i += 2
            elif arg == "--end-date" and i + 1 < len(sys.argv):
                end_date = sys.argv[i + 1]
                i += 2
            elif arg == "--max-results" and i + 1 < len(sys.argv):
                max_results = int(sys.argv[i + 1])
                i += 2
            elif not arg.startswith("--") and command == "search" and query is None:
                query = arg
                i += 1
            else:
                i += 1

        # Initialize client
        client = ChromeClient(profile_path=profile_path)

        # Execute command
        if command == "list-history":
            results = client.list_history(
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
            print(f"Found {len(results)} history entries:\n")
            for entry in results:
                print(_format_history_entry(entry))

        elif command == "search":
            if not query:
                print("Error: search command requires a query argument", file=sys.stderr)
                sys.exit(1)

            results = client.search_history(query, max_results=max_results)
            print(f"Found {len(results)} matching entries:\n")
            for entry in results:
                print(_format_history_entry(entry))

        elif command == "list-confluence":
            results = client.list_confluence_pages(
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
            print(f"Found {len(results)} Confluence pages:\n")
            for entry in results:
                print(_format_history_entry(entry))

        elif command == "list-paper":
            results = client.list_paper_docs(
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
            print(f"Found {len(results)} Paper docs:\n")
            for entry in results:
                print(_format_history_entry(entry))

        elif command == "list-jira":
            results = client.list_jira_issues(
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
            print(f"Found {len(results)} JIRA issues:\n")
            for entry in results:
                print(_format_history_entry(entry))

        elif command == "list-sheets":
            results = client.list_google_sheets(
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
            print(f"Found {len(results)} Google Sheets:\n")
            for entry in results:
                print(_format_history_entry(entry))

        elif command == "list-searches":
            results = client.list_google_searches(
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
            print(f"Found {len(results)} Google searches:\n")
            for entry in results:
                print(_format_history_entry(entry))

        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)

        # Debug output
        elapsed_time = time.time() - start_time
        print(f"\n[Debug] Queries: {client.query_count}, Time: {elapsed_time:.2f}s", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
