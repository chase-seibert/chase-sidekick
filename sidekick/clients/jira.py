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
                return json.loads(response.read().decode())
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
        project: str,
        issue_type: Optional[str] = None,
        max_depth: int = 10,
        fields: Optional[list] = None
    ):
        """Recursively fetch issue hierarchy as an iterator that yields results.

        Traverses both parent-child relationships and linked issues, staying within
        the specified project. Yields results as they're fetched for better performance
        and immediate feedback.

        Args:
            root_issue_key: Starting issue key (e.g., "DBX-123")
            project: Project key to filter by (e.g., "DBX")
            issue_type: Optional issue type filter (e.g., "Story", "Epic")
            max_depth: Maximum recursion depth to prevent infinite loops
            fields: List of fields to return (uses default if not specified)

        Yields:
            dict with:
            - issue: Issue data
            - depth: Depth in hierarchy (0 = root)
            - relationship: "root", "child", or "linked"
            - parent_key: Parent issue key (or None for root)

        Example:
            for item in client.get_issue_hierarchy("DBX-100", "DBX"):
                print(f"{item['issue']['key']} at depth {item['depth']}")
        """
        visited = set()

        def _traverse(issue_key: str, depth: int, relationship: str, parent_key: Optional[str]):
            """Internal recursive generator."""
            if depth > max_depth or issue_key in visited:
                return

            visited.add(issue_key)

            # Get issue
            try:
                issue = self.get_issue(issue_key)
            except ValueError:
                return

            # Filter by issue type if specified
            if issue_type:
                issue_type_name = issue.get("fields", {}).get("issuetype", {}).get("name", "")
                if issue_type_name != issue_type:
                    # Skip this issue but still check children/links
                    pass
                else:
                    # Yield this issue
                    yield {
                        "issue": issue,
                        "depth": depth,
                        "relationship": relationship,
                        "parent_key": parent_key
                    }
            else:
                # No filter, yield this issue
                yield {
                    "issue": issue,
                    "depth": depth,
                    "relationship": relationship,
                    "parent_key": parent_key
                }

            # Build JQL to find children
            jql = f"parent = {issue_key} AND project = {project}"
            if issue_type:
                jql += f' AND issuetype = "{issue_type}"'

            # Get children
            children_result = self.query_issues(jql, max_results=100, fields=fields)
            children_issues = children_result.get("issues", [])

            # Traverse children
            for child in children_issues:
                child_key = child.get("key")
                if child_key and child_key not in visited:
                    yield from _traverse(child_key, depth + 1, "child", issue_key)

            # Extract and traverse linked issues
            issuelinks = issue.get("fields", {}).get("issuelinks", [])
            for link in issuelinks:
                linked_issue = link.get("inwardIssue") or link.get("outwardIssue")
                if linked_issue:
                    linked_key = linked_issue.get("key", "")
                    # Only include if in the same project
                    if linked_key.startswith(project + "-") and linked_key not in visited:
                        yield from _traverse(linked_key, depth + 1, "linked", issue_key)

        # Start traversal from root
        yield from _traverse(root_issue_key, 0, "root", None)


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


def main():
    """CLI entry point for JIRA client.

    Usage:
        python3 sidekick/clients/jira.py get-issue PROJ-123
        python3 sidekick/clients/jira.py query "project = PROJ"
        python3 sidekick/clients/jira.py query-by-parent PROJ-100
        python3 sidekick/clients/jira.py query-by-label backend
        python3 sidekick/clients/jira.py update-issue PROJ-123 '{"summary": "New"}'
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
        print("  roadmap-hierarchy <root-issue> <project> [issue-type]")
        print("  update-issue <issue-key> <fields-json>")
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
            project = sys.argv[3]
            issue_type = sys.argv[4] if len(sys.argv) > 4 else None

            type_str = f" (filtered to {issue_type})" if issue_type else ""
            print(f"Roadmap hierarchy for {root_issue} in {project}{type_str}:\n")

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
