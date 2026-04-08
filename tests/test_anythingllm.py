"""Tests for AnythingLLM client using mock HTTP transport."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from botstash.anythingllm.client import AnythingLLMClient, AnythingLLMError


def _mock_response(data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=data)


def test_list_workspaces() -> None:
    workspaces = [{"slug": "isys2001", "name": "ISYS2001"}]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        return _mock_response({"workspaces": workspaces})

    transport = httpx.MockTransport(handler)
    client = AnythingLLMClient.__new__(AnythingLLMClient)
    client._base_url = "http://localhost:3001"
    client._client = httpx.Client(
        base_url="http://localhost:3001",
        headers={"Authorization": "Bearer test-key"},
        transport=transport,
    )

    result = client.list_workspaces()
    assert len(result) == 1
    assert result[0]["slug"] == "isys2001"
    client.close()


def _make_client(handler) -> AnythingLLMClient:  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    client = AnythingLLMClient.__new__(AnythingLLMClient)
    client._base_url = "http://localhost:3001"
    client._client = httpx.Client(
        base_url="http://localhost:3001",
        headers={"Authorization": "Bearer test-key"},
        transport=transport,
    )
    return client


def test_get_workspace_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _mock_response({
            "workspaces": [{"slug": "isys2001", "name": "ISYS2001"}]
        })

    client = _make_client(handler)
    ws = client.get_workspace("isys2001")
    assert ws is not None
    assert ws["slug"] == "isys2001"
    client.close()


def test_get_workspace_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _mock_response({"workspaces": []})

    client = _make_client(handler)
    ws = client.get_workspace("nonexistent")
    assert ws is None
    client.close()


def test_create_workspace() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return _mock_response({
            "workspace": {"slug": body["name"].lower(), "name": body["name"]}
        })

    client = _make_client(handler)
    ws = client.create_workspace("ISYS2001")
    assert ws["slug"] == "isys2001"
    client.close()


def test_get_or_create_creates_when_missing() -> None:
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if "workspaces" in str(request.url) and request.method == "GET":
            return _mock_response({"workspaces": []})
        return _mock_response({
            "workspace": {"slug": "isys2001", "name": "ISYS2001"}
        })

    client = _make_client(handler)
    ws = client.get_or_create_workspace("ISYS2001")
    assert ws["slug"] == "isys2001"
    assert call_count["n"] >= 2  # list + create
    client.close()


def test_upload_document(tmp_path: Path) -> None:
    doc = tmp_path / "test.txt"
    doc.write_text("content")

    def handler(request: httpx.Request) -> httpx.Response:
        assert b"test.txt" in request.content
        return _mock_response({
            "success": True,
            "documents": [{"location": "custom-documents/test.txt"}],
        })

    client = _make_client(handler)
    result = client.upload_document(doc)
    assert result["success"] is True
    client.close()


def test_move_to_workspace() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["adds"] == ["custom-documents/test.txt"]
        return _mock_response({"workspace": {"slug": "isys2001"}})

    client = _make_client(handler)
    result = client.move_to_workspace(
        "isys2001", ["custom-documents/test.txt"]
    )
    assert "workspace" in result
    client.close()


def test_reset_workspace() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["deletes"] == ["*"]
        return _mock_response({"workspace": {"slug": "isys2001"}})

    client = _make_client(handler)
    result = client.reset_workspace("isys2001")
    assert "workspace" in result
    client.close()


def test_api_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "Forbidden"})

    client = _make_client(handler)
    with pytest.raises(AnythingLLMError, match="403"):
        client.list_workspaces()
    client.close()


def test_context_manager() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _mock_response({"workspaces": []})

    with _make_client(handler) as client:
        result = client.list_workspaces()
        assert result == []
