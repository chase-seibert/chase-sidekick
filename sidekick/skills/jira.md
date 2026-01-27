# JIRA Skill

Command-line interface for JIRA operations.

## Configuration

Configuration is automatically loaded from `.env` file in project root.

Create a `.env` file:
```bash
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your_api_token
```

Get your JIRA API token: https://id.atlassian.com/manage-profile/security/api-tokens

**Note**: Configuration can also be set via environment variables if `.env` file is not present.

## Commands

All commands run directly with Python 3 - no installation needed.

### Get Single Issue

```bash
python3 sidekick/clients/jira.py get-issue PROJ-123
```

Displays issue details in readable format:
```
PROJ-123: Fix login bug
  Status: In Progress
  Assignee: John Doe
  Labels: backend, bug
  Type: Bug
  Description: Users cannot log in with SSO...
```

### Get Multiple Issues

```bash
python3 sidekick/clients/jira.py get-issues-bulk PROJ-123 PROJ-124 PROJ-125
```

Displays issues in one-line format:
```
PROJ-123: Fix login bug [In Progress] (John Doe) [backend, bug]
PROJ-124: Add dark mode [To Do] (Jane Smith) [frontend]
PROJ-125: Update docs [Done] (Unassigned)
```

Skips any issues that don't exist.

### Query Issues with JQL

```bash
python3 sidekick/clients/jira.py query "project = PROJ AND status = Open"
python3 sidekick/clients/jira.py query "project = PROJ AND status = Open" 10
```

Query using JQL (JIRA Query Language). Optional max results (default: 50).

Output format:
```
Found 42 issues (showing 10):
PROJ-123: Fix login bug [In Progress] (John Doe) [backend, bug]
PROJ-124: Add dark mode [To Do] (Jane Smith) [frontend]
...
```

**Common JQL Examples:**
- `project = PROJ` - All issues in project
- `status = Open` - All open issues
- `assignee = currentUser()` - Assigned to you
- `project = PROJ AND status = "In Progress"` - Specific project and status
- `labels = backend` - Issues with specific label
- `parent = PROJ-100` - Child issues of parent

### Query by Parent

```bash
python3 sidekick/clients/jira.py query-by-parent PROJ-100
python3 sidekick/clients/jira.py query-by-parent PROJ-100 20
```

Get all subtasks/child issues of a parent issue. Optional max results (default: 50).

Output format:
```
Subtasks of PROJ-100 (5 issues):
PROJ-101: Implement backend API [Done] (John Doe) [backend]
PROJ-102: Create frontend UI [In Progress] (Jane Smith) [frontend]
...
```

### Query by Label

```bash
python3 sidekick/clients/jira.py query-by-label backend
python3 sidekick/clients/jira.py query-by-label backend PROJ
python3 sidekick/clients/jira.py query-by-label backend PROJ 20
```

Get issues with a specific label. Optionally filter by project. Optional max results (default: 50).

Output format:
```
Issues with label 'backend' in PROJ (12 issues):
PROJ-123: Fix login bug [In Progress] (John Doe) [backend, bug]
PROJ-125: Update API [To Do] (Jane Smith) [backend, api]
...
```

### Update Issue

```bash
python3 sidekick/clients/jira.py update-issue PROJ-123 '{"summary": "New summary"}'
python3 sidekick/clients/jira.py update-issue PROJ-123 '{"labels": ["backend", "bug"]}'
python3 sidekick/clients/jira.py update-issue PROJ-123 '{"description": "Updated description"}'
```

Update issue fields. Provide fields as JSON object.

**Common field updates:**
- `{"summary": "text"}` - Update title
- `{"description": "text"}` - Update description
- `{"labels": ["label1", "label2"]}` - Set labels
- `{"assignee": {"accountId": "123456"}}` - Assign to user

## Python Usage

```python
from sidekick.clients.jira import JiraClient

client = JiraClient(
    base_url="https://company.atlassian.net",
    email="you@company.com",
    api_token="your-token"
)

# Get issue
issue = client.get_issue("PROJ-123")
print(issue["fields"]["summary"])

# Query with default fields (key, summary, status, assignee, labels, issuetype, description)
result = client.query_issues("project = PROJ")
for issue in result["issues"]:
    print(f"{issue['key']}: {issue['fields']['summary']}")

# Query with custom fields
result = client.query_issues(
    "project = PROJ",
    fields=["key", "summary", "priority", "created"]
)

# Query by parent
subtasks = client.query_issues_by_parent("PROJ-100")

# Query by label with custom fields
backend_issues = client.query_issues_by_label(
    "backend",
    project="PROJ",
    fields=["key", "summary", "assignee"]
)

# Update
client.update_issue("PROJ-123", {"summary": "New summary"})
```

### Common Field Names

When customizing fields, you can use any JIRA field name:
- `key` - Issue key (e.g., PROJ-123)
- `summary` - Issue title
- `description` - Issue description
- `status` - Current status
- `assignee` - Assigned user
- `reporter` - User who created the issue
- `labels` - Issue labels
- `issuetype` - Type (Bug, Story, Task, etc.)
- `priority` - Priority level
- `created` - Creation timestamp
- `updated` - Last update timestamp
- `duedate` - Due date
- `parent` - Parent issue (for subtasks)
- `project` - Project details
- `customfield_*` - Custom fields (check your JIRA instance)
