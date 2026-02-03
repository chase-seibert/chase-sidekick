"""OmniFocus client - single-file implementation using Python stdlib only."""
import sys
import json
import subprocess
import time
from datetime import datetime


class OmniFocusClient:
    """OmniFocus API client using JXA (JavaScript for Automation) and AppleScript."""

    def __init__(self, timeout: int = 30, default_project: str = None, default_tag: str = None):
        """Initialize OmniFocus client.

        Args:
            timeout: Script execution timeout in seconds
            default_project: Default project name for new tasks
            default_tag: Default tag name for new tasks

        Raises:
            RuntimeError: If OmniFocus is not available
        """
        self.timeout = timeout
        self.default_project = default_project
        self.default_tag = default_tag
        self.script_call_count = 0  # Track script calls for debugging

        # Check if OmniFocus is available
        self._check_omnifocus_available()

    def _check_omnifocus_available(self) -> bool:
        """Check if OmniFocus is installed and accessible.

        Returns:
            True if available

        Raises:
            RuntimeError: If OmniFocus not available
        """
        try:
            # Try to get OmniFocus version via JXA
            script = 'Application("OmniFocus").version()'
            self._execute_jxa(script)
            return True
        except Exception as e:
            raise RuntimeError(
                "OmniFocus not available. Is it installed?\n"
                "This client requires OmniFocus to be installed on macOS.\n"
                "Download from: https://www.omnigroup.com/omnifocus\n"
                f"Error: {e}"
            )

    def _execute_jxa(self, script: str) -> str:
        """Execute JXA (JavaScript for Automation) script via osascript.

        Args:
            script: JavaScript code to execute

        Returns:
            Script output as string

        Raises:
            RuntimeError: If OmniFocus not available
            ConnectionError: If script execution fails
            ValueError: If script returns error
        """
        self.script_call_count += 1

        try:
            result = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()

                # Check for common errors
                if "Application can't be found" in error_msg:
                    raise RuntimeError(
                        "OmniFocus not available. Is it installed?\n"
                        "Download from: https://www.omnigroup.com/omnifocus"
                    )
                elif "not allowed" in error_msg or "permission" in error_msg.lower():
                    raise RuntimeError(
                        "OmniFocus automation permission denied.\n"
                        "Grant automation permissions in:\n"
                        "System Settings > Privacy & Security > Automation"
                    )
                else:
                    raise ValueError(f"OmniFocus script failed: {error_msg}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise ConnectionError(f"OmniFocus script timeout after {self.timeout}s")
        except FileNotFoundError:
            raise RuntimeError(
                "osascript command not found. This client requires macOS."
            )
        except Exception as e:
            if isinstance(e, (RuntimeError, ConnectionError, ValueError)):
                raise
            raise ConnectionError(f"Script execution failed: {e}")

    def _execute_applescript(self, script: str) -> str:
        """Execute AppleScript via osascript.

        Args:
            script: AppleScript code to execute

        Returns:
            Script output as string

        Raises:
            RuntimeError: If OmniFocus not available
            ConnectionError: If script execution fails
            ValueError: If script returns error
        """
        self.script_call_count += 1

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()

                # Check for common errors
                if "Application can't be found" in error_msg:
                    raise RuntimeError(
                        "OmniFocus not available. Is it installed?\n"
                        "Download from: https://www.omnigroup.com/omnifocus"
                    )
                elif "not allowed" in error_msg or "permission" in error_msg.lower():
                    raise RuntimeError(
                        "OmniFocus automation permission denied.\n"
                        "Grant automation permissions in:\n"
                        "System Settings > Privacy & Security > Automation"
                    )
                else:
                    raise ValueError(f"OmniFocus script failed: {error_msg}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise ConnectionError(f"OmniFocus script timeout after {self.timeout}s")
        except FileNotFoundError:
            raise RuntimeError(
                "osascript command not found. This client requires macOS."
            )
        except Exception as e:
            if isinstance(e, (RuntimeError, ConnectionError, ValueError)):
                raise
            raise ConnectionError(f"Script execution failed: {e}")

    def _parse_date(self, date_str: str) -> str:
        """Parse and validate ISO date string (YYYY-MM-DD).

        Args:
            date_str: ISO date string

        Returns:
            Validated date string

        Raises:
            ValueError: If date format invalid
        """
        if not date_str:
            return date_str

        try:
            # Validate date format
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            raise ValueError(
                f"Invalid date format: {date_str}\n"
                "Use ISO format: YYYY-MM-DD (e.g., 2026-02-10)"
            )

    def _format_task_dict(self, jxa_json: str) -> dict:
        """Parse JXA task JSON output into standardized dict.

        Args:
            jxa_json: JSON string from JXA script

        Returns:
            Standardized task dict with keys:
            - id: Task ID
            - name: Task name
            - note: Task note
            - completed: Boolean
            - flagged: Boolean
            - dueDate: ISO date string or None
            - deferDate: ISO date string or None
            - project: Dict with id/name or None
            - tags: List of dicts with id/name

        Raises:
            ValueError: If JSON parsing fails
        """
        try:
            return json.loads(jxa_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse task data: {e}")

    # ===== Read Operations =====

    def get_task(self, task_id: str) -> dict:
        """Get a single task by ID.

        Args:
            task_id: OmniFocus task ID (e.g., "n--Q40q4juK")

        Returns:
            dict with: id, name, note, completed, flagged, dueDate, deferDate,
                       project (dict with id/name or None), tags (list of dicts)

        Raises:
            ValueError: If task not found
        """
        script = f'''
var app = Application("OmniFocus");
var doc = app.defaultDocument;
var tasks = doc.flattenedTasks.whose({{id: "{task_id}"}});

if (tasks.length === 0) {{
    throw new Error("Task not found: {task_id}");
}}

var task = tasks[0];
var proj = task.containingProject();

// Helper to check if date is valid (OmniFocus uses 1904-01-01 for unset dates)
function isValidDate(date) {{
    if (!date) return false;
    var year = date.getFullYear();
    return year > 2000;  // Treat dates before 2000 as unset
}}

var result = {{
    id: task.id(),
    name: task.name(),
    note: task.note(),
    completed: task.completed(),
    flagged: task.flagged(),
    dueDate: isValidDate(task.dueDate()) ? task.dueDate().toISOString() : null,
    deferDate: isValidDate(task.deferDate()) ? task.deferDate().toISOString() : null,
    project: proj ? {{id: proj.id(), name: proj.name()}} : null,
    tags: task.tags().map(function(t) {{
        return {{id: t.id(), name: t.name()}};
    }})
}};

JSON.stringify(result);
'''
        result = self._execute_jxa(script)
        return self._format_task_dict(result)

    def query_tasks(
        self,
        status: str = "inbox",
        project: str = None,
        tag: str = None,
        flagged: bool = None,
        due_before: str = None,
        due_after: str = None,
        limit: int = 50
    ) -> list:
        """Query tasks with filters.

        Args:
            status: "inbox" (default), "active", "completed", or "all"
            project: Filter by project name
            tag: Filter by tag name
            flagged: Filter by flagged status
            due_before: ISO date string (YYYY-MM-DD)
            due_after: ISO date string (YYYY-MM-DD)
            limit: Maximum results to return

        Returns:
            List of task dicts (non-completed by default)

        Raises:
            ValueError: If date format invalid
        """
        # Validate dates if provided
        if due_before:
            due_before = self._parse_date(due_before)
        if due_after:
            due_after = self._parse_date(due_after)

        # Build filter parameters
        has_project = "true" if project else "false"
        has_tag = "true" if tag else "false"
        has_flagged = "true" if flagged is not None else "false"
        has_due_before = "true" if due_before else "false"
        has_due_after = "true" if due_after else "false"

        script = f'''
var app = Application("OmniFocus");
var doc = app.defaultDocument;

// Helper to check if date is valid (OmniFocus uses 1904-01-01 for unset dates)
function isValidDate(date) {{
    if (!date) return false;
    var year = date.getFullYear();
    return year > 2000;  // Treat dates before 2000 as unset
}}

// Get tasks based on status
var tasks;
if ("{status}" === "inbox") {{
    tasks = doc.inboxTasks();
}} else if ("{status}" === "completed") {{
    tasks = doc.flattenedTasks.whose({{completed: true}});
}} else if ("{status}" === "all") {{
    tasks = doc.flattenedTasks();
}} else {{
    // active: not completed
    tasks = doc.flattenedTasks.whose({{completed: false}});
}}

// Filter tasks
var filtered = [];
for (var i = 0; i < tasks.length && filtered.length < {limit}; i++) {{
    var task = tasks[i];

    // Skip completed tasks unless specifically querying for them
    if ("{status}" !== "completed" && "{status}" !== "all" && task.completed()) {{
        continue;
    }}

    var include = true;

    // Filter by project
    if ({has_project}) {{
        var proj = task.containingProject();
        include = proj && proj.name() === "{project}";
    }}

    // Filter by tag
    if ({has_tag} && include) {{
        var taskTags = task.tags().map(function(t) {{ return t.name(); }});
        include = taskTags.indexOf("{tag}") >= 0;
    }}

    // Filter by flagged
    if ({has_flagged} && include) {{
        include = task.flagged() === {str(flagged).lower()};
    }}

    // Filter by due_before
    if ({has_due_before} && include) {{
        var dueDate = task.dueDate();
        if (dueDate) {{
            var due = new Date("{due_before}");
            include = dueDate <= due;
        }} else {{
            include = false;
        }}
    }}

    // Filter by due_after
    if ({has_due_after} && include) {{
        var dueDate = task.dueDate();
        if (dueDate) {{
            var due = new Date("{due_after}");
            include = dueDate >= due;
        }} else {{
            include = false;
        }}
    }}

    if (include) {{
        var proj = task.containingProject();
        filtered.push({{
            id: task.id(),
            name: task.name(),
            completed: task.completed(),
            flagged: task.flagged(),
            dueDate: isValidDate(task.dueDate()) ? task.dueDate().toISOString() : null,
            project: proj ? proj.name() : null,
            tags: task.tags().map(function(t) {{ return t.name(); }})
        }});
    }}
}}

JSON.stringify(filtered);
'''
        result = self._execute_jxa(script)
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse tasks data: {e}")

    def get_inbox_tasks(self, limit: int = 50) -> list:
        """Get tasks in inbox.

        Args:
            limit: Maximum results to return

        Returns:
            List of task dicts
        """
        return self.query_tasks(status="inbox", limit=limit)

    def get_flagged_tasks(self, limit: int = 50) -> list:
        """Get flagged tasks.

        Args:
            limit: Maximum results to return

        Returns:
            List of task dicts
        """
        return self.query_tasks(status="active", flagged=True, limit=limit)

    def get_tasks_by_project(self, project_name: str, limit: int = 50) -> list:
        """Get tasks in a specific project.

        Args:
            project_name: Project name
            limit: Maximum results to return

        Returns:
            List of task dicts
        """
        return self.query_tasks(status="active", project=project_name, limit=limit)

    def get_tasks_by_tag(self, tag_name: str, limit: int = 50) -> list:
        """Get tasks with a specific tag.

        Args:
            tag_name: Tag name
            limit: Maximum results to return

        Returns:
            List of task dicts
        """
        return self.query_tasks(status="active", tag=tag_name, limit=limit)

# ===== Projects & Tags Operations =====

    def list_projects(self) -> list:
        """List all projects.

        Returns:
            List of dicts with: id, name, status
        """
        script = '''
var app = Application("OmniFocus");
var doc = app.defaultDocument;
var projects = doc.flattenedProjects();

var result = [];
for (var i = 0; i < projects.length; i++) {
    var proj = projects[i];
    result.push({
        id: proj.id(),
        name: proj.name(),
        status: proj.status()
    });
}

JSON.stringify(result);
'''
        result = self._execute_jxa(script)
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse projects data: {e}")

    def list_tags(self) -> list:
        """List all tags.

        Returns:
            List of dicts with: id, name
        """
        script = '''
var app = Application("OmniFocus");
var doc = app.defaultDocument;
var tags = doc.flattenedTags();

var result = [];
for (var i = 0; i < tags.length; i++) {
    var tag = tags[i];
    result.push({
        id: tag.id(),
        name: tag.name()
    });
}

JSON.stringify(result);
'''
        result = self._execute_jxa(script)
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse tags data: {e}")

    def get_project_by_name(self, name: str) -> dict:
        """Get project by name.

        Args:
            name: Project name

        Returns:
            dict with: id, name, status

        Raises:
            ValueError: If project not found or multiple matches
        """
        script = f'''
var app = Application("OmniFocus");
var doc = app.defaultDocument;
var projects = doc.flattenedProjects.whose({{name: "{name}"}});

if (projects.length === 0) {{
    throw new Error("Project not found: {name}");
}}

if (projects.length > 1) {{
    throw new Error("Multiple projects found with name: {name}");
}}

var proj = projects[0];
JSON.stringify({{
    id: proj.id(),
    name: proj.name(),
    status: proj.status()
}});
'''
        result = self._execute_jxa(script)
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse project data: {e}")

    def get_tag_by_name(self, name: str) -> dict:
        """Get tag by name.

        Args:
            name: Tag name

        Returns:
            dict with: id, name

        Raises:
            ValueError: If tag not found or multiple matches
        """
        script = f'''
var app = Application("OmniFocus");
var doc = app.defaultDocument;
var tags = doc.flattenedTags.whose({{name: "{name}"}});

if (tags.length === 0) {{
    throw new Error("Tag not found: {name}");
}}

if (tags.length > 1) {{
    throw new Error("Multiple tags found with name: {name}");
}}

var tag = tags[0];
JSON.stringify({{
    id: tag.id(),
    name: tag.name()
}});
'''
        result = self._execute_jxa(script)
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse tag data: {e}")

# ===== Write Operations =====

    def create_task(
        self,
        name: str,
        note: str = None,
        project: str = None,
        due_date: str = None,
        defer_date: str = None,
        tags: list = None,
        flagged: bool = False
    ) -> dict:
        """Create a new task in inbox or specified project.

        Prevents duplicate tasks by checking if a task with the same name already exists.

        Args:
            name: Task name
            note: Task note/description
            project: Project name (creates in inbox if not specified)
            due_date: ISO date string (YYYY-MM-DD)
            defer_date: ISO date string (YYYY-MM-DD)
            tags: List of tag names
            flagged: Whether to flag the task

        Returns:
            Created task dict with ID, or existing task if duplicate found

        Raises:
            ValueError: If project or tag not found, date format invalid, or duplicate task exists
        """
        # Check for duplicate task
        target_project = project or self.default_project
        if target_project:
            existing_tasks = self.query_tasks(status="active", project=target_project, limit=200)
        else:
            existing_tasks = self.get_inbox_tasks(limit=200)

        for task in existing_tasks:
            if task.get('name') == name:
                raise ValueError(
                    f"Task '{name}' already exists (ID: {task['id']}). "
                    "Not creating duplicate."
                )

        # Validate dates
        if due_date:
            due_date = self._parse_date(due_date)
        if defer_date:
            defer_date = self._parse_date(defer_date)

        # Use default project if configured and no project specified
        if not project and self.default_project:
            project = self.default_project

        # Add default tag if configured
        if self.default_tag:
            if tags:
                if self.default_tag not in tags:
                    tags.append(self.default_tag)
            else:
                tags = [self.default_tag]

        # Escape quotes in strings
        name_escaped = name.replace('"', '\\"').replace("'", "\\'")
        note_escaped = (note or "").replace('"', '\\"').replace("'", "\\'")
        project_escaped = (project or "").replace('"', '\\"').replace("'", "\\'")

        # Build tag names JSON
        tag_names_json = json.dumps(tags) if tags else "[]"

        # Build date setting code only if dates are provided
        date_code = ""
        if due_date:
            date_code += f'\ntask.dueDate = new Date("{due_date}");'
        if defer_date:
            date_code += f'\ntask.deferDate = new Date("{defer_date}");'

        script = f'''
var app = Application("OmniFocus");
var doc = app.defaultDocument;

// Create task in inbox first
var taskProps = {{
    name: "{name_escaped}"
}};

if ("{note_escaped}") {{
    taskProps.note = "{note_escaped}";
}}

if ({str(flagged).lower()}) {{
    taskProps.flagged = true;
}}

var task = app.InboxTask(taskProps);
doc.inboxTasks.push(task);
{date_code}

// Move to project if specified
if ("{project_escaped}") {{
    var projects = doc.flattenedProjects.whose({{name: "{project_escaped}"}});
    if (projects.length === 0) {{
        throw new Error("Project not found: {project_escaped}");
    }}
    var targetProject = projects[0];
    task.assignedContainer = targetProject;
}}

// Add tags if provided
var tagNames = {tag_names_json};
for (var i = 0; i < tagNames.length; i++) {{
    var tags = doc.flattenedTags.whose({{name: tagNames[i]}});
    if (tags.length > 0) {{
        task.addTag(tags[0]);
    }} else {{
        throw new Error("Tag not found: " + tagNames[i]);
    }}
}}

JSON.stringify({{
    id: task.id(),
    name: task.name()
}});
'''
        result = self._execute_jxa(script)
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse created task data: {e}")

    def update_task(self, task_id: str, **kwargs) -> None:
        """Update task properties.

        Args:
            task_id: Task ID
            **kwargs: Properties to update:
                - name: New task name
                - note: New task note
                - due_date: ISO date string (YYYY-MM-DD)
                - defer_date: ISO date string (YYYY-MM-DD)
                - flagged: Boolean
                - project: Project name
                - tags: List of tag names (replaces existing tags)

        Raises:
            ValueError: If task not found, project/tag not found, or date invalid
        """
        # Build update operations
        updates = []

        if "name" in kwargs:
            name = kwargs["name"].replace('"', '\\"').replace("'", "\\'")
            updates.append(f'task.name = "{name}";')

        if "note" in kwargs:
            note = kwargs["note"].replace('"', '\\"').replace("'", "\\'")
            updates.append(f'task.note = "{note}";')

        if "flagged" in kwargs:
            flagged_val = str(kwargs["flagged"]).lower()
            updates.append(f'task.flagged = {flagged_val};')

        if "due_date" in kwargs:
            due_date = self._parse_date(kwargs["due_date"])
            if due_date:
                updates.append(f'task.dueDate = new Date("{due_date}");')
            else:
                updates.append('task.dueDate = null;')

        if "defer_date" in kwargs:
            defer_date = self._parse_date(kwargs["defer_date"])
            if defer_date:
                updates.append(f'task.deferDate = new Date("{defer_date}");')
            else:
                updates.append('task.deferDate = null;')

        if "project" in kwargs:
            project = kwargs["project"].replace('"', '\\"').replace("'", "\\'")
            updates.append(f'''
var projects = doc.flattenedProjects.whose({{name: "{project}"}});
if (projects.length === 0) {{
    throw new Error("Project not found: {project}");
}}
task.assignedContainer = projects[0];
''')

        if "tags" in kwargs:
            tag_names_json = json.dumps(kwargs["tags"])
            updates.append(f'''
// Remove existing tags
var existingTags = task.tags();
for (var i = 0; i < existingTags.length; i++) {{
    task.removeTag(existingTags[i]);
}}
// Add new tags
var tagNames = {tag_names_json};
for (var i = 0; i < tagNames.length; i++) {{
    var tags = doc.flattenedTags.whose({{name: tagNames[i]}});
    if (tags.length > 0) {{
        task.addTag(tags[0]);
    }} else {{
        throw new Error("Tag not found: " + tagNames[i]);
    }}
}}
''')

        if not updates:
            return  # Nothing to update

        updates_code = "\n".join(updates)

        script = f'''
var app = Application("OmniFocus");
var doc = app.defaultDocument;
var tasks = doc.flattenedTasks.whose({{id: "{task_id}"}});

if (tasks.length === 0) {{
    throw new Error("Task not found: {task_id}");
}}

var task = tasks[0];

{updates_code}

"Task updated";
'''
        self._execute_jxa(script)

    def complete_task(self, task_id: str) -> None:
        """Mark task as complete.

        Uses AppleScript for better compatibility with mark complete command.

        Args:
            task_id: Task ID

        Raises:
            ValueError: If task not found
        """
        script = f'''
tell application "OmniFocus"
    tell default document
        set matchingTasks to flattened tasks whose id is "{task_id}"
        if length of matchingTasks is 0 then
            error "Task not found: {task_id}"
        end if
        set theTask to item 1 of matchingTasks
        mark complete theTask
        return "Task completed"
    end tell
end tell
'''
        self._execute_applescript(script)

    def delete_task(self, task_id: str) -> None:
        """Delete (drop) a task.

        Args:
            task_id: Task ID

        Raises:
            ValueError: If task not found
        """
        script = f'''
var app = Application("OmniFocus");
var doc = app.defaultDocument;
var tasks = doc.flattenedTasks.whose({{id: "{task_id}"}});

if (tasks.length === 0) {{
    throw new Error("Task not found: {task_id}");
}}

var task = tasks[0];
task.delete();

"Task deleted";
'''
        self._execute_jxa(script)


# ===== Output Formatting =====


def _format_task(task: dict) -> str:
    """Format task as one-liner.

    Format: <task-id>: <name> [<status>] [<project>] [<tags>] [due: <date>]
    Example: n--Q40q4juK: Review documentation [Active] [Work] [urgent, review] [due: 2026-02-10]

    Args:
        task: Task dict

    Returns:
        Formatted one-line string
    """
    task_id = task.get("id", "UNKNOWN")
    name = task.get("name", "No name")
    completed = task.get("completed", False)
    flagged = task.get("flagged", False)

    # Status
    if completed:
        status = "Completed"
    elif flagged:
        status = "Flagged"
    else:
        status = "Active"

    # Project
    project = task.get("project")
    if isinstance(project, dict):
        project_str = f" [{project.get('name', 'No project')}]"
    elif isinstance(project, str):
        project_str = f" [{project}]" if project else ""
    else:
        project_str = ""

    # Tags
    tags = task.get("tags", [])
    if tags:
        if isinstance(tags[0], dict):
            tag_names = [t.get("name", "") for t in tags]
        else:
            tag_names = tags
        tags_str = f" [{', '.join(tag_names)}]" if tag_names else ""
    else:
        tags_str = ""

    # Due date
    due_date = task.get("dueDate")
    if due_date:
        # Extract date part from ISO format
        if "T" in due_date:
            due_date = due_date.split("T")[0]
        due_str = f" [due: {due_date}]"
    else:
        due_str = ""

    return f"{task_id}: {name} [{status}]{project_str}{tags_str}{due_str}"


def _print_task_details(task: dict) -> None:
    """Print detailed multi-line task information.

    Args:
        task: Task dict
    """
    task_id = task.get("id", "UNKNOWN")
    name = task.get("name", "No name")
    note = task.get("note", "")
    completed = task.get("completed", False)
    flagged = task.get("flagged", False)

    # Status
    if completed:
        status = "Completed"
    else:
        status = "Active"

    # Project
    project = task.get("project")
    if isinstance(project, dict):
        project_name = project.get("name", "None")
    elif isinstance(project, str):
        project_name = project if project else "None"
    else:
        project_name = "None"

    # Tags
    tags = task.get("tags", [])
    if tags:
        if isinstance(tags[0], dict):
            tag_names = [t.get("name", "") for t in tags]
        else:
            tag_names = tags
        tags_str = ", ".join(tag_names) if tag_names else "None"
    else:
        tags_str = "None"

    # Flagged
    flagged_str = "Yes" if flagged else "No"

    # Due date
    due_date = task.get("dueDate")
    if due_date:
        if "T" in due_date:
            due_date = due_date.split("T")[0]
        due_str = due_date
    else:
        due_str = "None"

    # Defer date
    defer_date = task.get("deferDate")
    if defer_date:
        if "T" in defer_date:
            defer_date = defer_date.split("T")[0]
        defer_str = defer_date
    else:
        defer_str = "None"

    # Note preview
    if note:
        note_preview = note[:200] + "..." if len(note) > 200 else note
    else:
        note_preview = "None"

    print(f"{task_id}: {name}")
    print(f"  Status: {status}")
    print(f"  Project: {project_name}")
    print(f"  Tags: {tags_str}")
    print(f"  Flagged: {flagged_str}")
    print(f"  Due: {due_str}")
    print(f"  Defer: {defer_str}")
    print(f"  Note: {note_preview}")


# ===== CLI Integration =====


def main():
    """CLI entry point for OmniFocus client.

    Default behavior: Works with inbox tasks only, excludes completed tasks.

    Usage:
        python -m sidekick.clients.omnifocus get-task <task-id>
        python -m sidekick.clients.omnifocus query [--status inbox|active|completed|all] [--project NAME] [--tag NAME] [--flagged] [--due-before YYYY-MM-DD] [--due-after YYYY-MM-DD] [--limit N]
        python -m sidekick.clients.omnifocus inbox [--limit N]
        python -m sidekick.clients.omnifocus flagged [--limit N]
        python -m sidekick.clients.omnifocus by-project <name> [--limit N]
        python -m sidekick.clients.omnifocus by-tag <name> [--limit N]
        python -m sidekick.clients.omnifocus create <name> [--note TEXT] [--project NAME] [--due YYYY-MM-DD] [--defer YYYY-MM-DD] [--tag NAME] [--flagged]
        python -m sidekick.clients.omnifocus update <task-id> [--name TEXT] [--note TEXT] [--project NAME] [--due YYYY-MM-DD] [--defer YYYY-MM-DD] [--flagged yes|no]
        python -m sidekick.clients.omnifocus complete <task-id>
        python -m sidekick.clients.omnifocus delete <task-id>
        python -m sidekick.clients.omnifocus list-projects
        python -m sidekick.clients.omnifocus list-tags
    """
    if len(sys.argv) < 2:
        print("Usage: python -m sidekick.clients.omnifocus <command> [args...]")
        print("\nCommands:")
        print("  get-task <task-id>")
        print("  query [--status STATUS] [--project NAME] [--tag NAME] [--flagged] [--due-before DATE] [--due-after DATE] [--limit N]")
        print("  inbox [--limit N]")
        print("  flagged [--limit N]")
        print("  by-project <name> [--limit N]")
        print("  by-tag <name> [--limit N]")
        print("  create <name> [--note TEXT] [--project NAME] [--due DATE] [--defer DATE] [--tag NAME] [--flagged]")
        print("  update <task-id> [--name TEXT] [--note TEXT] [--project NAME] [--due DATE] [--defer DATE] [--flagged yes|no]")
        print("  complete <task-id>")
        print("  delete <task-id>")
        print("  list-projects")
        print("  list-tags")
        print("\nOptions:")
        print("  --status: inbox (default), active, completed, all")
        print("  --limit: Maximum results (default 50)")
        print("  Dates: YYYY-MM-DD format (e.g., 2026-02-10)")
        print("\nNote: By default, all queries exclude completed tasks and work with inbox only.")
        sys.exit(1)

    try:
        start_time = time.time()

        # Initialize client with optional config
        # Try to load defaults from config if available
        default_project = None
        default_tag = None
        try:
            from sidekick.config import get_omnifocus_config
            config = get_omnifocus_config()
            default_project = config.get("default_project")
            default_tag = config.get("default_tag")
        except (ImportError, ValueError):
            # Config not available or incomplete, continue without defaults
            pass

        client = OmniFocusClient(
            default_project=default_project,
            default_tag=default_tag
        )

        command = sys.argv[1]

        # ===== Read Commands =====
        if command == "get-task":
            if len(sys.argv) < 3:
                print("Error: get-task requires task-id argument", file=sys.stderr)
                sys.exit(1)
            task_id = sys.argv[2]
            task = client.get_task(task_id)
            _print_task_details(task)

        elif command == "query":
            # Parse query options
            status = "inbox"
            project = None
            tag = None
            flagged = None
            due_before = None
            due_after = None
            limit = 50

            i = 2
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--status" and i + 1 < len(sys.argv):
                    status = sys.argv[i + 1]
                    i += 2
                elif arg == "--project" and i + 1 < len(sys.argv):
                    project = sys.argv[i + 1]
                    i += 2
                elif arg == "--tag" and i + 1 < len(sys.argv):
                    tag = sys.argv[i + 1]
                    i += 2
                elif arg == "--flagged":
                    flagged = True
                    i += 1
                elif arg == "--due-before" and i + 1 < len(sys.argv):
                    due_before = sys.argv[i + 1]
                    i += 2
                elif arg == "--due-after" and i + 1 < len(sys.argv):
                    due_after = sys.argv[i + 1]
                    i += 2
                elif arg == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            tasks = client.query_tasks(
                status=status,
                project=project,
                tag=tag,
                flagged=flagged,
                due_before=due_before,
                due_after=due_after,
                limit=limit
            )
            print(f"Found {len(tasks)} tasks:")
            for task in tasks:
                print(_format_task(task))

        elif command == "inbox":
            limit = 50
            if len(sys.argv) >= 3 and sys.argv[2] == "--limit":
                limit = int(sys.argv[3])
            tasks = client.get_inbox_tasks(limit=limit)
            print(f"Inbox tasks ({len(tasks)}):")
            for task in tasks:
                print(_format_task(task))

        elif command == "flagged":
            limit = 50
            if len(sys.argv) >= 3 and sys.argv[2] == "--limit":
                limit = int(sys.argv[3])
            tasks = client.get_flagged_tasks(limit=limit)
            print(f"Flagged tasks ({len(tasks)}):")
            for task in tasks:
                print(_format_task(task))

        elif command == "by-project":
            if len(sys.argv) < 3:
                print("Error: by-project requires project name argument", file=sys.stderr)
                sys.exit(1)
            project_name = sys.argv[2]
            limit = 50
            if len(sys.argv) >= 4 and sys.argv[3] == "--limit":
                limit = int(sys.argv[4])
            tasks = client.get_tasks_by_project(project_name, limit=limit)
            print(f"Tasks in '{project_name}' ({len(tasks)}):")
            for task in tasks:
                print(_format_task(task))

        elif command == "by-tag":
            if len(sys.argv) < 3:
                print("Error: by-tag requires tag name argument", file=sys.stderr)
                sys.exit(1)
            tag_name = sys.argv[2]
            limit = 50
            if len(sys.argv) >= 4 and sys.argv[3] == "--limit":
                limit = int(sys.argv[4])
            tasks = client.get_tasks_by_tag(tag_name, limit=limit)
            print(f"Tasks with tag '{tag_name}' ({len(tasks)}):")
            for task in tasks:
                print(_format_task(task))

        # ===== Write Commands =====
        elif command == "create":
            if len(sys.argv) < 3:
                print("Error: create requires task name argument", file=sys.stderr)
                sys.exit(1)

            name = sys.argv[2]
            note = None
            project = None
            due_date = None
            defer_date = None
            tags = []
            flagged = False

            i = 3
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--note" and i + 1 < len(sys.argv):
                    note = sys.argv[i + 1]
                    i += 2
                elif arg == "--project" and i + 1 < len(sys.argv):
                    project = sys.argv[i + 1]
                    i += 2
                elif arg == "--due" and i + 1 < len(sys.argv):
                    due_date = sys.argv[i + 1]
                    i += 2
                elif arg == "--defer" and i + 1 < len(sys.argv):
                    defer_date = sys.argv[i + 1]
                    i += 2
                elif arg == "--tag" and i + 1 < len(sys.argv):
                    tags.append(sys.argv[i + 1])
                    i += 2
                elif arg == "--flagged":
                    flagged = True
                    i += 1
                else:
                    i += 1

            created_task = client.create_task(
                name=name,
                note=note,
                project=project,
                due_date=due_date,
                defer_date=defer_date,
                tags=tags if tags else None,
                flagged=flagged
            )
            print(f"Created task: {created_task['id']}: {created_task['name']}")

        elif command == "update":
            if len(sys.argv) < 3:
                print("Error: update requires task-id argument", file=sys.stderr)
                sys.exit(1)

            task_id = sys.argv[2]
            updates = {}

            i = 3
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--name" and i + 1 < len(sys.argv):
                    updates["name"] = sys.argv[i + 1]
                    i += 2
                elif arg == "--note" and i + 1 < len(sys.argv):
                    updates["note"] = sys.argv[i + 1]
                    i += 2
                elif arg == "--project" and i + 1 < len(sys.argv):
                    updates["project"] = sys.argv[i + 1]
                    i += 2
                elif arg == "--due" and i + 1 < len(sys.argv):
                    updates["due_date"] = sys.argv[i + 1]
                    i += 2
                elif arg == "--defer" and i + 1 < len(sys.argv):
                    updates["defer_date"] = sys.argv[i + 1]
                    i += 2
                elif arg == "--flagged" and i + 1 < len(sys.argv):
                    updates["flagged"] = sys.argv[i + 1].lower() in ("yes", "true", "1")
                    i += 2
                else:
                    i += 1

            if not updates:
                print("Error: update requires at least one property to update", file=sys.stderr)
                sys.exit(1)

            client.update_task(task_id, **updates)
            print(f"Updated task: {task_id}")

        elif command == "complete":
            if len(sys.argv) < 3:
                print("Error: complete requires task-id argument", file=sys.stderr)
                sys.exit(1)
            task_id = sys.argv[2]
            client.complete_task(task_id)
            print(f"Completed task: {task_id}")

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Error: delete requires task-id argument", file=sys.stderr)
                sys.exit(1)
            task_id = sys.argv[2]
            client.delete_task(task_id)
            print(f"Deleted task: {task_id}")

        # ===== Projects & Tags Commands =====
        elif command == "list-projects":
            projects = client.list_projects()
            print(f"Projects ({len(projects)}):")
            for project in projects:
                status = project.get("status", "")
                print(f"  {project['name']} [{status}]")

        elif command == "list-tags":
            tags = client.list_tags()
            print(f"Tags ({len(tags)}):")
            for tag in tags:
                print(f"  {tag['name']}")

        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)

        # Debug output
        elapsed_time = time.time() - start_time
        print(f"\n[Debug] Script calls: {client.script_call_count}, Time: {elapsed_time:.2f}s", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
