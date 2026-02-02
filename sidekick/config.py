"""Configuration management - loads from .env file and environment variables."""
import os
from pathlib import Path


def _load_env_file(env_path: Path = None) -> dict:
    """Load environment variables from .env file.

    Args:
        env_path: Path to .env file (defaults to .env in project root)

    Returns:
        dict of environment variables from .env file
    """
    if env_path is None:
        # Find .env in project root (1 level up from this file)
        env_path = Path(__file__).parent.parent / ".env"

    env_vars = {}

    if not env_path.exists():
        return env_vars

    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # Parse KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    env_vars[key] = value
    except Exception:
        # If we can't read the file, just return empty dict
        pass

    return env_vars


def _get_env(key: str, env_file_vars: dict) -> str:
    """Get environment variable from .env file or os.environ.

    Args:
        key: Environment variable key
        env_file_vars: Dict of variables loaded from .env file

    Returns:
        Value from .env file if present, otherwise from os.environ
    """
    # First check .env file, then fall back to os.environ
    return env_file_vars.get(key) or os.environ.get(key)


def get_jira_config() -> dict:
    """Get JIRA configuration from .env file or environment variables.

    Loads from .env file first, then falls back to system environment variables.

    Returns:
        dict with keys: url, email, api_token

    Raises:
        ValueError: If required environment variables are missing
    """
    env_file_vars = _load_env_file()

    url = _get_env("JIRA_URL", env_file_vars)
    email = _get_env("JIRA_EMAIL", env_file_vars)
    api_token = _get_env("JIRA_API_TOKEN", env_file_vars)

    if not all([url, email, api_token]):
        raise ValueError(
            "Missing required JIRA configuration. "
            "Set JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN in .env file or environment variables."
        )

    return {
        "url": url,
        "email": email,
        "api_token": api_token
    }


def get_groups() -> dict:
    """Get group configurations from .env file.

    Supports defining custom groups with project lists and JQL snippets.
    Groups are not checked into git - they're defined in .env only.

    Example .env configuration:
        MYTEAM_GROUP_PROJECTS=PROJ1,PROJ2,PROJ3
        MYTEAM_GROUP_JQL=project IN ("PROJ1", "PROJ2", "PROJ3")

        BACKEND_GROUP_PROJECTS=API,FRONTEND
        BACKEND_GROUP_JQL=project IN ("API", "FRONTEND")

    Returns:
        dict mapping group names to their configuration:
        {
            "myteam": {
                "projects": ["PROJ1", "PROJ2", "PROJ3"],
                "jql": 'project IN ("PROJ1", "PROJ2", "PROJ3")'
            }
        }
    """
    env_file_vars = _load_env_file()
    groups = {}

    # Find all *_GROUP_PROJECTS entries
    for key in env_file_vars.keys():
        if key.endswith("_GROUP_PROJECTS"):
            # Extract group name (e.g., "MYTEAM_GROUP_PROJECTS" -> "myteam")
            group_name = key[:-len("_GROUP_PROJECTS")].lower()

            projects_str = env_file_vars[key]
            projects = [p.strip() for p in projects_str.split(",") if p.strip()]

            # Look for corresponding JQL
            jql_key = f"{group_name.upper()}_GROUP_JQL"
            jql = _get_env(jql_key, env_file_vars)

            # If no custom JQL, generate default
            if not jql:
                if len(projects) == 1:
                    jql = f'project = "{projects[0]}"'
                else:
                    project_list = ", ".join(f'"{p}"' for p in projects)
                    jql = f'project IN ({project_list})'

            groups[group_name] = {
                "projects": projects,
                "jql": jql
            }

    return groups


def get_group(group_name: str) -> dict:
    """Get configuration for a specific group.

    Args:
        group_name: Name of the group (e.g., "myteam", "backend")

    Returns:
        dict with keys: projects (list), jql (str)

    Raises:
        ValueError: If group is not configured
    """
    groups = get_groups()
    group_name_lower = group_name.lower()

    if group_name_lower not in groups:
        available = ", ".join(groups.keys()) if groups else "none"
        raise ValueError(
            f"Group '{group_name}' not configured. "
            f"Available groups: {available}. "
            f"Configure in .env with {group_name.upper()}_GROUP_PROJECTS=..."
        )

    return groups[group_name_lower]
