"""Confluence client - single-file implementation using Python stdlib only."""
import sys
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
import time
from typing import Optional
from pathlib import Path
from datetime import datetime


class SearchCache:
    """Manages simple YAML cache of search query to page mappings."""

    def __init__(self, cache_file: Optional[Path] = None):
        """Initialize cache with path to YAML file.

        Default: output/confluence/confluence_search_cache.yaml
        """
        if cache_file is None:
            cache_dir = Path(__file__).parent.parent.parent / "output" / "confluence"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "confluence_search_cache.yaml"

        self.cache_file = Path(cache_file)
        self._cache = self._load()

    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent lookup (lowercase, strip)."""
        return query.lower().strip()

    def _load(self) -> dict:
        """Load cache from YAML file."""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple YAML parsing (no external libs)
            cache = {}
            current_key = None

            for line in content.split('\n'):
                if line.startswith('#') or not line.strip():
                    continue

                if not line.startswith(' ') and line.endswith(':'):
                    # Top-level key (query) - strip the trailing colon
                    current_key = line[:-1].strip()
                    cache[current_key] = {}
                elif current_key and ':' in line:
                    # Nested key-value
                    key, value = line.strip().split(':', 1)
                    cache[current_key][key.strip()] = value.strip().strip('"')

            return cache
        except Exception:
            return {}

    def _save(self):
        """Save cache to YAML file."""
        lines = [
            "# Confluence Search Cache",
            "# Maps search queries to page IDs",
            "# Edit this file to add or correct search term mappings",
            ""
        ]

        for query, data in sorted(self._cache.items()):
            lines.append(f"{query}:")
            for key, value in data.items():
                lines.append(f"  {key}: \"{value}\"")
            lines.append("")

        self.cache_file.write_text('\n'.join(lines), encoding='utf-8')

    def get(self, query: str) -> Optional[dict]:
        """Get cached page for query.

        Returns:
            dict with page_id, title, space, last_used, or None
        """
        normalized = self._normalize_query(query)
        return self._cache.get(normalized)

    def set(self, query: str, page_id: str, title: str, space: str):
        """Cache a query to page mapping."""
        normalized = self._normalize_query(query)
        self._cache[normalized] = {
            "page_id": page_id,
            "title": title,
            "space": space,
            "last_used": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save()

    def clear(self):
        """Clear entire cache (delete file)."""
        if self.cache_file.exists():
            self.cache_file.unlink()
        self._cache = {}

    def show(self) -> str:
        """Return cache file contents for display."""
        if self.cache_file.exists():
            return self.cache_file.read_text()
        return "# Cache is empty"


class ConfluenceClient:
    """Confluence API client using native Python stdlib."""

    def __init__(self, base_url: str, email: str, api_token: str, timeout: int = 30):
        """Initialize Confluence client with basic auth.

        Args:
            base_url: Confluence instance URL (e.g., https://company.atlassian.net)
            email: User email for authentication
            api_token: API token for authentication (same as JIRA token)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self.api_call_count = 0  # Track API calls for debugging
        self.search_cache = SearchCache()

    def _get_auth_headers(self) -> dict:
        """Generate Basic Auth headers.

        Returns:
            dict with Authorization, Content-Type, and Accept headers
        """
        credentials = f"{self.email}:{self.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None
    ) -> dict:
        """Make HTTP request to Confluence API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Optional query parameters
            json_data: Optional JSON data for request body

        Returns:
            Response data as dict (or None for empty responses)

        Raises:
            ConnectionError: For network errors
            ValueError: For 4xx client errors
            RuntimeError: For 5xx server errors
        """
        # Build URL
        url = f"{self.base_url}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        # Prepare request
        headers = self._get_auth_headers()
        data = json.dumps(json_data).encode() if json_data else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                self.api_call_count += 1
                body = response.read().decode()

                # Handle empty response bodies
                if not body or body.strip() == "":
                    return None

                return json.loads(body)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""

            if e.code == 404:
                raise ValueError(f"Resource not found: {url}")

            elif e.code == 401 or e.code == 403:
                # Parse error details for better messaging
                error_message = "Authentication failed"
                try:
                    error_data = json.loads(error_body) if error_body else {}
                    if "message" in error_data:
                        error_message = error_data["message"]
                except (json.JSONDecodeError, KeyError):
                    pass

                raise ValueError(
                    f"Confluence authentication failed (HTTP {e.code}): {error_message}\n"
                    "Check your credentials and permissions.\n"
                    "Generate a new token at: https://id.atlassian.com/manage-profile/security/api-tokens"
                )

            elif e.code == 409:
                # Version conflict
                raise ValueError(
                    "Version conflict: Page was modified by another user. "
                    "Fetch the latest version and try again."
                )

            elif 400 <= e.code < 500:
                raise ValueError(f"Client error {e.code}: {error_body}")

            else:
                raise RuntimeError(f"Server error {e.code}: {error_body}")

        except urllib.error.URLError as e:
            raise ConnectionError(f"Network error: {e.reason}")

    # ===== Read Operations =====

    def get_page(self, page_id: str, expand: Optional[list] = None) -> dict:
        """Get page details by ID.

        Args:
            page_id: Confluence page ID
            expand: List of properties to expand
                   Default: ['body.storage', 'version', 'space']

        Returns:
            dict with:
            - id: Page ID
            - type: "page"
            - status: "current" or "trashed"
            - title: Page title
            - space: Space info (key, name) if expanded
            - version: Version info (number, when, by) if expanded
            - body: Content if expanded
            - _links: API and web links

        Raises:
            ValueError: If page not found
        """
        if expand is None:
            expand = ['body.storage', 'version', 'space']

        endpoint = f"/wiki/rest/api/content/{page_id}"
        params = {"expand": ",".join(expand)}

        return self._request("GET", endpoint, params=params)

    def get_page_content(self, page_id: str) -> str:
        """Get page content in storage format (HTML).

        Args:
            page_id: Confluence page ID

        Returns:
            HTML content string in storage format

        Raises:
            ValueError: If page not found or content not available
        """
        page = self.get_page(page_id, expand=['body.storage'])

        try:
            return page['body']['storage']['value']
        except (KeyError, TypeError):
            raise ValueError(f"Could not extract content from page {page_id}")

    # ===== Search Operations =====

    def search_pages(
        self,
        query: str,
        space: Optional[str] = None,
        limit: int = 25,
        start: int = 0
    ) -> dict:
        """Search for pages using CQL (Confluence Query Language).

        Args:
            query: Search query or CQL expression
            space: Optional space key to limit search
            limit: Maximum results to return
            start: Starting index for pagination

        Returns:
            dict with:
            - results: List of page objects
            - size: Number of results returned
            - start: Starting index
            - limit: Requested limit
            - _links: Pagination links

        Examples:
            search_pages("API Documentation")
            search_pages("type=page AND title~'API'", space="DEV")
        """
        # Check cache first
        cached = self.search_cache.get(query)
        if cached:
            # Return cached page directly
            page_id = cached["page_id"]
            try:
                page = self.get_page(page_id)
                print(f"[Using cached result for '{query}']", file=sys.stderr)
                return {"results": [page], "size": 1, "_from_cache": True}
            except (ValueError, ConnectionError):
                # Cached page no longer exists, remove from cache and search normally
                pass

        # Build CQL query
        if space:
            # If query doesn't look like CQL, make it a title search
            if "AND" not in query.upper() and "OR" not in query.upper():
                cql = f'type=page AND space={space} AND title~"{query}"'
            else:
                cql = f'type=page AND space={space} AND ({query})'
        else:
            if "AND" not in query.upper() and "OR" not in query.upper():
                cql = f'type=page AND title~"{query}"'
            else:
                cql = f'type=page AND ({query})'

        endpoint = "/wiki/rest/api/content/search"
        params = {
            "cql": cql,
            "limit": limit,
            "start": start
        }

        result = self._request("GET", endpoint, params=params)

        # Cache the first result automatically
        results = result.get("results", [])
        if results:
            first_page = results[0]
            page_id = first_page.get("id")
            title = first_page.get("title", "")
            space_info = first_page.get("space", {})
            space_key = space_info.get("key", "") if isinstance(space_info, dict) else ""

            if page_id and title:
                self.search_cache.set(query, page_id, title, space_key)
                print(f"[Cached '{query}' -> {page_id}]", file=sys.stderr)

        return result

    def get_page_by_title(self, title: str, space: str) -> Optional[dict]:
        """Get page by exact title match in a space.

        Args:
            title: Exact page title
            space: Space key (e.g., "DEV", "TEAM")

        Returns:
            Page dict or None if not found
        """
        # Use CQL for exact title match
        cql = f'type=page AND space={space} AND title="{title}"'
        endpoint = "/wiki/rest/api/content/search"
        params = {
            "cql": cql,
            "limit": 1,
            "expand": "body.storage,version,space"
        }

        result = self._request("GET", endpoint, params=params)
        results = result.get("results", [])

        return results[0] if results else None

    # ===== Write Operations =====

    def create_page(
        self,
        space: str,
        title: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> dict:
        """Create a new Confluence page.

        Args:
            space: Space key (e.g., "DEV")
            title: Page title
            content: Page content (HTML in storage format)
            parent_id: Optional parent page ID

        Returns:
            Created page dict

        Raises:
            ValueError: If page with same title exists in space or space not found
        """
        endpoint = "/wiki/rest/api/content"

        # Build request body
        json_data = {
            "type": "page",
            "title": title,
            "space": {"key": space},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }

        # Add parent if provided
        if parent_id:
            json_data["ancestors"] = [{"id": parent_id}]

        return self._request("POST", endpoint, json_data=json_data)

    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        version: int
    ) -> dict:
        """Update an existing Confluence page.

        Args:
            page_id: Page ID to update
            title: New page title
            content: New page content (HTML in storage format)
            version: Current version number (required for conflict detection)

        Returns:
            Updated page dict

        Raises:
            ValueError: If version conflict (page was modified) or page not found
        """
        endpoint = f"/wiki/rest/api/content/{page_id}"

        json_data = {
            "version": {"number": version + 1},
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }

        return self._request("PUT", endpoint, json_data=json_data)

    def update_page_safely(
        self,
        page_id: str,
        title: str,
        content: str
    ) -> dict:
        """Update page by auto-fetching current version.

        This is a convenience wrapper around update_page that automatically
        fetches the current version number before updating.

        Args:
            page_id: Page ID to update
            title: New page title
            content: New page content (HTML in storage format)

        Returns:
            Updated page dict

        Raises:
            ValueError: If page not found
        """
        # Fetch current page to get version
        page = self.get_page(page_id, expand=['version'])
        current_version = page['version']['number']

        return self.update_page(page_id, title, content, current_version)


