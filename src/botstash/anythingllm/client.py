"""AnythingLLM REST API wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


class AnythingLLMError(Exception):
    """Raised when an AnythingLLM API call fails."""


class AnythingLLMClient:
    """Synchronous client for the AnythingLLM REST API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    def __enter__(self) -> AnythingLLMClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make an API request and return the JSON response."""
        resp = self._client.request(method, path, **kwargs)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            msg = f"AnythingLLM API error: {e.response.status_code} {e.response.text}"
            raise AnythingLLMError(msg) from e
        return resp.json()  # type: ignore[no-any-return]

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List all workspaces."""
        data = self._request("GET", "/api/v1/workspaces")
        return data.get("workspaces", [])  # type: ignore[no-any-return]

    def get_workspace(self, slug: str) -> dict[str, Any] | None:
        """Find a workspace by slug."""
        for ws in self.list_workspaces():
            if ws.get("slug") == slug:
                return ws
        return None

    def create_workspace(self, name: str) -> dict[str, Any]:
        """Create a new workspace."""
        data = self._request(
            "POST", "/api/v1/workspace/new", json={"name": name}
        )
        return data.get("workspace", data)  # type: ignore[no-any-return]

    def get_or_create_workspace(self, name: str) -> dict[str, Any]:
        """Get an existing workspace by name/slug or create a new one."""
        slug = name.lower().replace(" ", "-")
        existing = self.get_workspace(slug)
        if existing:
            return existing
        return self.create_workspace(name)

    def upload_document(self, file_path: Path) -> dict[str, Any]:
        """Upload a document file to AnythingLLM.

        Returns the upload response containing the document location.
        """
        with open(file_path, "rb") as f:
            return self._request(
                "POST",
                "/api/v1/document/upload",
                files={"file": (file_path.name, f)},
            )

    def move_to_workspace(
        self, slug: str, doc_locations: list[str]
    ) -> dict[str, Any]:
        """Move uploaded documents into a workspace for embedding."""
        return self._request(
            "POST",
            f"/api/v1/workspace/{slug}/update-embeddings",
            json={"adds": doc_locations},
        )

    def reset_workspace(self, slug: str) -> dict[str, Any]:
        """Remove all documents from a workspace."""
        return self._request(
            "POST",
            f"/api/v1/workspace/{slug}/update-embeddings",
            json={"adds": [], "deletes": ["*"]},
        )

    def get_embed_config(self, slug: str) -> dict[str, Any] | None:
        """Retrieve the embed/chatbot configuration for a workspace."""
        try:
            data = self._request(
                "GET", f"/api/v1/workspace/{slug}/embed"
            )
            return data
        except AnythingLLMError:
            return None
