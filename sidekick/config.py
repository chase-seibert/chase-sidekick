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


def get_atlassian_config() -> dict:
    """Get Atlassian configuration from .env file or environment variables.

    This configuration works for both JIRA and Confluence since they share
    the same authentication system (same API token, email, and domain).

    Loads from .env file first, then falls back to system environment variables.
    Supports legacy JIRA_* variables for backward compatibility.

    Returns:
        dict with keys: url, email, api_token

    Raises:
        ValueError: If required environment variables are missing
    """
    env_file_vars = _load_env_file()

    # Try new ATLASSIAN_* variables first
    url = _get_env("ATLASSIAN_URL", env_file_vars)
    email = _get_env("ATLASSIAN_EMAIL", env_file_vars)
    api_token = _get_env("ATLASSIAN_API_TOKEN", env_file_vars)

    # Fallback to legacy JIRA_* variables for backward compatibility
    if not url:
        url = _get_env("JIRA_URL", env_file_vars)
    if not email:
        email = _get_env("JIRA_EMAIL", env_file_vars)
    if not api_token:
        api_token = _get_env("JIRA_API_TOKEN", env_file_vars)

    if not all([url, email, api_token]):
        raise ValueError(
            "Missing required Atlassian configuration. "
            "Set ATLASSIAN_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_TOKEN "
            "in .env file or environment variables. "
            "(Legacy JIRA_* variables are also supported for backward compatibility.)"
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


def get_omnifocus_config() -> dict:
    """Get OmniFocus configuration from .env file or environment variables.

    OmniFocus configuration is optional and provides defaults for task creation.

    Loads from .env file first, then falls back to system environment variables.

    Returns:
        dict with optional keys:
        - default_project: Default project name for new tasks
        - default_tag: Default tag name for new tasks

    Note:
        All configuration is optional. Empty dict will be returned if no
        OmniFocus configuration is present.
    """
    env_file_vars = _load_env_file()

    default_project = _get_env("OMNIFOCUS_DEFAULT_PROJECT", env_file_vars)
    default_tag = _get_env("OMNIFOCUS_DEFAULT_TAG", env_file_vars)

    config = {}
    if default_project:
        config["default_project"] = default_project
    if default_tag:
        config["default_tag"] = default_tag

    return config


def get_user_config() -> dict:
    """Get user configuration from .env file or environment variables.

    Used for personalized features like 1:1 doc management.

    Returns:
        dict with keys: name, email

    Raises:
        ValueError: If required environment variables are missing
    """
    env_file_vars = _load_env_file()

    name = _get_env("USER_NAME", env_file_vars)
    email = _get_env("USER_EMAIL", env_file_vars)

    # Fallback to ATLASSIAN_EMAIL if USER_EMAIL not set
    if not email:
        email = _get_env("ATLASSIAN_EMAIL", env_file_vars)

    if not all([name, email]):
        raise ValueError(
            "Missing required user configuration. "
            "Set USER_NAME and USER_EMAIL in .env file or environment variables."
        )

    return {
        "name": name,
        "email": email
    }


def get_dropbox_config() -> dict:
    """Get Dropbox configuration from .env file or environment variables.

    Returns:
        dict with key: access_token

    Raises:
        ValueError: If required environment variables are missing
    """
    env_file_vars = _load_env_file()

    access_token = _get_env("DROPBOX_ACCESS_TOKEN", env_file_vars)

    if not access_token:
        raise ValueError(
            "Missing required Dropbox configuration. "
            "Set DROPBOX_ACCESS_TOKEN in .env file or environment variables. "
            "Get token at: https://www.dropbox.com/developers/apps "
            "(create app → generate access token)"
        )

    return {"access_token": access_token}


def get_google_config() -> dict:
    """Get Google configuration from .env file or environment variables.

    This configuration works for Gmail, Google Calendar, and Google Sheets
    since they all use the same OAuth2 credentials (just need different API scopes).

    Returns:
        dict with keys: client_id, client_secret, refresh_token

    Raises:
        ValueError: If required environment variables are missing
    """
    env_file_vars = _load_env_file()

    client_id = _get_env("GOOGLE_CLIENT_ID", env_file_vars)
    client_secret = _get_env("GOOGLE_CLIENT_SECRET", env_file_vars)
    refresh_token = _get_env("GOOGLE_REFRESH_TOKEN", env_file_vars)

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Missing required Google configuration. "
            "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN "
            "in .env file or environment variables. "
            "See sidekick/skills/gmail.md, gcalendar.md, or gsheets.md for setup instructions."
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }
