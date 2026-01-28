"""JIRA API Client - single file implementation with CLI support."""

import os
import sys
import json
import base64
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional


class JiraClient:
    """JIRA API client using native Python stdlib."""

    def __init__(self, base_url: str, email: str, api_token: str, timeout: int = 30):
        """Initialize JIRA client with basic auth.

        Args:
            base_url: JIRA instance URL (e.g., https://company.atlassian.net)
            email: User email for authentication
            api_token: API token for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self.api_version = "3"  # JIRA Cloud API v3
        self.api_call_count = 0  # Track API calls for debugging

    def _get_auth_headers(self) -> dict:
        """Generate Basic Auth headers."""
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
        """Make HTTP request to JIRA API.

        Args:
            method: HTTP method (GET, POST, PUT)
            endpoint: API endpoint (e.g., /rest/api/3/issue/PROJ-123)
            params: URL query parameters
            json_data: JSON body data

        Returns:
            Parsed JSON response as dict

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
                # Some API calls (like update operations) return no content
                if not body or body.strip() == "":
                    return None
                return json.loads(body)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            if e.code == 404:
                raise ValueError(f"Resource not found: {url}")
            elif e.code == 401 or e.code == 403:
                raise ValueError(f"Authentication failed: {e.code}")
            elif 400 <= e.code < 500:
                raise ValueError(f"Client error {e.code}: {error_body}")
            else:
                raise RuntimeError(f"Server error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Network error: {e.reason}")

    def get_issue(self, issue_key: str) -> dict:
        """Get a single issue by key (e.g., PROJ-123).

        Args:
            issue_key: Issue key like "PROJ-123"

        Returns:
            dict with issue data including:
            - key: Issue key
            - fields: Dict with summary, description, status, assignee, etc.

        Raises:
            ValueError: If issue not found or invalid key
        """
        endpoint = f"/rest/api/{self.api_version}/issue/{issue_key}"
        return self._request("GET", endpoint)

    def get_issues_bulk(self, issue_keys: list) -> list:
        """Get multiple issues by keys.

        Args:
            issue_keys: List of issue keys like ["PROJ-123", "PROJ-124"]

        Returns:
            List of issue dicts
        """
        results = []
        for key in issue_keys:
            try:
                results.append(self.get_issue(key))
            except ValueError:
                # Skip issues that don't exist
                continue
        return results

    def query_issues(
        self,
        jql: str,
        max_results: int = 50,
        start_at: int = 0,
        fields: Optional[list] = None
    ) -> dict:
        """Query issues using JQL (JIRA Query Language).

        Args:
            jql: JQL query string (e.g., "project = PROJ AND status = Open")
            max_results: Maximum number of results to return
            start_at: Starting index for pagination
            fields: List of fields to return (default: key, summary, status, assignee, labels, issuetype, description)

        Returns:
            dict with:
            - total: Total number of matching issues
            - issues: List of issue dicts
            - startAt: Starting index
            - maxResults: Max results requested

        Example JQL queries:
            - "project = PROJ"
            - "labels = backend"
            - "parent = PROJ-100"
            - "project = PROJ AND labels = backend"
        """
        if fields is None:
            # Default fields for display
            fields = ["key", "summary", "status", "assignee", "labels", "issuetype", "description"]

        endpoint = f"/rest/api/{self.api_version}/search/jql"
        params = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at,
            "fields": ",".join(fields)
        }
        return self._request("GET", endpoint, params=params)

    def update_issue(self, issue_key: str, fields: dict) -> None:
        """Update issue fields.

        Args:
            issue_key: Issue key like "PROJ-123"
            fields: Dict of field updates, e.g.:
                {"summary": "New summary"}
                {"description": "New description"}
                {"labels": ["backend", "bug"]}
                {"assignee": {"accountId": "123456"}}

        Raises:
            ValueError: If update fails
        """
        endpoint = f"/rest/api/{self.api_version}/issue/{issue_key}"
        json_data = {"fields": fields}
        self._request("PUT", endpoint, json_data=json_data)

    def add_label(self, issue_key: str, label: str) -> None:
        """Add a label to an issue (preserving existing labels).

        Args:
            issue_key: Issue key like "PROJ-123"
            label: Label to add (e.g., "backend", "needs-review")

        Raises:
            ValueError: If issue not found or update fails
        """
        # Get current issue to fetch existing labels
        issue = self.get_issue(issue_key)
        current_labels = issue.get("fields", {}).get("labels", [])

        # Add new label if not already present
        if label not in current_labels:
            updated_labels = current_labels + [label]
            self.update_issue(issue_key, {"labels": updated_labels})

    def remove_label(self, issue_key: str, label: str) -> None:
        """Remove a label from an issue (preserving other labels).

        Args:
            issue_key: Issue key like "PROJ-123"
            label: Label to remove (e.g., "backend", "needs-review")

        Raises:
            ValueError: If issue not found or update fails
        """
        # Get current issue to fetch existing labels
        issue = self.get_issue(issue_key)
        current_labels = issue.get("fields", {}).get("labels", [])

        # Remove label if present
        if label in current_labels:
            updated_labels = [
                lbl for lbl in current_labels if lbl != label
            ]
            self.update_issue(issue_key, {"labels": updated_labels})

    def label_roadmap_hierarchy(
        self,
        root_issue_key: str,
        project: Optional[str] = None,
        dry_run: bool = False,
        limit: Optional[int] = None
    ) -> dict:
        """Label issues in hierarchy based on their roadmap prefixes.

        Traverses issue hierarchy and adds labels based on prefix ancestry.
        Issues at depth 0-2 get all ancestor prefixes as labels.
        Issues at depth 3 get root + parent + self (3 labels max).
        Issues at depth 4+ inherit their parent's labels.

        Args:
            root_issue_key: Root issue key (e.g., 'DBX-1734')
            project: Optional project filter
            dry_run: If True, preview changes without applying
            limit: Optional maximum number of issues to update

        Returns:
            Dict with stats: {
                'processed': int,
                'labeled': int,
                'skipped': int,
                'errors': int
            }

        Raises:
            ValueError: If root issue has no valid prefix
        """
        # Validate root issue has a valid prefix
        root_issue = self.get_issue(root_issue_key)
        root_summary = root_issue.get("fields", {}).get("summary", "")
        root_prefix = _extract_prefix(root_summary)

        if not root_prefix:
            raise ValueError(
                f"Root issue {root_issue_key} has no valid prefix in summary: '{root_summary}'"
            )

        # Extract root family for filtering (e.g., "C" from "C1")
        root_family = root_prefix[0]

        # Initialize tracking structures
        prefix_map = {}
        parent_map = {}
        label_map = {}
        stats = {
            'processed': 0,
            'labeled': 0,
            'skipped': 0,
            'errors': 0
        }

        # Traverse hierarchy
        for item in self.get_issue_hierarchy(root_issue_key, project):
            issue = item["issue"]
            depth = item["depth"]
            parent_key = item["parent_key"]
            issue_key = issue.get("key")
            summary = issue.get("fields", {}).get("summary", "")
            current_labels = issue.get("fields", {}).get("labels", [])

            # Store parent relationship
            if parent_key:
                parent_map[issue_key] = parent_key

            # Extract prefix from summary (only if matches root family)
            prefix = _extract_prefix(summary)
            if prefix and prefix[0] == root_family:
                prefix_map[issue_key] = prefix
            # If prefix doesn't match family or is missing, issue will inherit parent's labels

            # Build ancestry labels
            ancestry_labels = _build_ancestry_labels(
                issue_key, prefix_map, parent_map, label_map, depth
            )

            # Store computed labels
            label_map[issue_key] = ancestry_labels

            # Calculate new labels to add
            new_labels = set(ancestry_labels) - set(current_labels)

            # Skip if already has correct labels
            if not new_labels:
                if dry_run:
                    print(f"{issue_key}: {summary[:60]}...")
                    print(f"  Current labels: {current_labels}")
                    print(f"  Already has correct labels, skipped\n")
                else:
                    print(f"[{stats['processed'] + 1}] {issue_key}: Skipped (already has correct labels)")
                continue

            # Preview or apply changes
            if dry_run:
                inherited_note = " (inherited)" if depth >= 4 else ""
                print(f"{issue_key}: {summary[:60]}...")
                print(f"  Current labels: {current_labels}")
                print(f"  Labels to add: {sorted(new_labels)}{inherited_note}\n")
            else:
                # Apply labels
                errors_in_issue = []
                for label in new_labels:
                    try:
                        self.add_label(issue_key, label)
                    except Exception as e:
                        errors_in_issue.append(str(e))
                        stats['errors'] += 1

                # Print progress
                new_count = len(new_labels)
                existing = [lbl for lbl in current_labels if lbl in ancestry_labels]
                existing_str = f", already had: {', '.join(existing)}" if existing else ""
                inherited_note = ", inherited" if depth >= 4 else ""
                error_str = f" (errors: {len(errors_in_issue)})" if errors_in_issue else ""

                print(
                    f"[{stats['processed'] + 1}] {issue_key}: "
                    f"Added labels {sorted(new_labels)} ({new_count} new{existing_str}{inherited_note}){error_str}"
                )

            stats['processed'] += 1
            stats['labeled'] += 1

            # Check limit
            if limit and stats['labeled'] >= limit:
                break

        return stats

    def query_issues_by_parent(
        self,
        parent_key: str,
        max_results: int = 50,
        fields: Optional[list] = None
    ) -> list:
        """Query issues that have a specific parent (subtasks/child issues).

        Args:
            parent_key: Parent issue key like "PROJ-123"
            max_results: Maximum results to return
            fields: List of fields to return (uses default if not specified)

        Returns:
            List of issue dicts
        """
        jql = f"parent = {parent_key}"
        result = self.query_issues(jql, max_results=max_results, fields=fields)
        return result.get("issues", [])

    def query_issues_by_label(
        self,
        label: str,
        project: Optional[str] = None,
        max_results: int = 50,
        fields: Optional[list] = None
    ) -> list:
        """Query issues by label, optionally filtered by project.

        Args:
            label: Label to search for
            project: Optional project key to filter by
            max_results: Maximum results to return
            fields: List of fields to return (uses default if not specified)

        Returns:
            List of issue dicts
        """
        jql = f"labels = {label}"
        if project:
            jql = f"project = {project} AND {jql}"
        result = self.query_issues(jql, max_results=max_results, fields=fields)
        return result.get("issues", [])

    def get_issue_hierarchy(
        self,
        root_issue_key: str,
        project: Optional[str] = None,
        issue_type: Optional[str] = None,
        max_depth: int = 10,
        fields: Optional[list] = None
    ):
        """Fetch issue hierarchy as an iterator using depth-first traversal.

        Traverses both parent-child relationships and linked issues. Optionally filters
        to stay within a specified project. Children appear immediately under their parent.

        Args:
            root_issue_key: Starting issue key (e.g., "DBX-123")
            project: Optional project key to filter by (e.g., "DBX"). If None, traverses across all projects.
            issue_type: Optional issue type filter (e.g., "Story", "Epic")
            max_depth: Maximum recursion depth to prevent infinite loops
            fields: List of fields to return (uses default if not specified)

        Yields:
            dict with:
            - issue: Issue data
            - depth: Depth in hierarchy (0 = root)
            - relationship: "root", "child", or "linked"
            - parent_key: Parent issue key (or None for root)

        Examples:
            # Filter to single project
            for item in client.get_issue_hierarchy("DBX-100", project="DBX"):
                print(f"{item['issue']['key']} at depth {item['depth']}")

            # Traverse across all projects
            for item in client.get_issue_hierarchy("DBX-100"):
                print(f"{item['issue']['key']} at depth {item['depth']}")
        """
        if fields is None:
            fields = ["key", "summary", "status", "assignee", "labels", "issuetype", "description", "issuelinks", "parent"]
        else:
            # Ensure issuelinks and parent are included
            if "issuelinks" not in fields:
                fields = fields + ["issuelinks"]
            if "parent" not in fields:
                fields = fields + ["parent"]

        visited = set()
        issue_cache = {}  # Cache fetched issues to avoid redundant API calls

        def fetch_issue(issue_key: str):
            """Fetch issue from cache or API."""
            if issue_key not in issue_cache:
                try:
                    issue_cache[issue_key] = self.get_issue(issue_key)
                except ValueError:
                    issue_cache[issue_key] = None
            return issue_cache[issue_key]

        def traverse(issue_key: str, depth: int, relationship: str, parent_key: Optional[str]):
            """Recursively traverse hierarchy depth-first with batched fetching."""
            if depth > max_depth or issue_key in visited:
                return

            visited.add(issue_key)

            # Fetch the issue (from cache if available)
            issue = fetch_issue(issue_key)
            if issue is None:
                return

            # Filter by issue type if specified
            should_yield = True
            if issue_type:
                issue_type_name = issue.get("fields", {}).get("issuetype", {}).get("name", "")
                should_yield = (issue_type_name == issue_type)

            if should_yield:
                yield {
                    "issue": issue,
                    "depth": depth,
                    "relationship": relationship,
                    "parent_key": parent_key
                }

            # Collect all descendants (linked + children) to process in order
            descendants = []

            # Get linked issues first (they appear before children in output)
            linked_keys = []
            issuelinks = issue.get("fields", {}).get("issuelinks", [])
            for link in issuelinks:
                # Skip clone-type links
                link_type = link.get("type", {})
                link_type_name = link_type.get("name", "").lower()
                link_inward = link_type.get("inward", "").lower()
                link_outward = link_type.get("outward", "").lower()

                # Check if this is a clone relationship
                is_clone = (
                    "clone" in link_type_name or
                    "clone" in link_inward or
                    "clone" in link_outward
                )

                if is_clone:
                    continue  # Skip clone links

                linked_issue = link.get("inwardIssue") or link.get("outwardIssue")
                if linked_issue:
                    linked_key = linked_issue.get("key", "")
                    should_include = linked_key not in visited
                    if project:
                        should_include = should_include and linked_key.startswith(project + "-")
                    if should_include:
                        descendants.append((linked_key, "linked"))
                        linked_keys.append(linked_key)

            # Batch fetch linked issues that aren't cached
            uncached_linked = [k for k in linked_keys if k not in issue_cache]
            if uncached_linked:
                try:
                    if len(uncached_linked) == 1:
                        linked_jql = f"key = {uncached_linked[0]}"
                    else:
                        keys_str = ", ".join(uncached_linked)
                        linked_jql = f"key IN ({keys_str})"

                    linked_result = self.query_issues(linked_jql, max_results=len(uncached_linked), fields=fields)
                    for linked_issue in linked_result.get("issues", []):
                        issue_cache[linked_issue["key"]] = linked_issue
                except Exception:
                    pass

            # Query for child issues (this caches them automatically)
            children_jql = f"parent = {issue_key}"
            if project:
                children_jql += f" AND project = {project}"
            if issue_type:
                children_jql += f' AND issuetype = "{issue_type}"'

            try:
                children_result = self.query_issues(children_jql, max_results=100, fields=fields)
                children_issues = children_result.get("issues", [])

                for child in children_issues:
                    child_key = child.get("key")
                    if child_key and child_key not in visited:
                        # Cache the child issue
                        issue_cache[child_key] = child
                        descendants.append((child_key, "child"))
            except Exception:
                pass

            # Recursively traverse each descendant in order (depth-first)
            for desc_key, desc_relationship in descendants:
                yield from traverse(desc_key, depth + 1, desc_relationship, issue_key)

        # Start traversal from root
        yield from traverse(root_issue_key, 0, "root", None)