# ===== Output Formatting =====

def _format_page(page: dict) -> str:
    """Format page as one-liner.

    Format: PAGE-ID: Title [Space] (vN)
    Example: 123456789: API Documentation [DEV] (v5)
    """
    page_id = page.get("id", "UNKNOWN")
    title = page.get("title", "No title")

    # Extract space key
    space = page.get("space", {})
    if isinstance(space, dict):
        space_key = space.get("key", "")
    else:
        space_key = ""

    # Extract version
    version = page.get("version", {})
    if isinstance(version, dict):
        version_num = version.get("number", "?")
    else:
        version_num = "?"

    space_str = f" [{space_key}]" if space_key else ""
    return f"{page_id}: {title}{space_str} (v{version_num})"


def _print_page_details(page: dict) -> None:
    """Print detailed multi-line page information."""
    page_id = page.get("id", "UNKNOWN")
    title = page.get("title", "No title")
    status = page.get("status", "unknown")

    # Space info
    space = page.get("space", {})
    if isinstance(space, dict):
        space_key = space.get("key", "Unknown")
        space_name = space.get("name", space_key)
    else:
        space_key = "Unknown"
        space_name = space_key

    # Version info
    version = page.get("version", {})
    if isinstance(version, dict):
        version_num = version.get("number", "?")
        when_info = version.get("when", "")
        # Extract date from ISO timestamp if available
        if when_info and "T" in when_info:
            when_date = when_info.split("T")[0]
        else:
            when_date = when_info or "unknown"
    else:
        version_num = "?"
        when_date = "unknown"

    # URL
    links = page.get("_links", {})
    if isinstance(links, dict):
        webui = links.get("webui", "")
        base = links.get("base", "")
        if webui:
            url = base + webui if base else webui
        else:
            url = f"/wiki/spaces/{space_key}/pages/{page_id}"
    else:
        url = f"/wiki/spaces/{space_key}/pages/{page_id}"

    print(f"{page_id}: {title}")
    print(f"  Space: {space_key} ({space_name})")
    print(f"  Version: {version_num} (updated {when_date})")
    print(f"  Status: {status}")
    print(f"  URL: {url}")

    # Content preview
    body = page.get("body", {})
    if isinstance(body, dict) and "storage" in body:
        storage = body["storage"]
        if isinstance(storage, dict) and "value" in storage:
            content = storage["value"]
            # Show first 200 chars
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"  Content preview: {preview}")


