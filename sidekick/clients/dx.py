"""DX API client - Data Studio queries, datafeeds, and CSV downloads."""

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional


class DXHTTPError(RuntimeError):
    """HTTP error returned by DX."""

    def __init__(
        self,
        message: str,
        status: Optional[int] = None,
        body=None,
        retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.status = status
        self.body = body
        self.retry_after = retry_after


class DXClient:
    """DX Web API client using native Python stdlib."""

    TERMINAL_QUERY_STATUSES = {"succeeded", "failed", "expired"}
    PENDING_QUERY_STATUSES = {"queued", "started", "running"}

    def __init__(
        self,
        api_base_url: str,
        token: str,
        web_base_url: str = "https://app.getdx.com",
        timeout: int = 60
    ):
        """Initialize a DX client.

        Args:
            api_base_url: DX API base URL, usually https://api.getdx.com.
            token: DX personal or organization API token.
            web_base_url: DX web app base URL for human-facing links.
            timeout: HTTP request timeout in seconds.
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.web_base_url = web_base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.api_call_count = 0

    def _headers(self, accept: str = "application/json") -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
            "Content-Type": "application/json",
            "User-Agent": "sidekick-dx/1.0"
        }

    def _build_url(self, endpoint: str, params: Optional[dict] = None) -> str:
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        clean_params = {
            key: value
            for key, value in (params or {}).items()
            if value is not None
        }
        if clean_params:
            url += "?" + urllib.parse.urlencode(clean_params, doseq=True)
        return url

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        accept: str = "application/json"
    ) -> dict:
        """Make a DX Web API request and return parsed JSON plus response metadata."""
        url = self._build_url(endpoint, params=params)
        data = json.dumps(json_data).encode("utf-8") if json_data is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(accept=accept),
            method=method
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                self.api_call_count += 1
                body_text = response.read().decode("utf-8")
                body = _parse_json_or_text(body_text)
                self._raise_for_dx_body(body, response.status)
                return {
                    "body": body,
                    "status": response.status,
                    "headers": dict(response.headers)
                }
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8") if e.fp else ""
            body = _parse_json_or_text(body_text)
            retry_after = _parse_retry_after(e.headers.get("Retry-After"))
            message = _extract_error_message(body) or f"DX request failed with HTTP {e.code}"
            raise DXHTTPError(message, status=e.code, body=body, retry_after=retry_after)
        except urllib.error.URLError as e:
            raise ConnectionError(f"DX network error: {e.reason}")

    def _raise_for_dx_body(self, body, status: int) -> None:
        if isinstance(body, dict) and body.get("ok") is False:
            message = _extract_error_message(body) or f"DX API returned ok=false (HTTP {status})"
            raise DXHTTPError(message, status=status, body=body)

    def whoami(self) -> dict:
        """Return the user/team associated with the current token, when available."""
        return self._request("GET", "/auth.whoami")["body"]

    def execute_query(self, sql: str, variables: Optional[dict] = None) -> dict:
        """Start a Data Studio query run."""
        body = {"sql": sql}
        if variables:
            body["variables"] = variables
        return self._request("POST", "/studio.queryRuns.execute", json_data=body)["body"]

    def get_query_run(self, query_run_id: str) -> dict:
        """Get query run status and metadata."""
        return self._request(
            "GET",
            "/studio.queryRuns.info",
            params={"id": query_run_id}
        )["body"]

    def wait_for_query_run(
        self,
        query_run_id: str,
        timeout_seconds: int = 300,
        poll_interval: float = 1.0
    ) -> dict:
        """Poll a query run until it succeeds, fails, or expires."""
        deadline = time.time() + timeout_seconds

        while True:
            try:
                response = self.get_query_run(query_run_id)
            except DXHTTPError as e:
                if e.status == 429:
                    time.sleep(e.retry_after or poll_interval)
                    continue
                raise

            query_run = _query_run(response)
            status = query_run.get("status")

            if status == "succeeded":
                return response
            if status == "failed":
                error = query_run.get("error") or {}
                message = error.get("message") or error.get("code") or query_run
                raise RuntimeError(f"DX query failed: {message}")
            if status == "expired":
                raise RuntimeError(f"DX query results expired: {query_run.get('expires_at')}")
            if status not in self.PENDING_QUERY_STATUSES:
                raise RuntimeError(f"Unexpected DX query status: {status}")
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for DX query run {query_run_id}")

            time.sleep(poll_interval)

    def get_query_results(self, query_run_id: str) -> dict:
        """Get JSON results for a completed query run.

        DX limits JSON responses to 1000 rows. Use CSV downloads for the full
        result set.
        """
        return self._request(
            "GET",
            "/studio.queryRuns.results",
            params={"id": query_run_id, "format": "json"}
        )["body"]

    def execute_and_wait(
        self,
        sql: str,
        variables: Optional[dict] = None,
        timeout_seconds: int = 300,
        poll_interval: float = 1.0,
        fetch_results: bool = True
    ) -> dict:
        """Execute SQL, wait for completion, and optionally fetch JSON results."""
        execute_response = self.execute_query(sql, variables=variables)
        query_run = _query_run(execute_response)
        query_run_id = query_run.get("id")
        if not query_run_id:
            raise RuntimeError(f"DX did not return a query run ID: {execute_response}")

        info_response = self.wait_for_query_run(
            query_run_id,
            timeout_seconds=timeout_seconds,
            poll_interval=poll_interval
        )
        if not fetch_results:
            return info_response

        results_response = self.get_query_results(query_run_id)
        return {
            "ok": True,
            "query_run": _query_run(info_response),
            "results": _results(results_response)
        }

    def download_query_results_csv(self, query_run_id: str, path: str) -> Path:
        """Download full query results as CSV to a local path."""
        url = self._build_url(
            "/studio.queryRuns.results",
            params={"id": query_run_id, "format": "csv"}
        )
        req = urllib.request.Request(
            url,
            headers=self._headers(accept="text/csv"),
            method="GET"
        )
        opener = urllib.request.build_opener(_NoRedirectHandler)

        try:
            response = opener.open(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            if 300 <= e.code < 400:
                location = e.headers.get("Location")
                if not location:
                    raise DXHTTPError(
                        "DX CSV download redirect did not include a Location header",
                        status=e.code
                    )
                download_url = urllib.parse.urljoin(self.api_base_url, location)
                return _download_url_without_auth(download_url, path, timeout=self.timeout)

            body_text = e.read().decode("utf-8") if e.fp else ""
            body = _parse_json_or_text(body_text)
            message = _extract_error_message(body) or f"DX CSV download failed with HTTP {e.code}"
            raise DXHTTPError(message, status=e.code, body=body)

        with response:
            return _write_response_to_path(response, path)

    def get_datafeed(
        self,
        feed_token: str,
        variables: Optional[dict] = None,
        columns: Optional[str] = None
    ) -> dict:
        """Get rows from a saved query datafeed."""
        params = {"feed_token": feed_token, "columns": columns}
        for key, value in (variables or {}).items():
            params[f"var-{key}"] = value
        return self._request("GET", "/queries.datafeed", params=params)["body"]


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _parse_json_or_text(text: str):
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _extract_error_message(body) -> Optional[str]:
    if isinstance(body, dict):
        if isinstance(body.get("error_details"), dict):
            message = body["error_details"].get("message")
            if message:
                return str(message)
        for key in ("message", "error", "error_code"):
            if body.get(key):
                return str(body[key])
    elif body:
        return str(body)
    return None


def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _query_run(response: dict) -> dict:
    return response.get("query_run") or response


def _results(response: dict) -> dict:
    return response.get("results") or response.get("data") or {}


def _columns_and_rows(response: dict) -> tuple:
    data = _results(response)
    return data.get("columns") or [], data.get("rows") or []


def _download_url_without_auth(url: str, path: str, timeout: int = 60) -> Path:
    req = urllib.request.Request(
        url,
        headers={"Accept": "text/csv", "User-Agent": "sidekick-dx/1.0"},
        method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return _write_response_to_path(response, path)
    except urllib.error.URLError as e:
        raise ConnectionError(f"DX CSV download network error: {e.reason}")


def _write_response_to_path(response, path: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return output_path


def _write_rows_csv(path: str, columns: list, rows: list) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if columns:
            writer.writerow(columns)
        writer.writerows(rows)
    return output_path


def _parse_variables(args: argparse.Namespace) -> Optional[dict]:
    variables = {}

    if getattr(args, "variables_json", None):
        parsed = json.loads(args.variables_json)
        if not isinstance(parsed, dict):
            raise ValueError("--variables-json must be a JSON object")
        variables.update(parsed)

    for raw_var in getattr(args, "var", None) or []:
        if "=" not in raw_var:
            raise ValueError(f"Variable must be name=value: {raw_var}")
        key, value = raw_var.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Variable name cannot be empty: {raw_var}")
        variables[key] = _parse_variable_value(value)

    return variables or None


def _parse_variable_value(value: str):
    if "," in value:
        return [part.strip() for part in value.split(",")]
    return value


def _truncate(value, max_width: int = 48) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\n", " ")
    if len(text) <= max_width:
        return text
    return text[:max_width - 3] + "..."


def _print_table(columns: list, rows: list, limit: int = 50) -> None:
    if not columns:
        print("No columns returned.")
        return

    display_rows = rows[:limit]
    string_rows = [
        [_truncate(value) for value in row]
        for row in display_rows
    ]
    widths = []
    for index, column in enumerate(columns):
        width = len(str(column))
        for row in string_rows:
            if index < len(row):
                width = max(width, len(row[index]))
        widths.append(min(48, width))

    header = " | ".join(str(column).ljust(widths[index]) for index, column in enumerate(columns))
    divider = "-+-".join("-" * width for width in widths)
    print(header)
    print(divider)
    for row in string_rows:
        values = []
        for index in range(len(columns)):
            value = row[index] if index < len(row) else ""
            values.append(value.ljust(widths[index]))
        print(" | ".join(values))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more rows not shown")


def _print_query_run(response: dict, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(response, indent=2, sort_keys=True))
        return
    query_run = _query_run(response)
    print(f"Query run: {query_run.get('id')}")
    print(f"Status: {query_run.get('status')}")
    if query_run.get("submitted_at"):
        print(f"Submitted: {query_run.get('submitted_at')}")
    if query_run.get("finished_at"):
        print(f"Finished: {query_run.get('finished_at')}")
    if query_run.get("expires_at"):
        print(f"Expires: {query_run.get('expires_at')}")
    if query_run.get("error"):
        print(f"Error: {_extract_error_message(query_run.get('error')) or query_run.get('error')}")


def _print_results(response: dict, json_output: bool = False, limit: int = 50) -> None:
    if json_output:
        print(json.dumps(response, indent=2, sort_keys=True))
        return

    query_run = response.get("query_run")
    if query_run:
        print(f"Query run: {query_run.get('id')}")
        print(f"Status: {query_run.get('status')}")
        print()

    columns, rows = _columns_and_rows(response)
    print(f"Rows: {len(rows)}")
    if rows:
        print()
        _print_table(columns, rows, limit=limit)
    else:
        print("No rows returned.")


def _print_datafeed(response: dict, json_output: bool = False, limit: int = 50) -> None:
    _print_results(response, json_output=json_output, limit=limit)


def _add_query_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--var", action="append", help="Template variable: name=value. Commas create arrays.")
    parser.add_argument("--variables-json", help="Template variables as a JSON object")
    parser.add_argument("--timeout", type=int, default=300, help="Total wait timeout in seconds")
    parser.add_argument("--poll", type=float, default=1.0, help="Poll interval in seconds")
    parser.add_argument("--no-results", action="store_true", help="Only wait for completion; do not fetch JSON rows")
    parser.add_argument("--csv", help="Download the full result set as CSV to this path")
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    parser.add_argument("--limit", type=int, default=50, help="Rows to display in table output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DX API client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    whoami = subparsers.add_parser("whoami", help="Show the authenticated DX user when available")
    whoami.add_argument("--json", action="store_true")

    query = subparsers.add_parser("query", help="Run Data Studio SQL text")
    query.add_argument("sql", help="Read-only SELECT statement to run")
    _add_query_options(query)

    query_file = subparsers.add_parser("query-file", help="Run Data Studio SQL from a file")
    query_file.add_argument("path", help="SQL file path")
    _add_query_options(query_file)

    execute = subparsers.add_parser("execute", help="Submit a query run without waiting")
    execute.add_argument("sql", help="Read-only SELECT statement to run")
    execute.add_argument("--var", action="append", help="Template variable: name=value")
    execute.add_argument("--variables-json", help="Template variables as a JSON object")
    execute.add_argument("--json", action="store_true")

    status = subparsers.add_parser("status", help="Get query run status")
    status.add_argument("query_run_id")
    status.add_argument("--wait", action="store_true", help="Poll until the query run reaches a terminal status")
    status.add_argument("--timeout", type=int, default=300)
    status.add_argument("--poll", type=float, default=1.0)
    status.add_argument("--json", action="store_true")

    results = subparsers.add_parser("results", help="Get JSON results or download CSV for a completed query run")
    results.add_argument("query_run_id")
    results.add_argument("--csv", help="Download full CSV results to this path")
    results.add_argument("--json", action="store_true")
    results.add_argument("--limit", type=int, default=50)

    datafeed = subparsers.add_parser("datafeed", help="Get rows from a saved query datafeed")
    datafeed.add_argument("feed_token")
    datafeed.add_argument("--var", action="append", help="Datafeed variable: name=value")
    datafeed.add_argument("--columns", help="Comma-separated columns to include")
    datafeed.add_argument("--csv", help="Write returned rows to CSV")
    datafeed.add_argument("--json", action="store_true")
    datafeed.add_argument("--limit", type=int, default=50)

    ai = subparsers.add_parser("ai", help="Explain DX AI prompt-to-SQL support status")
    ai.add_argument("prompt", nargs="?", help="Natural-language prompt")

    return parser


def _make_client() -> DXClient:
    from sidekick.config import get_dx_config

    config = get_dx_config()
    return DXClient(
        api_base_url=config["api_base_url"],
        web_base_url=config["web_base_url"],
        token=config["token"]
    )


def _handle_query(client: DXClient, sql: str, args: argparse.Namespace) -> None:
    variables = _parse_variables(args)
    if args.csv:
        response = client.execute_and_wait(
            sql,
            variables=variables,
            timeout_seconds=args.timeout,
            poll_interval=args.poll,
            fetch_results=False
        )
        query_run_id = _query_run(response).get("id")
        output_path = client.download_query_results_csv(query_run_id, args.csv)
        print(f"Wrote {output_path}")
        return

    response = client.execute_and_wait(
        sql,
        variables=variables,
        timeout_seconds=args.timeout,
        poll_interval=args.poll,
        fetch_results=not args.no_results
    )
    if args.no_results:
        _print_query_run(response, json_output=args.json)
    else:
        _print_results(response, json_output=args.json, limit=args.limit)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "ai":
            raise RuntimeError(
                "DX AI prompt-to-SQL is available in the DX product UI, but DX does not "
                "currently expose a documented Web API or CLI command for prompt-based SQL "
                "generation. Use Data Studio AI in the browser, paste the generated SQL into "
                "`python3 -m sidekick.clients.dx query ...`, or use this client for official "
                "Data Studio query execution and downloads."
            )

        client = _make_client()

        if args.command == "whoami":
            response = client.whoami()
            if args.json:
                print(json.dumps(response, indent=2, sort_keys=True))
            else:
                user = response.get("user") or {}
                if user:
                    print(f"User: {user.get('name')} <{user.get('email')}>")
                    print(f"ID: {user.get('id')}")
                else:
                    print(json.dumps(response, indent=2, sort_keys=True))

        elif args.command == "query":
            _handle_query(client, args.sql, args)

        elif args.command == "query-file":
            sql = Path(args.path).read_text(encoding="utf-8")
            _handle_query(client, sql, args)

        elif args.command == "execute":
            response = client.execute_query(args.sql, variables=_parse_variables(args))
            _print_query_run(response, json_output=args.json)

        elif args.command == "status":
            if args.wait:
                response = client.wait_for_query_run(
                    args.query_run_id,
                    timeout_seconds=args.timeout,
                    poll_interval=args.poll
                )
            else:
                response = client.get_query_run(args.query_run_id)
            _print_query_run(response, json_output=args.json)

        elif args.command == "results":
            if args.csv:
                output_path = client.download_query_results_csv(args.query_run_id, args.csv)
                print(f"Wrote {output_path}")
            else:
                response = client.get_query_results(args.query_run_id)
                _print_results(response, json_output=args.json, limit=args.limit)

        elif args.command == "datafeed":
            response = client.get_datafeed(
                args.feed_token,
                variables=_parse_variables(args),
                columns=args.columns
            )
            if args.csv:
                columns, rows = _columns_and_rows(response)
                output_path = _write_rows_csv(args.csv, columns, rows)
                print(f"Wrote {output_path}")
            else:
                _print_datafeed(response, json_output=args.json, limit=args.limit)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