def _format_issue(issue: dict) -> str:
    """Format issue as microformat: KEY: summary [status] (assignee) [labels]"""
    key = issue.get("key", "UNKNOWN")
    fields = issue.get("fields", {})
    summary = fields.get("summary", "No summary")

    # Get status
    status = fields.get("status", {})
    status_name = status.get("name", "Unknown") if isinstance(status, dict) else "Unknown"

    # Get assignee
    assignee = fields.get("assignee", {})
    if assignee and isinstance(assignee, dict):
        assignee_name = assignee.get("displayName", assignee.get("name", "Unassigned"))
    else:
        assignee_name = "Unassigned"

    # Get labels
    labels = fields.get("labels", [])
    labels_str = f" [{', '.join(labels)}]" if labels else ""

    return f"{key}: {summary} [{status_name}] ({assignee_name}){labels_str}"


def _print_issue_details(issue: dict) -> None:
    """Print detailed issue information."""
    key = issue.get("key", "UNKNOWN")
    fields = issue.get("fields", {})

    print(f"{key}: {fields.get('summary', 'No summary')}")

    # Status
    status = fields.get("status", {})
    status_name = status.get("name", "Unknown") if isinstance(status, dict) else "Unknown"
    print(f"  Status: {status_name}")

    # Assignee
    assignee = fields.get("assignee", {})
    if assignee and isinstance(assignee, dict):
        assignee_name = assignee.get("displayName", assignee.get("name", "Unassigned"))
    else:
        assignee_name = "Unassigned"
    print(f"  Assignee: {assignee_name}")

    # Labels
    labels = fields.get("labels", [])
    if labels:
        print(f"  Labels: {', '.join(labels)}")

    # Issue type
    issue_type = fields.get("issuetype", {})
    if issue_type and isinstance(issue_type, dict):
        print(f"  Type: {issue_type.get('name', 'Unknown')}")

    # Description (first 100 chars)
    description = fields.get("description")
    if description:
        desc_preview = description[:100] + "..." if len(description) > 100 else description
        print(f"  Description: {desc_preview}")