def _read_content_file(filepath: str) -> str:
    """Read content from file for page creation/update."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"Content file not found: {filepath}")
    except Exception as e:
        raise ValueError(f"Error reading content file: {e}")


def main():
    """CLI entry point for Confluence client.

    Commands:
        search <query> [--space SPACE] [--limit N]
        get-page <page-id>
        get-page-by-title <title> <space>
        read-page <page-id>
        create-page <space> <title> <content-file> [--parent PAGE-ID]
        update-page <page-id> <content-file> [--title TITLE]
        cache-show - Display search cache
        cache-clear - Clear search cache
    """
    from sidekick.config import get_atlassian_config

    if len(sys.argv) < 2:
        print("Usage: python3 -m sidekick.clients.confluence <command> [args...]")
        print("\nCommands:")
        print("  search <query> [--space SPACE] [--limit N]")
        print("  get-page <page-id>")
        print("  get-page-by-title <title> <space>")
        print("  read-page <page-id>")
        print("  create-page <space> <title> <content-file> [--parent PAGE-ID]")
        print("  update-page <page-id> <content-file> [--title TITLE]")
        print("  cache-show - Display search cache")
        print("  cache-clear - Clear search cache")
        sys.exit(1)

    try:
        start_time = time.time()

        config = get_atlassian_config()
        client = ConfluenceClient(
            base_url=config["url"],
            email=config["email"],
            api_token=config["api_token"]
        )

        command = sys.argv[1]

        if command == "search":
            if len(sys.argv) < 3:
                print("Usage: search <query> [--space SPACE] [--limit N]", file=sys.stderr)
                sys.exit(1)

            query = sys.argv[2]
            space = None
            limit = 25

            # Parse optional arguments
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--space" and i + 1 < len(sys.argv):
                    space = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            result = client.search_pages(query, space=space, limit=limit)
            pages = result.get("results", [])
            total = result.get("totalSize", len(pages))

            print(f"Found {total} pages (showing {len(pages)}):")
            for page in pages:
                print(_format_page(page))

        elif command == "get-page":
            if len(sys.argv) < 3:
                print("Usage: get-page <page-id>", file=sys.stderr)
                sys.exit(1)

            page_id = sys.argv[2]
            page = client.get_page(page_id)

            _print_page_details(page)

        elif command == "get-page-by-title":
            if len(sys.argv) < 4:
                print("Usage: get-page-by-title <title> <space>", file=sys.stderr)
                sys.exit(1)

            title = sys.argv[2]
            space = sys.argv[3]
            page = client.get_page_by_title(title, space)

            if page:
                _print_page_details(page)
            else:
                print(f"Page not found: {title} in space {space}", file=sys.stderr)
                sys.exit(1)

        elif command == "read-page":
            if len(sys.argv) < 3:
                print("Usage: read-page <page-id>", file=sys.stderr)
                sys.exit(1)

            page_id = sys.argv[2]

            # Get and print content
            content = client.get_page_content(page_id)
            print(content)

        elif command == "create-page":
            if len(sys.argv) < 5:
                print("Usage: create-page <space> <title> <content-file> [--parent PAGE-ID]", file=sys.stderr)
                sys.exit(1)

            space = sys.argv[2]
            title = sys.argv[3]
            content_file = sys.argv[4]
            parent_id = None

            # Parse optional --parent argument
            if len(sys.argv) > 5 and sys.argv[5] == "--parent" and len(sys.argv) > 6:
                parent_id = sys.argv[6]

            content = _read_content_file(content_file)
            page = client.create_page(space, title, content, parent_id)

            page_id = page.get("id")
            version = page.get("version", {}).get("number", 1)
            links = page.get("_links", {})
            base = links.get("base", "")
            webui = links.get("webui", "")
            url = base + webui if base and webui else ""

            print(f"Created page: {page_id}: {title} [{space}] (v{version})")
            if url:
                print(f"  URL: {url}")

        elif command == "update-page":
            if len(sys.argv) < 4:
                print("Usage: update-page <page-id> <content-file> [--title TITLE]", file=sys.stderr)
                sys.exit(1)

            page_id = sys.argv[2]
            content_file = sys.argv[3]
            new_title = None

            # Parse optional --title argument
            if len(sys.argv) > 4 and sys.argv[4] == "--title" and len(sys.argv) > 5:
                new_title = sys.argv[5]

            content = _read_content_file(content_file)

            # Get current page to determine title if not provided
            current_page = client.get_page(page_id, expand=['version'])
            title = new_title if new_title else current_page.get("title", "Untitled")

            # Use update_page_safely to auto-fetch version
            page = client.update_page_safely(page_id, title, content)

            version = page.get("version", {}).get("number", "?")
            space = page.get("space", {})
            space_key = space.get("key", "") if isinstance(space, dict) else ""

            links = page.get("_links", {})
            base = links.get("base", "")
            webui = links.get("webui", "")
            url = base + webui if base and webui else ""

            print(f"Updated page: {page_id}: {title} [{space_key}] (v{version})")
            if url:
                print(f"  URL: {url}")

        elif command == "cache-show":
            # Display entire cache file
            print(client.search_cache.show())

        elif command == "cache-clear":
            # Clear the cache
            client.search_cache.clear()
            print("Cache cleared")

        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)

        # Debug output
        elapsed_time = time.time() - start_time
        print(f"\n[Debug] API calls: {client.api_call_count}, Time: {elapsed_time:.2f}s", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
