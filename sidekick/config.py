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
