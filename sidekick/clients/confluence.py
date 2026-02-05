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

        Default: memory/confluence/confluence_search_cache.yaml
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


def _add_topic_to_html(html_content: str, topic: str, section_header: str = "Next") -> str:
    """Add a topic to the top of a bulleted list in a section.

    Creates section and/or bullet list if needed. Never reorders existing sections.

    Args:
        html_content: Current page HTML content (storage format)
        topic: Topic text to add
        section_header: Header to look for or create (default: "Next")

    Returns:
        Updated HTML content with topic added
    """
    import re

    # Escape special regex characters in topic for duplicate checking
    escaped_topic = re.escape(topic)

    # Check if topic already exists as a list item
    if re.search(rf'<li[^>]*>\s*{escaped_topic}\s*</li>', html_content, re.IGNORECASE):
        print(f"[Topic '{topic}' already exists in doc]", file=sys.stderr)
        return html_content

    # Look for the section header
    header_pattern = rf'(<h1[^>]*>\s*{re.escape(section_header)}\s*</h1>)'
    header_match = re.search(header_pattern, html_content, re.IGNORECASE)

    if header_match:
        # Section exists - find the content after it
        header_end = header_match.end()

        # Find the next section header (h1) or end of document
        next_header_match = re.search(r'<h1[^>]*>', html_content[header_end:])
        section_end = header_end + next_header_match.start() if next_header_match else len(html_content)

        section_content = html_content[header_end:section_end]

        # Look for existing <ul> in this section
        ul_match = re.search(r'<ul[^>]*>', section_content)

        if ul_match:
            # Insert at the beginning of existing list
            ul_start = header_end + ul_match.end()
            new_item = f'<li>{topic}</li>'
            updated_content = html_content[:ul_start] + new_item + html_content[ul_start:]
        else:
            # No list exists - create one right after the header
            new_list = f'<ul><li>{topic}</li></ul>'
            updated_content = html_content[:header_end] + new_list + html_content[header_end:]

        return updated_content

    else:
        # Section doesn't exist - create it at the top with a new list
        new_section = f'<h1>{section_header}</h1><ul><li>{topic}</li></ul>'

        # Find first h1 tag to insert before it, or insert at beginning
        first_header_match = re.search(r'<h1[^>]*>', html_content)

        if first_header_match:
            # Insert before the first existing section
            insert_pos = first_header_match.start()
            updated_content = html_content[:insert_pos] + new_section + html_content[insert_pos:]
        else:
            # No sections exist - add at the beginning
            updated_content = new_section + html_content

        return updated_content


def _validate_oneonone_title(title: str, user_name: str, other_name: str) -> bool:
    """Check if a title matches the expected 1:1 doc format.

    Args:
        title: Page title to validate
        user_name: Current user's name
        other_name: Other person's name

    Returns:
        True if title matches expected format, False otherwise
    """
    import re

    # Normalize names for comparison (case-insensitive)
    user_lower = user_name.lower()
    other_lower = other_name.lower()

    # Normalize title for comparison
    title_lower = title.lower()

    # Expected patterns:
    # "Chase / Bob", "Chase / Bob 1:1", "Bob / Chase", "Bob / Chase 1:1"
    patterns = [
        rf'^{re.escape(user_lower)}\s*/\s*{re.escape(other_lower)}(\s+1:1)?$',
        rf'^{re.escape(other_lower)}\s*/\s*{re.escape(user_lower)}(\s+1:1)?$'
    ]

    for pattern in patterns:
        if re.match(pattern, title_lower):
            return True

    return False


def _validate_emails(emails: list) -> list:
    """Validate and normalize email addresses.

    Args:
        emails: List of email addresses to validate

    Returns:
        List of normalized (lowercase) email addresses

    Raises:
        ValueError: If any email is invalid format
    """
    import re

    if not emails:
        return []

    normalized = []
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    for email in emails:
        email = email.strip()
        if not re.match(email_pattern, email):
            raise ValueError(f"Invalid email format: {email}")
        normalized.append(email.lower())

    return normalized


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

    def get_page_from_link(self, link: str) -> dict:
        """Get page details from any Confluence link format.

        Supports multiple URL formats:
        - Short link: https://domain.atlassian.net/wiki/x/HYeVwQ
        - Full link: https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Title
        - Page ID link: https://domain.atlassian.net/wiki/pages/viewpage.action?pageId=123456

        Args:
            link: Confluence page URL in any format

        Returns:
            Page dict with id, title, content, version, space, etc.

        Raises:
            ValueError: If link cannot be parsed or page not found
        """
        import re

        # Extract page ID from various URL formats
        page_id = None

        # Format 1: Short link /wiki/x/XXXXX
        short_match = re.search(r'/wiki/x/([A-Za-z0-9_-]+)', link)
        if short_match:
            short_id = short_match.group(1)
            page_id = self._resolve_short_link(short_id)
        else:
            # Format 2: Full link /wiki/spaces/SPACE/pages/123456/Title
            full_match = re.search(r'/wiki/spaces/[^/]+/pages/(\d+)', link)
            if full_match:
                page_id = full_match.group(1)
            else:
                # Format 3: Page ID link ?pageId=123456
                pageid_match = re.search(r'pageId=(\d+)', link)
                if pageid_match:
                    page_id = pageid_match.group(1)

        if not page_id:
            raise ValueError(f"Could not extract page ID from link: {link}")

        return self.get_page(page_id)

    def get_content_from_link(self, link: str) -> str:
        """Get page content from any Confluence link format.

        This is a convenience method that combines get_page_from_link and
        extracts just the HTML content.

        Args:
            link: Confluence page URL (e.g., https://domain.atlassian.net/wiki/x/HYeVwQ)

        Returns:
            HTML content string in storage format

        Raises:
            ValueError: If link cannot be parsed or page not found

        Example:
            content = client.get_content_from_link("https://dropbox.atlassian.net/wiki/x/HYeVwQ")
        """
        page = self.get_page_from_link(link)
        try:
            return page['body']['storage']['value']
        except (KeyError, TypeError):
            raise ValueError(f"Could not extract content from page at link: {link}")

    def _resolve_short_link(self, short_id: str) -> str:
        """Resolve a Confluence short link ID to a page ID.

        Short links like /wiki/x/HYeVwQ need to be resolved to actual page IDs.
        This follows the redirect to find the real page ID.

        Args:
            short_id: Short ID from URL (e.g., "HYeVwQ")

        Returns:
            Page ID as string

        Raises:
            ValueError: If short link cannot be resolved
        """
        # The short link redirects to the full page URL
        short_url = f"{self.base_url}/wiki/x/{short_id}"

        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            """Handler that captures redirect without following it."""
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                # Store the redirect location
                self.redirect_url = newurl
                return None

        # Try to follow the redirect manually
        handler = NoRedirectHandler()
        opener = urllib.request.build_opener(handler)

        try:
            req = urllib.request.Request(short_url, headers=self._get_auth_headers())
            opener.open(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            # Redirects (301, 302, 303, 307, 308) are expected
            if hasattr(handler, 'redirect_url'):
                redirect_url = handler.redirect_url
            elif e.code in (301, 302, 303, 307, 308):
                redirect_url = e.headers.get('Location')
                if not redirect_url:
                    raise ValueError(f"No redirect location found for short link: {short_id}")
            else:
                raise ValueError(f"Failed to resolve short link {short_id}: HTTP {e.code}")
        except Exception as e:
            raise ValueError(f"Failed to resolve short link {short_id}: {e}")

        # Extract page ID from the redirect URL
        if hasattr(handler, 'redirect_url'):
            redirect_url = handler.redirect_url
            import re
            # Try to match /wiki/spaces/SPACE/pages/123456/Title
            match = re.search(r'/wiki/spaces/[^/]+/pages/(\d+)', redirect_url)
            if match:
                return match.group(1)

        raise ValueError(f"Could not extract page ID from redirect for short link: {short_id}")

    def get_page_restrictions(self, page_id: str) -> dict:
        """Get page restrictions (view/edit permissions).

        Args:
            page_id: Confluence page ID

        Returns:
            dict with restrictions info:
            - read: List of user restrictions for reading
            - update: List of user restrictions for editing

        Raises:
            ValueError: If page not found
        """
        endpoint = f"/wiki/rest/api/content/{page_id}/restriction"
        params = {"expand": "restrictions.user"}

        result = self._request("GET", endpoint, params=params)

        # Extract user emails from restrictions
        restrictions = {
            "read": [],
            "update": []
        }

        # Parse results array
        for operation_obj in result.get("results", []):
            operation = operation_obj.get("operation")
            if operation in ["read", "update"]:
                user_restrictions = operation_obj.get("restrictions", {}).get("user", {})
                if "results" in user_restrictions:
                    for user in user_restrictions["results"]:
                        email = user.get("email", "")
                        if email:
                            restrictions[operation].append(email)

        return restrictions

    def get_user_account_id(self, email: str) -> str:
        """Look up Confluence user accountId by email.

        Args:
            email: User email address

        Returns:
            Account ID string

        Raises:
            ValueError: If user not found
        """
        # Search for users - we'll need to filter by email since CQL doesn't support email directly
        endpoint = '/wiki/rest/api/search/user'
        params = {
            'cql': f'user.fullname ~ "{email.split("@")[0]}"',  # Search by name part before @
            'limit': 50
        }

        result = self._request('GET', endpoint, params=params)

        # Find user with matching email
        for item in result.get('results', []):
            user = item.get('user', {})
            if user.get('email', '').lower() == email.lower():
                account_id = user.get('accountId')
                if account_id:
                    print(f"[Found accountId for {email}: {account_id}]", file=sys.stderr)
                    return account_id

        raise ValueError(f"User not found with email: {email}")

    def set_page_restrictions(
        self,
        page_id: str,
        read_users: Optional[list] = None,
        update_users: Optional[list] = None
    ) -> dict:
        """Set page restrictions to specific users (replaces all existing restrictions).

        This method completely replaces read and/or update restrictions on a page.
        If a restriction type is not provided, it will not be modified.

        Args:
            page_id: Confluence page ID
            read_users: List of user emails to restrict READ access to (e.g., ["alice@company.com"])
                       If None, read restrictions are not modified
                       If empty list [], all read restrictions are removed
            update_users: List of user emails to restrict UPDATE (edit) access to
                         If None, update restrictions are not modified
                         If empty list [], all update restrictions are removed

        Returns:
            dict with:
            - read: List of emails now restricted for reading (or empty list if none)
            - update: List of emails now restricted for updating (or empty list if none)

        Raises:
            ValueError: If page not found, invalid email format, or user doesn't exist in instance
            ConnectionError: For network errors

        Examples:
            # Restrict read to 2 people, keep update as-is
            client.set_page_restrictions("123456", read_users=["alice@company.com", "bob@company.com"])

            # Set both read and update restrictions
            client.set_page_restrictions("123456",
                read_users=["alice@company.com"],
                update_users=["alice@company.com", "bob@company.com"]
            )

            # Remove all read restrictions (keep update as-is)
            client.set_page_restrictions("123456", read_users=[])
        """
        # Validate at least one restriction type is provided
        if read_users is None and update_users is None:
            raise ValueError("Must specify at least one of read_users or update_users")

        # Build request body as an array of operations
        json_data = []

        if read_users is not None:
            # Validate and normalize emails
            validated_read = _validate_emails(read_users)
            # Convert emails to accountIds
            account_ids = []
            for email in validated_read:
                account_id = self.get_user_account_id(email)
                account_ids.append({"accountId": account_id})

            json_data.append({
                "operation": "read",
                "restrictions": {
                    "user": account_ids
                }
            })

        if update_users is not None:
            # Validate and normalize emails
            validated_update = _validate_emails(update_users)
            # Convert emails to accountIds
            account_ids = []
            for email in validated_update:
                account_id = self.get_user_account_id(email)
                account_ids.append({"accountId": account_id})

            json_data.append({
                "operation": "update",
                "restrictions": {
                    "user": account_ids
                }
            })

        # Make POST request to set restrictions
        endpoint = f"/wiki/rest/api/content/{page_id}/restriction"
        result = self._request("POST", endpoint, json_data=json_data)

        # Parse and return simplified response
        restrictions = {
            "read": [],
            "update": []
        }

        if result:
            # POST returns results array with operation objects
            for operation_obj in result.get("results", []):
                operation = operation_obj.get("operation")
                if operation in ["read", "update"]:
                    user_restrictions = operation_obj.get("restrictions", {}).get("user", {})
                    if "results" in user_restrictions:
                        for user in user_restrictions["results"]:
                            email = user.get("email", "")
                            if email:
                                restrictions[operation].append(email)

        print(f"[Set restrictions on page {page_id}]", file=sys.stderr)
        if read_users is not None:
            print(f"  Read: {', '.join(restrictions['read']) if restrictions['read'] else 'none'}", file=sys.stderr)
        if update_users is not None:
            print(f"  Update: {', '.join(restrictions['update']) if restrictions['update'] else 'none'}", file=sys.stderr)

        return restrictions

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
            search_pages("type=page AND title ~ 'API'", space="DEV")
        """
        # Validate query
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        query = query.strip()

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
        import re
        # Check if query looks like CQL (contains AND/OR as whole words, or special operators)
        is_cql = bool(re.search(r'\b(AND|OR|NOT)\b|[~=<>]', query, re.IGNORECASE))

        if space:
            # If query doesn't look like CQL, make it a title search
            if not is_cql:
                cql = f'type = page AND space = {space} AND title ~ "{query}"'
            else:
                cql = f'type = page AND space = {space} AND ({query})'
        else:
            if not is_cql:
                cql = f'type = page AND title ~ "{query}"'
            else:
                cql = f'type = page AND ({query})'
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
        cql = f'type = page AND space = {space} AND title = "{title}"'
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

    def add_topic_to_oneonone(
        self,
        user_name: str,
        user_email: str,
        other_name: str,
        topic: str,
        section_header: str = "Next"
    ) -> dict:
        """Add a topic to a 1:1 doc with another person.

        Searches for 1:1 doc, validates it's a proper 1:1 (title format + restricted access),
        then adds the topic to the specified section.

        Args:
            user_name: Current user's name (e.g., "Chase")
            user_email: Current user's email (for validation)
            other_name: Other person's name (e.g., "Bob")
            topic: Topic text to add to the doc
            section_header: Section to add to (default: "Next")

        Returns:
            Updated page dict

        Raises:
            ValueError: If page not found, invalid format, or access issues
        """
        # Build search query - try variations of the name
        query = f"{user_name} {other_name}"

        # Search for the page
        result = self.search_pages(query, limit=5)
        pages = result.get("results", [])

        if not pages:
            raise ValueError(
                f"No 1:1 doc found for '{user_name}' and '{other_name}'. "
                f"Search query: '{query}'"
            )

        # Find the first page that matches our title format
        matching_page = None
        for page in pages:
            title = page.get("title", "")
            if _validate_oneonone_title(title, user_name, other_name):
                matching_page = page
                break

        if not matching_page:
            # Show what we found for debugging
            titles = [p.get("title", "") for p in pages]
            raise ValueError(
                f"Found pages but none match 1:1 doc title format.\n"
                f"Expected: '{user_name} / {other_name}' or '{other_name} / {user_name}' "
                f"(optionally with ' 1:1' suffix).\n"
                f"Found: {', '.join(repr(t) for t in titles)}"
            )

        page_id = matching_page["id"]
        title = matching_page["title"]

        print(f"Found 1:1 doc: {page_id}: {title}", file=sys.stderr)

        # Validate access restrictions (should be locked to 2 people)
        try:
            restrictions = self.get_page_restrictions(page_id)

            # Check read or update restrictions (either works)
            restricted_users = restrictions.get("read", []) or restrictions.get("update", [])

            if restricted_users:
                # Normalize emails for comparison
                restricted_emails_lower = [e.lower() for e in restricted_users]
                user_email_lower = user_email.lower()

                # Check that current user is in the list
                if user_email_lower not in restricted_emails_lower:
                    print(
                        f"[Warning] Current user ({user_email}) not in page restrictions. "
                        f"Restricted to: {', '.join(restricted_users)}",
                        file=sys.stderr
                    )

                # Check that there are exactly 2 people
                if len(restricted_users) != 2:
                    print(
                        f"[Warning] Expected 2 users in restrictions, found {len(restricted_users)}: "
                        f"{', '.join(restricted_users)}",
                        file=sys.stderr
                    )
            else:
                print("[Warning] No page restrictions found (page may be public)", file=sys.stderr)

        except Exception as e:
            print(f"[Warning] Could not verify page restrictions: {e}", file=sys.stderr)

        # Get current content
        content = self.get_page_content(page_id)

        # Add topic to the section
        updated_content = _add_topic_to_html(content, topic, section_header)

        # Check if content actually changed
        if updated_content == content:
            print("No changes needed (topic already exists or no modification)", file=sys.stderr)
            return matching_page

        # Update the page
        updated_page = self.update_page_safely(page_id, title, updated_content)

        print(f"Added topic to {section_header} section", file=sys.stderr)

        return updated_page

    def create_oneonone_doc(
        self,
        user_name: str,
        user_email: str,
        person_name: str,
        person_email: str,
        parent_id: str,
        paper_doc_url: Optional[str] = None,
        template_link: Optional[str] = None
    ) -> dict:
        """Create a new 1:1 doc with restricted access.

        Creates a Confluence page with:
        - Title: "user_name / person_name 1:1"
        - Content from template (if provided) or blank page
        - Restricted access to user_email and person_email only

        Args:
            user_name: Current user's name (e.g., "Alice")
            user_email: Current user's email for restrictions
            person_name: Other person's name (e.g., "Bob")
            person_email: Other person's email for restrictions
            parent_id: Parent folder ID in Confluence
            paper_doc_url: Optional URL to old Paper 1:1 doc (used as variable in template)
            template_link: Optional Confluence link to copy content from

        Returns:
            Created page dict with URL

        Raises:
            ValueError: If page creation or restriction setting fails
        """
        # Generate title
        title = f"{user_name} / {person_name} 1:1"

        # Generate content
        if template_link:
            # Fetch content from template page
            print(f"Fetching template from: {template_link}", file=sys.stderr)
            content = self.get_content_from_link(template_link)

            # Replace template variables if paper_doc_url is provided
            if paper_doc_url:
                content = content.replace("{PAPER_DOC_URL}", paper_doc_url)
                content = content.replace("{PERSON_NAME}", person_name)
        else:
            # Create blank page
            content = "<p>Please add agenda items as you think of them.</p>"

        # Create page
        print(f"Creating 1:1 doc: {title}", file=sys.stderr)
        page = self.create_page(
            space="TNC",
            title=title,
            content=content,
            parent_id=parent_id
        )

        page_id = page.get("id")
        if not page_id:
            raise ValueError("Failed to create page: No page ID returned")

        print(f"Created page {page_id}", file=sys.stderr)

        # Set restrictions
        print(f"Setting restrictions to {user_email} and {person_email}", file=sys.stderr)
        self.set_page_restrictions(
            page_id,
            read_users=[user_email, person_email],
            update_users=[user_email, person_email]
        )

        print("Restrictions set successfully", file=sys.stderr)

        # Return page with URL
        return page


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
        get-page-from-link <url>
        get-content-from-link <url>
        read-page <page-id>
        create-page <space> <title> <content-file> [--parent PAGE-ID]
        update-page <page-id> <content-file> [--title TITLE]
        add-topic-to-oneonone <person-name> <topic> [--section SECTION]
        create-oneonone <name> <email> <parent-id> [--paper-url URL] [--template URL]
        set-page-restrictions <page-id> [--read EMAIL1,EMAIL2] [--update EMAIL1,EMAIL2]
        cache-show - Display search cache
        cache-clear - Clear search cache
    """
    from sidekick.config import get_atlassian_config, get_user_config

    if len(sys.argv) < 2:
        print("Usage: python3 -m sidekick.clients.confluence <command> [args...]")
        print("\nCommands:")
        print("  search <query> [--space SPACE] [--limit N]")
        print("  get-page <page-id>")
        print("  get-page-by-title <title> <space>")
        print("  get-page-from-link <url>")
        print("  get-content-from-link <url>")
        print("  read-page <page-id>")
        print("  create-page <space> <title> <content-file> [--parent PAGE-ID]")
        print("  update-page <page-id> <content-file> [--title TITLE]")
        print("  add-topic-to-oneonone <person-name> <topic> [--section SECTION]")
        print("  create-oneonone <name> <email> <parent-id> [--paper-url URL] [--template URL]")
        print("  set-page-restrictions <page-id> [--read EMAIL1,EMAIL2] [--update EMAIL1,EMAIL2]")
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

        elif command == "get-page-from-link":
            if len(sys.argv) < 3:
                print("Usage: get-page-from-link <url>", file=sys.stderr)
                sys.exit(1)

            link = sys.argv[2]
            page = client.get_page_from_link(link)
            _print_page_details(page)

        elif command == "get-content-from-link":
            if len(sys.argv) < 3:
                print("Usage: get-content-from-link <url>", file=sys.stderr)
                sys.exit(1)

            link = sys.argv[2]
            content = client.get_content_from_link(link)
            print(content)

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

        elif command == "add-topic-to-oneonone":
            if len(sys.argv) < 4:
                print("Usage: add-topic-to-oneonone <person-name> <topic> [--section SECTION]", file=sys.stderr)
                sys.exit(1)

            person_name = sys.argv[2]
            topic = sys.argv[3]
            section = "Next"

            # Parse optional --section argument
            if len(sys.argv) > 4 and sys.argv[4] == "--section" and len(sys.argv) > 5:
                section = sys.argv[5]

            # Get user config
            user_config = get_user_config()
            user_name = user_config["name"]
            user_email = user_config["email"]

            # Add topic to 1:1 doc
            page = client.add_topic_to_oneonone(
                user_name=user_name,
                user_email=user_email,
                other_name=person_name,
                topic=topic,
                section_header=section
            )

            # Display result
            page_id = page.get("id")
            title = page.get("title", "")
            version = page.get("version", {}).get("number", "?")

            print(f"\nUpdated 1:1 doc: {page_id}: {title} (v{version})")

            # Show URL if available
            links = page.get("_links", {})
            base = links.get("base", "")
            webui = links.get("webui", "")
            if base and webui:
                url = base + webui
                print(f"  URL: {url}")

        elif command == "create-oneonone":
            if len(sys.argv) < 5:
                print("Usage: create-oneonone <name> <email> <parent-id> [--paper-url URL] [--template URL]", file=sys.stderr)
                sys.exit(1)

            person_name = sys.argv[2]
            person_email = sys.argv[3]
            parent_id = sys.argv[4]
            paper_doc_url = None
            template_link = None

            # Parse optional arguments
            i = 5
            while i < len(sys.argv):
                if sys.argv[i] == "--paper-url" and i + 1 < len(sys.argv):
                    paper_doc_url = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--template" and i + 1 < len(sys.argv):
                    template_link = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1

            # Get user config
            user_config = get_user_config()
            user_name = user_config["name"]
            user_email = user_config["email"]

            # Create 1:1 doc
            page = client.create_oneonone_doc(
                user_name=user_name,
                user_email=user_email,
                person_name=person_name,
                person_email=person_email,
                parent_id=parent_id,
                paper_doc_url=paper_doc_url,
                template_link=template_link
            )

            # Display result
            page_id = page.get("id")
            title = page.get("title", "")
            version = page.get("version", {}).get("number", 1)
            links = page.get("_links", {})
            base = links.get("base", "")
            webui = links.get("webui", "")
            url = base + webui if base and webui else ""

            print(f"\nCreated 1:1 doc: {page_id}: {title} (v{version})")
            if url:
                print(f"  URL: {url}")

        elif command == "set-page-restrictions":
            if len(sys.argv) < 3:
                print("Usage: set-page-restrictions <page-id> [--read EMAIL1,EMAIL2] [--update EMAIL1,EMAIL2]", file=sys.stderr)
                sys.exit(1)

            page_id = sys.argv[2]
            read_users = None
            update_users = None

            # Parse optional arguments
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--read" and i + 1 < len(sys.argv):
                    # Parse comma-separated emails
                    read_arg = sys.argv[i + 1]
                    read_users = [e.strip() for e in read_arg.split(",")] if read_arg else []
                    i += 2
                elif sys.argv[i] == "--update" and i + 1 < len(sys.argv):
                    # Parse comma-separated emails
                    update_arg = sys.argv[i + 1]
                    update_users = [e.strip() for e in update_arg.split(",")] if update_arg else []
                    i += 2
                else:
                    i += 1

            # Set restrictions
            restrictions = client.set_page_restrictions(page_id, read_users, update_users)

            # Display result
            print(f"\nRestrictions set for page {page_id}:")
            print(f"  Read: {', '.join(restrictions['read']) if restrictions['read'] else 'none'}")
            print(f"  Update: {', '.join(restrictions['update']) if restrictions['update'] else 'none'}")

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
