"""Tests for persona provisioning."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from botstash.anythingllm.client import AnythingLLMClient
from botstash.personas import (
    PersonaManifest,
    PersonaSpec,
    load_manifest,
    provision_persona,
)


def _mock_client(handler) -> AnythingLLMClient:  # type: ignore[no-untyped-def]
    client = AnythingLLMClient.__new__(AnythingLLMClient)
    client._base_url = "http://localhost:3001"  # type: ignore[attr-defined]
    client._client = httpx.Client(
        base_url="http://localhost:3001",
        headers={"Authorization": "Bearer test-key"},
        transport=httpx.MockTransport(handler),
    )
    return client


def test_load_manifest(tmp_path: Path) -> None:
    prompt = tmp_path / "p.txt"
    prompt.write_text("be the persona")
    back = tmp_path / "back.md"
    back.write_text("backstory")
    shared = tmp_path / "shared.md"
    shared.write_text("shared")
    manifest_file = tmp_path / "personas.json"
    manifest_file.write_text(
        json.dumps(
            {
                "shared_docs": ["shared.md"],
                "allowlist_domains": ["example.org"],
                "personas": [
                    {
                        "slug": "alice",
                        "prompt": "p.txt",
                        "backstory": "back.md",
                        "page": "page.qmd",
                    }
                ],
            }
        )
    )

    manifest = load_manifest(manifest_file)

    assert isinstance(manifest, PersonaManifest)
    assert len(manifest.personas) == 1
    spec = manifest.personas[0]
    assert spec.slug == "alice"
    assert spec.prompt_file == prompt
    assert spec.backstory_file == back
    assert spec.page_file == tmp_path / "page.qmd"
    assert manifest.shared_docs == [shared]
    assert manifest.allowlist_domains == ["example.org"]


def test_provision_persona(tmp_path: Path) -> None:
    prompt = tmp_path / "p.txt"
    prompt.write_text("you are Alice")
    back = tmp_path / "back.md"
    back.write_text("alice backstory")
    page = tmp_path / "page.qmd"
    page.write_text('<div data-embed-id="OLD"></div>')

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if request.method == "GET" and path == "/api/v1/workspaces":
            return httpx.Response(200, json={"workspaces": []})
        if request.method == "POST" and path == "/api/v1/workspace/new":
            return httpx.Response(
                200, json={"workspace": {"slug": "alice", "name": "alice"}}
            )
        if (
            request.method == "POST"
            and path == "/api/v1/workspace/alice/update"
        ):
            return httpx.Response(200, json={"workspace": {"slug": "alice"}})
        if request.method == "POST" and path == "/api/v1/document/upload":
            return httpx.Response(
                200,
                json={"documents": [{"location": "custom-documents/back.md"}]},
            )
        if (
            request.method == "POST"
            and path == "/api/v1/workspace/alice/update-embeddings"
        ):
            return httpx.Response(200, json={"workspace": {"id": 1}})
        if (
            request.method == "POST"
            and path == "/api/v1/workspace/alice/embed/new"
        ):
            return httpx.Response(200, json={"embed": {"uuid": "NEW-UUID"}})
        return httpx.Response(404, json={})

    client = _mock_client(handler)
    spec = PersonaSpec(
        slug="alice",
        prompt_file=prompt,
        backstory_file=back,
        page_file=page,
    )
    embed_uuid = provision_persona(
        spec, client, shared_docs=[], allowlist_domains=["example.org"]
    )
    client.close()

    assert embed_uuid == "NEW-UUID"
    assert 'data-embed-id="NEW-UUID"' in page.read_text()
    assert "/api/v1/workspace/alice/update" in calls
    assert "/api/v1/workspace/alice/embed/new" in calls
