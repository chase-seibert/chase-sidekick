"""Databricks API client - SQL, saved queries, and Genie prompts."""

import argparse
import copy
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional


class DatabricksClient:
    """Databricks REST API client using native Python stdlib."""

    STATEMENT_TERMINAL_STATES = {"SUCCEEDED", "FAILED", "CANCELED", "CLOSED"}
    GENIE_TERMINAL_STATES = {"COMPLETED", "FAILED", "QUERY_RESULT_EXPIRED"}

    def __init__(
        self,
        host: str,
        token: str,
        warehouse_id: Optional[str] = None,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        genie_space_id: Optional[str] = None,
        timeout: int = 60
    ):
        """Initialize a Databricks client.

        Args:
            host: Databricks workspace URL.
            token: Databricks personal access token.
            warehouse_id: Optional default SQL warehouse ID.
            catalog: Optional default Unity Catalog catalog.
            schema: Optional default Unity Catalog schema.
            genie_space_id: Optional default AI/BI Genie Space ID.
            timeout: HTTP request timeout in seconds.
        """
        self.host = host.rstrip("/")
        self.token = token
        self.warehouse_id = warehouse_id
        self.catalog = catalog
        self.schema = schema
        self.genie_space_id = genie_space_id
        self.timeout = timeout
        self.api_call_count = 0

    def _auth_headers(self) -> dict:
        """Return standard Databricks API headers."""
        return {
            "Authorization": f"Bearer {self.token}",
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
        """Make a Databricks REST API request."""
        url = f"{self.host}{endpoint}"
        clean_params = {
            key: value
            for key, value in (params or {}).items()
            if value is not None
        }
        if clean_params:
            url += "?" + urllib.parse.urlencode(clean_params)

        data = json.dumps(json_data).encode("utf-8") if json_data is not None else None
        req = urllib.request.Request(url, data=data, headers=self._auth_headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                self.api_call_count += 1
                body = response.read().decode("utf-8")
                if not body or not body.strip():
                    return {}
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return {"raw": body}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            message = _extract_error_message(error_body)
            if e.code in (401, 403):
                raise ValueError(
                    f"Databricks authentication or authorization failed (HTTP {e.code}): {message}"
                )
            if 400 <= e.code < 500:
                raise ValueError(f"Databricks client error {e.code}: {message}")
            raise RuntimeError(f"Databricks server error {e.code}: {message}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Databricks network error: {e.reason}")

    def list_warehouses(self) -> list:
        """List SQL warehouses visible to the current token."""
        result = self._request("GET", "/api/2.0/sql/warehouses")
        return result.get("warehouses", [])

    def execute_statement(
        self,
        statement: str,
        warehouse_id: Optional[str] = None,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        parameters: Optional[list] = None,
        wait_timeout: str = "30s",
        on_wait_timeout: str = "CONTINUE",
        disposition: str = "INLINE",
        result_format: str = "JSON_ARRAY",
        byte_limit: Optional[int] = None,
        row_limit: Optional[int] = None
    ) -> dict:
        """Submit a SQL statement to the Statement Execution API."""
        selected_warehouse = warehouse_id or self.warehouse_id
        if not selected_warehouse:
            raise ValueError(
                "Missing Databricks SQL warehouse ID. "
                "Set DATABRICKS_WAREHOUSE_ID or pass --warehouse-id."
            )

        body = {
            "warehouse_id": selected_warehouse,
            "statement": statement,
            "wait_timeout": wait_timeout,
            "on_wait_timeout": on_wait_timeout,
            "disposition": disposition,
            "format": result_format
        }

        selected_catalog = catalog if catalog is not None else self.catalog
        selected_schema = schema if schema is not None else self.schema
        if selected_catalog:
            body["catalog"] = selected_catalog
        if selected_schema:
            body["schema"] = selected_schema
        if parameters:
            body["parameters"] = parameters
        if byte_limit is not None:
            body["byte_limit"] = byte_limit
        if row_limit is not None:
            body["row_limit"] = row_limit

        return self._request("POST", "/api/2.0/sql/statements", json_data=body)

    def get_statement(self, statement_id: str) -> dict:
        """Get statement status, manifest, and first result chunk."""
        quoted = urllib.parse.quote(statement_id, safe="")
        return self._request("GET", f"/api/2.0/sql/statements/{quoted}")

    def get_result_chunk(self, statement_id: str, chunk_index: int) -> dict:
        """Get a statement result chunk by index."""
        quoted = urllib.parse.quote(statement_id, safe="")
        return self._request(
            "GET",
            f"/api/2.0/sql/statements/{quoted}/result/chunks/{chunk_index}"
        )

    def cancel_statement(self, statement_id: str) -> dict:
        """Cancel a running statement."""
        quoted = urllib.parse.quote(statement_id, safe="")
        return self._request(
            "POST",
            f"/api/2.0/sql/statements/{quoted}/cancel",
            json_data={}
        )

    def wait_for_statement(
        self,
        statement_id: str,
        timeout_seconds: int = 300,
        poll_interval: float = 2.0,
        fetch_all_chunks: bool = True
    ) -> dict:
        """Poll a statement until it reaches a terminal state."""
        deadline = time.time() + timeout_seconds
        response = self.get_statement(statement_id)

        while _statement_state(response) not in self.STATEMENT_TERMINAL_STATES:
            if time.time() >= deadline:
                raise TimeoutError(
                    f"Timed out waiting for Databricks statement {statement_id}"
                )
            time.sleep(poll_interval)
            response = self.get_statement(statement_id)

        if fetch_all_chunks and _statement_state(response) == "SUCCEEDED":
            response = self.collect_all_chunks(response)
        return response

    def execute_and_wait(
        self,
        statement: str,
        warehouse_id: Optional[str] = None,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        parameters: Optional[list] = None,
        wait_timeout: str = "30s",
        timeout_seconds: int = 300,
        poll_interval: float = 2.0,
        fetch_all_chunks: bool = True,
        byte_limit: Optional[int] = None,
        row_limit: Optional[int] = None
    ) -> dict:
        """Execute a SQL statement and wait for the final response."""
        response = self.execute_statement(
            statement=statement,
            warehouse_id=warehouse_id,
            catalog=catalog,
            schema=schema,
            parameters=parameters,
            wait_timeout=wait_timeout,
            byte_limit=byte_limit,
            row_limit=row_limit
        )

        state = _statement_state(response)
        if state not in self.STATEMENT_TERMINAL_STATES:
            statement_id = response.get("statement_id")
            if not statement_id:
                raise RuntimeError(f"Databricks returned no statement_id: {response}")
            response = self.wait_for_statement(
                statement_id,
                timeout_seconds=timeout_seconds,
                poll_interval=poll_interval,
                fetch_all_chunks=fetch_all_chunks
            )
        elif fetch_all_chunks and state == "SUCCEEDED":
            response = self.collect_all_chunks(response)

        _raise_for_statement_error(response)
        return response

    def collect_all_chunks(self, statement_response: dict) -> dict:
        """Return a copy of a statement response with all INLINE chunks merged."""
        statement_id = statement_response.get("statement_id")
        result = statement_response.get("result") or {}
        if not statement_id or "data_array" not in result:
            return statement_response

        merged = copy.deepcopy(statement_response)
        merged_result = merged.setdefault("result", {})
        all_rows = list(merged_result.get("data_array") or [])
        seen = {merged_result.get("chunk_index", 0)}

        next_chunk_index = merged_result.get("next_chunk_index")
        while next_chunk_index is not None and next_chunk_index not in seen:
            chunk_result = self.get_result_chunk(statement_id, next_chunk_index)
            chunk_payload = chunk_result.get("result", chunk_result)
            seen.add(chunk_payload.get("chunk_index", next_chunk_index))
            all_rows.extend(chunk_payload.get("data_array") or [])
            next_chunk_index = chunk_payload.get("next_chunk_index")

        if next_chunk_index is None:
            chunks = (
                merged.get("manifest", {})
                .get("chunks", [])
            )
            for chunk in chunks:
                chunk_index = chunk.get("chunk_index")
                if chunk_index is None or chunk_index in seen:
                    continue
                chunk_result = self.get_result_chunk(statement_id, chunk_index)
                chunk_payload = chunk_result.get("result", chunk_result)
                seen.add(chunk_index)
                all_rows.extend(chunk_payload.get("data_array") or [])

        merged_result["data_array"] = all_rows
        merged_result["next_chunk_index"] = None
        total_row_count = merged.get("manifest", {}).get("total_row_count")
        if total_row_count is not None:
            merged_result["row_count"] = total_row_count
        return merged

    def list_queries(
        self,
        filter_text: Optional[str] = None,
        page_size: int = 100,
        max_pages: int = 10
    ) -> list:
        """List saved Databricks SQL queries accessible to the user."""
        queries = []
        page_token = None

        for _ in range(max_pages):
            response = self._request(
                "GET",
                "/api/2.0/sql/queries",
                params={"page_size": page_size, "page_token": page_token}
            )
            page_queries = (
                response.get("results")
                or response.get("queries")
                or response.get("items")
                or []
            )
            queries.extend(page_queries)
            page_token = response.get("next_page_token")
            if not page_token:
                break

        if filter_text:
            needle = filter_text.lower()
            queries = [
                query for query in queries
                if needle in _query_name(query).lower()
                or needle in (query.get("id") or "").lower()
            ]
        return queries

    def get_query(self, query_id: str) -> dict:
        """Get a saved SQL query by ID."""
        quoted = urllib.parse.quote(query_id, safe="")
        return _unwrap_query(self._request("GET", f"/api/2.0/sql/queries/{quoted}"))

    def find_query(self, identifier: str) -> dict:
        """Find a saved query by ID, exact name, or unique name substring."""
        if _looks_like_query_id(identifier):
            try:
                return self.get_query(identifier)
            except ValueError:
                pass

        queries = self.list_queries(filter_text=identifier, max_pages=20)
        exact_matches = [
            query for query in queries
            if _query_name(query).lower() == identifier.lower()
            or (query.get("id") or "").lower() == identifier.lower()
        ]
        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(exact_matches) > 1:
            names = ", ".join(_query_name(query) for query in exact_matches[:10])
            raise ValueError(f"Multiple saved queries matched exactly: {names}")
        if len(queries) == 1:
            return queries[0]
        if queries:
            names = ", ".join(_query_name(query) for query in queries[:10])
            raise ValueError(f"Multiple saved queries matched '{identifier}': {names}")
        raise ValueError(f"No saved Databricks query matched '{identifier}'")

    def run_query(
        self,
        identifier: str,
        parameters: Optional[list] = None,
        timeout_seconds: int = 300,
        poll_interval: float = 2.0,
        fetch_all_chunks: bool = True
    ) -> dict:
        """Run a saved Databricks SQL query by ID or name."""
        query = self.find_query(identifier)
        statement = query.get("query_text")
        if not statement:
            query = self.get_query(query.get("id"))
            statement = query.get("query_text")
        if not statement:
            raise ValueError(f"Saved query '{identifier}' has no query_text")

        return self.execute_and_wait(
            statement=statement,
            warehouse_id=query.get("warehouse_id") or self.warehouse_id,
            catalog=query.get("catalog") or self.catalog,
            schema=query.get("schema") or self.schema,
            parameters=parameters,
            timeout_seconds=timeout_seconds,
            poll_interval=poll_interval,
            fetch_all_chunks=fetch_all_chunks
        )

    @staticmethod
    def extract_dashboard_id(identifier: str) -> str:
        """Extract a dashboard ID from a Databricks dashboard URL or raw ID."""
        if "/dashboardsv3/" in identifier:
            return identifier.split("/dashboardsv3/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        if "/lakeview/dashboards/" in identifier:
            return identifier.split("/lakeview/dashboards/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        return identifier.split("?", 1)[0].strip("/")

    def get_dashboard(self, dashboard_id_or_url: str) -> dict:
        """Get a Lakeview/AI-BI dashboard definition."""
        dashboard_id = self.extract_dashboard_id(dashboard_id_or_url)
        quoted = urllib.parse.quote(dashboard_id, safe="")
        return self._request("GET", f"/api/2.0/lakeview/dashboards/{quoted}")

    def get_published_dashboard(self, dashboard_id_or_url: str) -> dict:
        """Get published dashboard metadata."""
        dashboard_id = self.extract_dashboard_id(dashboard_id_or_url)
        quoted = urllib.parse.quote(dashboard_id, safe="")
        return self._request("GET", f"/api/2.0/lakeview/dashboards/{quoted}/published")

    def get_dashboard_definition(self, dashboard_id_or_url: str) -> dict:
        """Get and parse a dashboard's serialized definition."""
        dashboard = self.get_dashboard(dashboard_id_or_url)
        serialized = dashboard.get("serialized_dashboard")
        if not serialized:
            raise ValueError("Dashboard response did not include serialized_dashboard")
        try:
            definition = json.loads(serialized)
        except json.JSONDecodeError as e:
            raise ValueError(f"Dashboard serialized_dashboard is not valid JSON: {e}")
        return {
            "dashboard": dashboard,
            "definition": definition
        }

    def get_dashboard_datasets(self, dashboard_id_or_url: str) -> list:
        """Return SQL datasets from a dashboard definition."""
        payload = self.get_dashboard_definition(dashboard_id_or_url)
        datasets = []
        for dataset in payload["definition"].get("datasets") or []:
            query_lines = dataset.get("queryLines") or []
            sql = "\n".join(query_lines).strip()
            if not sql:
                continue
            datasets.append({
                "name": dataset.get("name"),
                "display_name": dataset.get("displayName") or dataset.get("display_name"),
                "sql": sql,
                "raw": dataset
            })
        return datasets

    def run_dashboard_datasets(
        self,
        dashboard_id_or_url: str,
        dataset_names: Optional[list] = None,
        row_limit: Optional[int] = 1000,
        timeout_seconds: int = 300,
        poll_interval: float = 2.0,
        fetch_all_chunks: bool = True,
        stop_on_error: bool = False
    ) -> dict:
        """Execute each SQL dataset from a dashboard definition."""
        dashboard_id = self.extract_dashboard_id(dashboard_id_or_url)
        payload = self.get_dashboard_definition(dashboard_id)
        dashboard = payload["dashboard"]

        published = {}
        try:
            published = self.get_published_dashboard(dashboard_id)
        except Exception:
            published = {}

        warehouse_id = (
            published.get("warehouse_id")
            or dashboard.get("warehouse_id")
            or self.warehouse_id
        )
        if not warehouse_id:
            raise ValueError(
                "Dashboard has no warehouse_id and DATABRICKS_WAREHOUSE_ID is not configured"
            )

        requested = set(dataset_names or [])
        dataset_results = []
        for dataset in self.get_dashboard_datasets(dashboard_id):
            if requested and dataset["name"] not in requested and dataset["display_name"] not in requested:
                continue

            result = {
                "name": dataset["name"],
                "display_name": dataset["display_name"],
                "sql": dataset["sql"]
            }
            try:
                response = self.execute_and_wait(
                    statement=dataset["sql"],
                    warehouse_id=warehouse_id,
                    timeout_seconds=timeout_seconds,
                    poll_interval=poll_interval,
                    fetch_all_chunks=fetch_all_chunks,
                    row_limit=row_limit
                )
                result.update({
                    "statement_id": response.get("statement_id"),
                    "state": _statement_state(response),
                    "row_count": _statement_total_rows(response),
                    "columns": _statement_columns(response),
                    "rows": _statement_rows(response),
                    "rows_fetched": len(_statement_rows(response))
                })
            except Exception as e:
                result.update({
                    "state": "ERROR",
                    "error": str(e),
                    "row_count": None,
                    "columns": [],
                    "rows": [],
                    "rows_fetched": 0
                })
                if stop_on_error:
                    dataset_results.append(result)
                    raise
            dataset_results.append(result)

        return {
            "dashboard_id": dashboard_id,
            "display_name": dashboard.get("display_name"),
            "path": dashboard.get("path"),
            "warehouse_id": warehouse_id,
            "published": published,
            "row_limit": row_limit,
            "datasets": dataset_results
        }

    def list_genie_spaces(self, page_size: int = 100, max_pages: int = 10) -> list:
        """List Genie Spaces accessible to the current token."""
        spaces = []
        page_token = None

        for _ in range(max_pages):
            response = self._request(
                "GET",
                "/api/2.0/genie/spaces",
                params={"page_size": page_size, "page_token": page_token}
            )
            spaces.extend(
                response.get("spaces")
                or response.get("genie_spaces")
                or response.get("items")
                or []
            )
            page_token = response.get("next_page_token")
            if not page_token:
                break
        return spaces

    def get_genie_space(self, space_id: str) -> dict:
        """Get a Genie Space by ID."""
        quoted = urllib.parse.quote(space_id, safe="")
        return self._request("GET", f"/api/2.0/genie/spaces/{quoted}")

    def start_genie_conversation(self, space_id: str, content: str) -> dict:
        """Start a Genie conversation with an initial prompt."""
        quoted = urllib.parse.quote(space_id, safe="")
        return self._request(
            "POST",
            f"/api/2.0/genie/spaces/{quoted}/start-conversation",
            json_data={"content": content}
        )

    def create_genie_message(
        self,
        space_id: str,
        conversation_id: str,
        content: str
    ) -> dict:
        """Send a follow-up message in a Genie conversation."""
        quoted_space = urllib.parse.quote(space_id, safe="")
        quoted_conversation = urllib.parse.quote(conversation_id, safe="")
        return self._request(
            "POST",
            f"/api/2.0/genie/spaces/{quoted_space}/conversations/"
            f"{quoted_conversation}/messages",
            json_data={"content": content}
        )

    def get_genie_message(
        self,
        space_id: str,
        conversation_id: str,
        message_id: str
    ) -> dict:
        """Get a Genie conversation message."""
        quoted_space = urllib.parse.quote(space_id, safe="")
        quoted_conversation = urllib.parse.quote(conversation_id, safe="")
        quoted_message = urllib.parse.quote(message_id, safe="")
        return self._request(
            "GET",
            f"/api/2.0/genie/spaces/{quoted_space}/conversations/"
            f"{quoted_conversation}/messages/{quoted_message}"
        )

    def get_message_attachment_query_result(
        self,
        space_id: str,
        conversation_id: str,
        message_id: str,
        attachment_id: str,
        fetch_all_chunks: bool = True
    ) -> dict:
        """Get the SQL result for a Genie message query attachment."""
        quoted_space = urllib.parse.quote(space_id, safe="")
        quoted_conversation = urllib.parse.quote(conversation_id, safe="")
        quoted_message = urllib.parse.quote(message_id, safe="")
        quoted_attachment = urllib.parse.quote(attachment_id, safe="")
        response = self._request(
            "GET",
            f"/api/2.0/genie/spaces/{quoted_space}/conversations/{quoted_conversation}/"
            f"messages/{quoted_message}/attachments/{quoted_attachment}/query-result"
        )
        return self._collect_genie_statement_chunks(response, fetch_all_chunks)

    def execute_message_attachment_query(
        self,
        space_id: str,
        conversation_id: str,
        message_id: str,
        attachment_id: str,
        fetch_all_chunks: bool = True
    ) -> dict:
        """Execute or re-execute a Genie message query attachment."""
        quoted_space = urllib.parse.quote(space_id, safe="")
        quoted_conversation = urllib.parse.quote(conversation_id, safe="")
        quoted_message = urllib.parse.quote(message_id, safe="")
        quoted_attachment = urllib.parse.quote(attachment_id, safe="")
        response = self._request(
            "POST",
            f"/api/2.0/genie/spaces/{quoted_space}/conversations/{quoted_conversation}/"
            f"messages/{quoted_message}/attachments/{quoted_attachment}/execute-query",
            json_data={}
        )
        return self._collect_genie_statement_chunks(response, fetch_all_chunks)

    def wait_for_genie_message(
        self,
        space_id: str,
        conversation_id: str,
        message_id: str,
        timeout_seconds: int = 300,
        poll_interval: float = 2.0
    ) -> dict:
        """Poll a Genie message until it reaches a terminal state."""
        deadline = time.time() + timeout_seconds
        message = self.get_genie_message(space_id, conversation_id, message_id)
        status = _genie_status(message)

        while status not in self.GENIE_TERMINAL_STATES:
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for Genie message {message_id}")
            time.sleep(poll_interval)
            message = self.get_genie_message(space_id, conversation_id, message_id)
            status = _genie_status(message)

        if status == "FAILED":
            error = message.get("error") or {}
            raise RuntimeError(error.get("message") or f"Genie message failed: {message}")
        return message

    def ask_genie(
        self,
        prompt: str,
        space_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        timeout_seconds: int = 300,
        poll_interval: float = 2.0,
        fetch_results: bool = True
    ) -> dict:
        """Ask Genie a prompt and optionally fetch generated query results."""
        selected_space = space_id or self.genie_space_id
        if not selected_space:
            raise ValueError(
                "Missing Genie Space ID. Set DATABRICKS_GENIE_SPACE_ID or pass --space-id."
            )

        if conversation_id:
            start_response = self.create_genie_message(selected_space, conversation_id, prompt)
        else:
            start_response = self.start_genie_conversation(selected_space, prompt)

        resolved_conversation_id = _extract_conversation_id(start_response) or conversation_id
        message_id = _extract_message_id(start_response)
        if not resolved_conversation_id or not message_id:
            raise RuntimeError(f"Genie response did not include conversation/message IDs: {start_response}")

        message = self.wait_for_genie_message(
            selected_space,
            resolved_conversation_id,
            message_id,
            timeout_seconds=timeout_seconds,
            poll_interval=poll_interval
        )

        results = []
        if fetch_results:
            message_status = _genie_status(message)
            for attachment in _genie_attachments(message):
                if "query" not in attachment or not attachment.get("attachment_id"):
                    continue
                try:
                    if message_status == "QUERY_RESULT_EXPIRED":
                        query_result = self.execute_message_attachment_query(
                            selected_space,
                            resolved_conversation_id,
                            message_id,
                            attachment["attachment_id"]
                        )
                    else:
                        query_result = self.get_message_attachment_query_result(
                            selected_space,
                            resolved_conversation_id,
                            message_id,
                            attachment["attachment_id"]
                        )
                    results.append({
                        "attachment_id": attachment["attachment_id"],
                        "result": query_result
                    })
                except Exception as e:
                    results.append({
                        "attachment_id": attachment["attachment_id"],
                        "error": str(e)
                    })

        return {
            "space_id": selected_space,
            "conversation_id": resolved_conversation_id,
            "message_id": message_id,
            "message": message,
            "results": results
        }

    def _collect_genie_statement_chunks(self, response: dict, fetch_all_chunks: bool) -> dict:
        """Merge chunks inside a Genie query-result response."""
        if not fetch_all_chunks:
            return response
        statement_response = response.get("statement_response")
        if not statement_response:
            return response
        response = copy.deepcopy(response)
        response["statement_response"] = self.collect_all_chunks(statement_response)
        return response


def _extract_error_message(error_body: str) -> str:
    """Extract a compact Databricks error message."""
    if not error_body:
        return "No error body returned"
    try:
        data = json.loads(error_body)
    except json.JSONDecodeError:
        return error_body

    pieces = []
    for key in ("error_code", "message", "error", "details"):
        value = data.get(key)
        if value:
            pieces.append(str(value))
    return ": ".join(pieces) if pieces else error_body


def _statement_state(response: dict) -> Optional[str]:
    return (response.get("status") or {}).get("state")


def _raise_for_statement_error(response: dict) -> None:
    state = _statement_state(response)
    if state in ("FAILED", "CANCELED", "CLOSED"):
        status = response.get("status") or {}
        error = status.get("error") or {}
        message = error.get("message") or status.get("error_code") or status
        raise RuntimeError(f"Databricks statement {state}: {message}")


def _unwrap_query(response: dict) -> dict:
    if isinstance(response.get("query"), dict):
        return response["query"]
    return response


def _query_name(query: dict) -> str:
    return (
        query.get("display_name")
        or query.get("name")
        or query.get("title")
        or query.get("id")
        or "Untitled query"
    )


def _looks_like_query_id(identifier: str) -> bool:
    return bool(re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}$", identifier))


def _extract_conversation_id(response: dict) -> Optional[str]:
    conversation = response.get("conversation") or {}
    return (
        response.get("conversation_id")
        or conversation.get("conversation_id")
        or conversation.get("id")
    )


def _extract_message_id(response: dict) -> Optional[str]:
    message = response.get("message") or {}
    return (
        response.get("message_id")
        or message.get("message_id")
        or message.get("id")
    )


def _genie_status(message: dict) -> Optional[str]:
    return message.get("status") or (message.get("message") or {}).get("status")


def _genie_attachments(message: dict) -> list:
    return message.get("attachments") or (message.get("message") or {}).get("attachments") or []


def _statement_payload(response: dict) -> dict:
    return response.get("statement_response") or response


def _statement_columns(response: dict) -> list:
    payload = _statement_payload(response)
    columns = (
        payload.get("manifest", {})
        .get("schema", {})
        .get("columns", [])
    )
    return [
        column.get("name") or column.get("column_name") or f"col_{index + 1}"
        for index, column in enumerate(columns)
    ]


def _statement_rows(response: dict) -> list:
    payload = _statement_payload(response)
    return (payload.get("result") or {}).get("data_array") or []


def _statement_total_rows(response: dict) -> Optional[int]:
    payload = _statement_payload(response)
    manifest = payload.get("manifest") or {}
    result = payload.get("result") or {}
    return manifest.get("total_row_count") or result.get("row_count")


def _parse_parameters(args: argparse.Namespace) -> Optional[list]:
    parameters = []

    if getattr(args, "params_json", None):
        parsed = json.loads(args.params_json)
        parameters.extend(_normalize_parameters(parsed))

    for raw_param in getattr(args, "param", None) or []:
        if "=" not in raw_param:
            raise ValueError(f"Parameter must be name=value or name:TYPE=value: {raw_param}")
        left, value = raw_param.split("=", 1)
        if ":" in left:
            name, param_type = left.split(":", 1)
            parameters.append({"name": name, "value": value, "type": param_type})
        else:
            parameters.append({"name": left, "value": value})

    return parameters or None


def _normalize_parameters(parsed) -> list:
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [
            {"name": key, "value": str(value)}
            for key, value in parsed.items()
        ]
    raise ValueError("--params-json must be a JSON object or list")


def _truncate(value, max_width: int = 48) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\n", " ")
    if len(text) <= max_width:
        return text
    return text[:max_width - 3] + "..."


def _print_table(columns: list, rows: list, limit: int = 50) -> None:
    display_rows = rows[:limit]
    string_rows = [[_truncate(value) for value in row] for row in display_rows]
    widths = [
        min(48, max(len(str(column)), *(len(row[index]) for row in string_rows or [[""] * len(columns)])))
        for index, column in enumerate(columns)
    ]

    header = " | ".join(str(column).ljust(widths[index]) for index, column in enumerate(columns))
    divider = "-+-".join("-" * width for width in widths)
    print(header)
    print(divider)
    for row in string_rows:
        print(" | ".join(row[index].ljust(widths[index]) for index in range(len(columns))))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more rows not shown")


def _print_statement_response(response: dict, json_output: bool = False, limit: int = 50) -> None:
    if json_output:
        print(json.dumps(response, indent=2, sort_keys=True))
        return

    payload = _statement_payload(response)
    statement_id = payload.get("statement_id")
    state = _statement_state(payload)
    if statement_id or state:
        bits = []
        if statement_id:
            bits.append(f"Statement: {statement_id}")
        if state:
            bits.append(f"State: {state}")
        print(" | ".join(bits))

    columns = _statement_columns(response)
    rows = _statement_rows(response)
    total = _statement_total_rows(response)
    if total is not None:
        print(f"Rows: {total}")
    if columns and rows:
        print()
        _print_table(columns, rows, limit=limit)
    elif state == "SUCCEEDED":
        print("No rows returned.")


def _print_warehouses(warehouses: list, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps({"warehouses": warehouses}, indent=2, sort_keys=True))
        return
    rows = [
        [
            warehouse.get("id"),
            warehouse.get("name"),
            warehouse.get("state"),
            warehouse.get("cluster_size"),
            warehouse.get("warehouse_type")
        ]
        for warehouse in warehouses
    ]
    _print_table(["ID", "Name", "State", "Size", "Type"], rows, limit=len(rows) or 1)


def _print_queries(queries: list, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps({"queries": queries}, indent=2, sort_keys=True))
        return
    rows = [
        [
            query.get("id"),
            _query_name(query),
            query.get("warehouse_id"),
            query.get("owner_user_name"),
            query.get("update_time")
        ]
        for query in queries
    ]
    if not rows:
        print("No saved queries found.")
        return
    _print_table(["ID", "Name", "Warehouse", "Owner", "Updated"], rows, limit=len(rows))


def _print_dashboard_results(response: dict, json_output: bool = False, show_sql: bool = False) -> None:
    if json_output:
        print(json.dumps(response, indent=2, sort_keys=True))
        return

    print(f"Dashboard: {response.get('display_name')} ({response.get('dashboard_id')})")
    if response.get("path"):
        print(f"Path: {response['path']}")
    print(f"Warehouse: {response.get('warehouse_id')}")
    if response.get("row_limit") is not None:
        print(f"Row limit per dataset: {response.get('row_limit')}")
    print()

    rows = []
    for dataset in response.get("datasets") or []:
        columns = ", ".join(dataset.get("columns") or [])
        rows.append([
            dataset.get("name"),
            dataset.get("display_name"),
            dataset.get("state"),
            dataset.get("row_count"),
            dataset.get("rows_fetched"),
            columns
        ])
    _print_table(["Dataset", "Display Name", "State", "Rows", "Fetched", "Columns"], rows, limit=len(rows) or 1)

    errors = [dataset for dataset in response.get("datasets") or [] if dataset.get("error")]
    if errors:
        print()
        print("Errors:")
        for dataset in errors:
            print(f"- {dataset.get('name')}: {dataset.get('error')}")

    if show_sql:
        for dataset in response.get("datasets") or []:
            print()
            print(f"-- {dataset.get('name')} / {dataset.get('display_name')}")
            print(dataset.get("sql") or "")


def _attachment_text(attachment: dict) -> Optional[str]:
    text = attachment.get("text")
    if isinstance(text, dict):
        return text.get("content") or text.get("text") or text.get("value")
    if isinstance(text, str):
        return text
    return None


def _attachment_query(attachment: dict) -> tuple:
    query = attachment.get("query")
    if not isinstance(query, dict):
        return None, None
    description = query.get("description") or query.get("title")
    sql = query.get("query") or query.get("statement") or query.get("sql")
    return description, sql


def _print_genie_response(response: dict, json_output: bool = False, limit: int = 50) -> None:
    if json_output:
        print(json.dumps(response, indent=2, sort_keys=True))
        return

    print(f"Space: {response.get('space_id')}")
    print(f"Conversation: {response.get('conversation_id')}")
    print(f"Message: {response.get('message_id')}")

    message = response.get("message") or {}
    status = _genie_status(message)
    if status:
        print(f"Status: {status}")

    for attachment in _genie_attachments(message):
        text = _attachment_text(attachment)
        if text:
            print()
            print(text)

        description, sql = _attachment_query(attachment)
        if description:
            print()
            print(f"Query: {description}")
        if sql:
            print()
            print("```sql")
            print(sql)
            print("```")

    for result in response.get("results") or []:
        if result.get("error"):
            print()
            print(f"Attachment {result.get('attachment_id')} error: {result['error']}")
            continue
        print()
        print(f"Attachment {result.get('attachment_id')} result:")
        _print_statement_response(result.get("result") or {}, limit=limit)


def _add_sql_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--warehouse-id", help="Override DATABRICKS_WAREHOUSE_ID")
    parser.add_argument("--catalog", help="Override DATABRICKS_CATALOG")
    parser.add_argument("--schema", help="Override DATABRICKS_SCHEMA")
    parser.add_argument("--param", action="append", help="SQL parameter: name=value or name:TYPE=value")
    parser.add_argument("--params-json", help="SQL parameters as JSON object or list")
    parser.add_argument("--wait", default="30s", help="Initial Statement API wait_timeout, e.g. 30s")
    parser.add_argument("--timeout", type=int, default=300, help="Total wait timeout in seconds")
    parser.add_argument("--poll", type=float, default=2.0, help="Poll interval in seconds")
    parser.add_argument("--byte-limit", type=int, help="Statement API byte_limit")
    parser.add_argument("--row-limit", type=int, help="Statement API row_limit")
    parser.add_argument("--no-fetch-all", action="store_true", help="Do not fetch additional result chunks")
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    parser.add_argument("--limit", type=int, default=50, help="Rows to display in table output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Databricks API client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    warehouses = subparsers.add_parser("warehouses", help="List SQL warehouses")
    warehouses.add_argument("--json", action="store_true")

    query = subparsers.add_parser("query", help="Run SQL text")
    query.add_argument("sql", help="SQL statement to run")
    _add_sql_options(query)

    query_file = subparsers.add_parser("query-file", help="Run SQL from a file")
    query_file.add_argument("path", help="SQL file path")
    _add_sql_options(query_file)

    status = subparsers.add_parser("status", help="Get statement status/results")
    status.add_argument("statement_id")
    status.add_argument("--timeout", type=int, default=300)
    status.add_argument("--poll", type=float, default=2.0)
    status.add_argument("--no-fetch-all", action="store_true")
    status.add_argument("--json", action="store_true")
    status.add_argument("--limit", type=int, default=50)

    cancel = subparsers.add_parser("cancel", help="Cancel a statement")
    cancel.add_argument("statement_id")
    cancel.add_argument("--json", action="store_true")

    reports = subparsers.add_parser("list-reports", help="List saved SQL queries")
    reports.add_argument("filter", nargs="?", help="Optional name or ID filter")
    reports.add_argument("--page-size", type=int, default=100)
    reports.add_argument("--max-pages", type=int, default=10)
    reports.add_argument("--json", action="store_true")

    get_report = subparsers.add_parser("get-report", help="Get a saved SQL query")
    get_report.add_argument("identifier", help="Saved query ID, exact name, or unique name substring")
    get_report.add_argument("--json", action="store_true")

    run_report = subparsers.add_parser("run-report", help="Run a saved SQL query")
    run_report.add_argument("identifier", help="Saved query ID, exact name, or unique name substring")
    run_report.add_argument("--param", action="append", help="SQL parameter: name=value or name:TYPE=value")
    run_report.add_argument("--params-json", help="SQL parameters as JSON object or list")
    run_report.add_argument("--timeout", type=int, default=300)
    run_report.add_argument("--poll", type=float, default=2.0)
    run_report.add_argument("--no-fetch-all", action="store_true")
    run_report.add_argument("--json", action="store_true")
    run_report.add_argument("--limit", type=int, default=50)

    dashboard_results = subparsers.add_parser(
        "dashboard-results",
        help="Execute SQL datasets from a Lakeview/AI-BI dashboard"
    )
    dashboard_results.add_argument("dashboard", help="Dashboard URL or ID")
    dashboard_results.add_argument("--dataset", action="append", help="Dataset name/displayName to run")
    dashboard_results.add_argument("--row-limit", type=int, default=1000, help="Rows to fetch per dataset")
    dashboard_results.add_argument("--timeout", type=int, default=300)
    dashboard_results.add_argument("--poll", type=float, default=2.0)
    dashboard_results.add_argument("--no-fetch-all", action="store_true")
    dashboard_results.add_argument("--stop-on-error", action="store_true")
    dashboard_results.add_argument("--show-sql", action="store_true")
    dashboard_results.add_argument("--json", action="store_true")

    spaces = subparsers.add_parser("genie-spaces", help="List Genie Spaces")
    spaces.add_argument("--page-size", type=int, default=100)
    spaces.add_argument("--max-pages", type=int, default=10)
    spaces.add_argument("--json", action="store_true")

    ask = subparsers.add_parser("ask", help="Ask Genie to generate and execute a query")
    ask.add_argument("prompt", help="Natural-language question")
    ask.add_argument("--space-id", help="Override DATABRICKS_GENIE_SPACE_ID")
    ask.add_argument("--conversation-id", help="Continue an existing Genie conversation")
    ask.add_argument("--timeout", type=int, default=300)
    ask.add_argument("--poll", type=float, default=2.0)
    ask.add_argument("--no-results", action="store_true", help="Do not fetch SQL attachment results")
    ask.add_argument("--json", action="store_true")
    ask.add_argument("--limit", type=int, default=50)

    genie_result = subparsers.add_parser("genie-result", help="Get a Genie query attachment result")
    genie_result.add_argument("space_id")
    genie_result.add_argument("conversation_id")
    genie_result.add_argument("message_id")
    genie_result.add_argument("attachment_id")
    genie_result.add_argument("--execute", action="store_true", help="Execute or re-execute the attachment query")
    genie_result.add_argument("--no-fetch-all", action="store_true")
    genie_result.add_argument("--json", action="store_true")
    genie_result.add_argument("--limit", type=int, default=50)

    return parser


def _make_client() -> DatabricksClient:
    from sidekick.config import get_databricks_config

    config = get_databricks_config()
    return DatabricksClient(
        host=config["host"],
        token=config["token"],
        warehouse_id=config.get("warehouse_id"),
        catalog=config.get("catalog"),
        schema=config.get("schema"),
        genie_space_id=config.get("genie_space_id")
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    start_time = time.time()

    try:
        client = _make_client()

        if args.command == "warehouses":
            _print_warehouses(client.list_warehouses(), json_output=args.json)

        elif args.command == "query":
            response = client.execute_and_wait(
                statement=args.sql,
                warehouse_id=args.warehouse_id,
                catalog=args.catalog,
                schema=args.schema,
                parameters=_parse_parameters(args),
                wait_timeout=args.wait,
                timeout_seconds=args.timeout,
                poll_interval=args.poll,
                fetch_all_chunks=not args.no_fetch_all,
                byte_limit=args.byte_limit,
                row_limit=args.row_limit
            )
            _print_statement_response(response, json_output=args.json, limit=args.limit)

        elif args.command == "query-file":
            sql = Path(args.path).read_text(encoding="utf-8")
            response = client.execute_and_wait(
                statement=sql,
                warehouse_id=args.warehouse_id,
                catalog=args.catalog,
                schema=args.schema,
                parameters=_parse_parameters(args),
                wait_timeout=args.wait,
                timeout_seconds=args.timeout,
                poll_interval=args.poll,
                fetch_all_chunks=not args.no_fetch_all,
                byte_limit=args.byte_limit,
                row_limit=args.row_limit
            )
            _print_statement_response(response, json_output=args.json, limit=args.limit)

        elif args.command == "status":
            response = client.wait_for_statement(
                args.statement_id,
                timeout_seconds=args.timeout,
                poll_interval=args.poll,
                fetch_all_chunks=not args.no_fetch_all
            )
            _print_statement_response(response, json_output=args.json, limit=args.limit)

        elif args.command == "cancel":
            response = client.cancel_statement(args.statement_id)
            if args.json:
                print(json.dumps(response, indent=2, sort_keys=True))
            else:
                print(f"Canceled {args.statement_id}")

        elif args.command == "list-reports":
            queries = client.list_queries(
                filter_text=args.filter,
                page_size=args.page_size,
                max_pages=args.max_pages
            )
            _print_queries(queries, json_output=args.json)

        elif args.command == "get-report":
            query = client.find_query(args.identifier)
            if query.get("id") and not query.get("query_text"):
                query = client.get_query(query["id"])
            if args.json:
                print(json.dumps(query, indent=2, sort_keys=True))
            else:
                _print_queries([query])
                if query.get("query_text"):
                    print()
                    print(query["query_text"])

        elif args.command == "run-report":
            response = client.run_query(
                args.identifier,
                parameters=_parse_parameters(args),
                timeout_seconds=args.timeout,
                poll_interval=args.poll,
                fetch_all_chunks=not args.no_fetch_all
            )
            _print_statement_response(response, json_output=args.json, limit=args.limit)

        elif args.command == "dashboard-results":
            response = client.run_dashboard_datasets(
                args.dashboard,
                dataset_names=args.dataset,
                row_limit=args.row_limit,
                timeout_seconds=args.timeout,
                poll_interval=args.poll,
                fetch_all_chunks=not args.no_fetch_all,
                stop_on_error=args.stop_on_error
            )
            _print_dashboard_results(response, json_output=args.json, show_sql=args.show_sql)

        elif args.command == "genie-spaces":
            spaces = client.list_genie_spaces(
                page_size=args.page_size,
                max_pages=args.max_pages
            )
            if args.json:
                print(json.dumps({"spaces": spaces}, indent=2, sort_keys=True))
            else:
                rows = [
                    [
                        space.get("space_id") or space.get("id"),
                        space.get("title") or space.get("display_name"),
                        space.get("warehouse_id"),
                        space.get("description")
                    ]
                    for space in spaces
                ]
                _print_table(["ID", "Title", "Warehouse", "Description"], rows, limit=len(rows) or 1)

        elif args.command == "ask":
            response = client.ask_genie(
                prompt=args.prompt,
                space_id=args.space_id,
                conversation_id=args.conversation_id,
                timeout_seconds=args.timeout,
                poll_interval=args.poll,
                fetch_results=not args.no_results
            )
            _print_genie_response(response, json_output=args.json, limit=args.limit)

        elif args.command == "genie-result":
            if args.execute:
                response = client.execute_message_attachment_query(
                    args.space_id,
                    args.conversation_id,
                    args.message_id,
                    args.attachment_id,
                    fetch_all_chunks=not args.no_fetch_all
                )
            else:
                response = client.get_message_attachment_query_result(
                    args.space_id,
                    args.conversation_id,
                    args.message_id,
                    args.attachment_id,
                    fetch_all_chunks=not args.no_fetch_all
                )
            _print_statement_response(response, json_output=args.json, limit=args.limit)

        elapsed_time = time.time() - start_time
        print(
            f"\n[Debug] API calls: {client.api_call_count}, Time: {elapsed_time:.2f}s",
            file=sys.stderr
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