def _print_hierarchy_item(item: dict, parent_depths: dict) -> None:
    """Print a single hierarchy item from the iterator.

    Args:
        item: Hierarchy item dict with issue, depth, relationship, parent_key
        parent_depths: Dict tracking the last child at each depth for proper tree formatting
    """
    issue = item["issue"]
    depth = item["depth"]
    relationship = item["relationship"]

    # Format the issue line
    issue_line = _format_issue(issue)

    if depth == 0:
        # Root issue - no prefix
        print(issue_line)
    else:
        # Build prefix based on depth and parent structure
        prefix = ""
        for d in range(1, depth):
            if d in parent_depths and parent_depths[d]:
                prefix += "│  "
            else:
                prefix += "   "

        # Add final connector
        if relationship == "linked":
            prefix += "├~> "
        else:
            prefix += "├─ "

        print(prefix + issue_line)


def _extract_prefix(summary: str) -> Optional[str]:
    """Extract roadmap prefix from issue summary (e.g., 'C1', 'C1.5', 'C1.5.1').

    Args:
        summary: Issue summary text

    Returns:
        Extracted prefix string or None if no valid prefix found
    """
    import re
    match = re.match(r'^([A-Z]\d+(?:\.\d+)*)\s*\.?\s*', summary)
    return match.group(1) if match else None


def _build_ancestry_labels(
    issue_key: str,
    prefix_map: dict,
    parent_map: dict,
    label_map: dict,
    depth: int
) -> list:
    """Build ancestry label chain for an issue.

    Strategy:
    - Depth 0-2: Return all ancestor prefixes
    - Depth 3: Return root + parent + self (3 labels max)
    - Depth 4+: Inherit parent's labels

    Args:
        issue_key: Current issue key
        prefix_map: Dictionary mapping issue_key → prefix
        parent_map: Dictionary mapping issue_key → parent_key
        label_map: Dictionary mapping issue_key → labels
        depth: Current depth in hierarchy

    Returns:
        List of lowercase label strings (e.g., ['c1', 'c1.5', 'c1.5.1'])
    """
    # For depth >= 4, inherit parent's labels
    if depth >= 4:
        parent_key = parent_map.get(issue_key)
        if parent_key and parent_key in label_map:
            return label_map[parent_key]  # Inherit parent's labels
        # Fallback: try to build from ancestry

    # Collect full ancestry chain from issue to root
    ancestry = []
    current_key = issue_key

    while current_key:
        if current_key in prefix_map:
            ancestry.append(prefix_map[current_key].lower())
        if current_key in parent_map:
            current_key = parent_map[current_key]
        else:
            break

    # Reverse to get root → ... → self order
    ancestry = list(reversed(ancestry))

    # Apply depth-based strategy
    if len(ancestry) > 3:
        return [ancestry[0], ancestry[-2], ancestry[-1]]  # root, parent, self
    else:
        return ancestry


def main():
    """CLI entry point for JIRA client.

    Usage:
        python3 sidekick/clients/jira.py get-issue PROJ-123
        python3 sidekick/clients/jira.py query "project = PROJ"
        python3 sidekick/clients/jira.py query-by-parent PROJ-100
        python3 sidekick/clients/jira.py query-by-label backend
        python3 sidekick/clients/jira.py update-issue PROJ-123 '{"summary": "New"}'
        python3 sidekick/clients/jira.py add-label PROJ-123 needs-review
        python3 sidekick/clients/jira.py remove-label PROJ-123 needs-review
        python3 sidekick/clients/jira.py label-roadmap DBX-1734 DBX --dry-run
        python3 sidekick/clients/jira.py label-roadmap DBX-1734 DBX --limit 10
    """
    from sidekick.config import get_jira_config

    if len(sys.argv) < 2:
        print("Usage: python3 sidekick/clients/jira.py <command> [args...]")
        print("\nCommands:")
        print("  get-issue <issue-key>")
        print("  get-issues-bulk <key1> <key2> ...")
        print("  query <jql> [max-results]")
        print("  query-by-parent <parent-key> [max-results]")
        print("  query-by-label <label> [project] [max-results]")
        print("  roadmap-hierarchy <root-issue> [project] [issue-type]")
        print("  update-issue <issue-key> <fields-json>")
        print("  add-label <issue-key> <label>")
        print("  remove-label <issue-key> <label>")
        print("  label-roadmap <root-issue> [project] [--dry-run] [--limit N]")
        sys.exit(1)

    try:
        start_time = time.time()

        config = get_jira_config()
        client = JiraClient(
            base_url=config["url"],
            email=config["email"],
            api_token=config["api_token"]
        )

        command = sys.argv[1]

        if command == "get-issue":
            issue = client.get_issue(sys.argv[2])
            _print_issue_details(issue)

        elif command == "get-issues-bulk":
            issues = client.get_issues_bulk(sys.argv[2:])
            for issue in issues:
                print(_format_issue(issue))

        elif command == "query":
            jql = sys.argv[2]
            max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            result = client.query_issues(jql, max_results=max_results)
            issues = result.get("issues", [])
            total = result.get("total", 0)
            print(f"Found {total} issues (showing {len(issues)}):")
            for issue in issues:
                print(_format_issue(issue))

        elif command == "query-by-parent":
            parent_key = sys.argv[2]
            max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            issues = client.query_issues_by_parent(parent_key, max_results)
            print(f"Subtasks of {parent_key} ({len(issues)} issues):")
            for issue in issues:
                print(_format_issue(issue))

        elif command == "query-by-label":
            label = sys.argv[2]
            project = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].isdigit() else None
            max_results = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 50
            issues = client.query_issues_by_label(label, project, max_results)
            project_str = f" in {project}" if project else ""
            print(f"Issues with label '{label}'{project_str} ({len(issues)} issues):")
            for issue in issues:
                print(_format_issue(issue))

        elif command == "roadmap-hierarchy":
            root_issue = sys.argv[2]
            # Project is optional - can be None, empty string, or "None"
            project = sys.argv[3] if len(sys.argv) > 3 else None
            if project in ("", "None", "none"):
                project = None
            issue_type = sys.argv[4] if len(sys.argv) > 4 else None

            type_str = f" (filtered to {issue_type})" if issue_type else ""
            project_str = f" in {project}" if project else " (across all projects)"
            print(f"Roadmap hierarchy for {root_issue}{project_str}{type_str}:\n")

            # Consume iterator and display results as they come
            count = 0
            parent_depths = {}
            for item in client.get_issue_hierarchy(root_issue, project, issue_type=issue_type):
                _print_hierarchy_item(item, parent_depths)
                count += 1

            print(f"\nTotal: {count} issues")

        elif command == "update-issue":
            issue_key = sys.argv[2]
            fields = json.loads(sys.argv[3])
            client.update_issue(issue_key, fields)
            print(f"Updated {issue_key}")

        elif command == "add-label":
            issue_key = sys.argv[2]
            label = sys.argv[3]
            client.add_label(issue_key, label)
            print(f"Added label '{label}' to {issue_key}")

        elif command == "remove-label":
            issue_key = sys.argv[2]
            label = sys.argv[3]
            client.remove_label(issue_key, label)
            print(f"Removed label '{label}' from {issue_key}")

        elif command == "label-roadmap":
            root_issue = sys.argv[2]

            # Parse optional project argument and flags
            project = None
            dry_run = False
            limit = None

            i = 3
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--dry-run":
                    dry_run = True
                    i += 1
                elif arg == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                elif not arg.startswith("--") and project is None:
                    project = arg
                    i += 1
                else:
                    i += 1

            if project in ("", "None", "none"):
                project = None

            mode_str = " (DRY RUN)" if dry_run else ""
            project_str = f" in {project}" if project else ""
            limit_str = f" (limit: {limit})" if limit else ""
            print(f"Labeling roadmap hierarchy for {root_issue}{project_str}{mode_str}{limit_str}:\n")

            stats = client.label_roadmap_hierarchy(root_issue, project, dry_run, limit)

            print(f"\nSummary: Processed {stats['processed']} issues, " +
                  f"labeled {stats['labeled']}, skipped {stats['skipped']}, " +
                  f"{stats['errors']} errors")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

        # Debug output
        elapsed_time = time.time() - start_time
        print(f"\n[Debug] API calls: {client.api_call_count}, Time: {elapsed_time:.2f}s", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
