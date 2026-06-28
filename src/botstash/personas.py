"""Persona chatbot provisioning for AnythingLLM.

Provision multiple in-character persona bots from a manifest. Each persona
gets its own workspace, a system-prompt identity, a personal backstory plus
any shared documents, and an embed widget whose id is written back into the
persona's page file.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from botstash.anythingllm.client import AnythingLLMClient
from botstash.models import BotStashConfig

logger = logging.getLogger(__name__)

_EMBED_ID_RE = re.compile(r'data-embed-id="[^"]*"')


@dataclass
class PersonaSpec:
    """A single persona bot to provision."""

    slug: str
    prompt_file: Path
    backstory_file: Path | None = None
    page_file: Path | None = None
    extra_docs: list[Path] = field(default_factory=list)


@dataclass
class PersonaManifest:
    """Personas plus documents and domains shared by all of them."""

    personas: list[PersonaSpec]
    shared_docs: list[Path] = field(default_factory=list)
    allowlist_domains: list[str] = field(default_factory=list)


def load_manifest(path: Path) -> PersonaManifest:
    """Load a persona manifest from a JSON file.

    Paths in the manifest are resolved relative to the manifest's parent.
    Schema::

        {
          "shared_docs": ["company_overview.md"],
          "allowlist_domains": ["tessera.locoensayo.org"],
          "personas": [
            {"slug": "priya_nair", "prompt": "bots/priya_nair/prompt.txt",
             "backstory": "_backstories/priya_nair_cfo.md",
             "page": "bots/priya_nair/index.qmd",
             "extra_docs": ["data_breach_overview.md"]}
          ]
        }
    """
    root = path.parent
    raw: dict[str, Any] = json.loads(path.read_text())

    def _resolve(value: str) -> Path:
        resolved = Path(value)
        return resolved if resolved.is_absolute() else root / resolved

    personas = [
        PersonaSpec(
            slug=str(entry["slug"]),
            prompt_file=_resolve(str(entry["prompt"])),
            backstory_file=_resolve(str(entry["backstory"]))
            if entry.get("backstory")
            else None,
            page_file=_resolve(str(entry["page"]))
            if entry.get("page")
            else None,
            extra_docs=[_resolve(str(d)) for d in entry.get("extra_docs", [])],
        )
        for entry in raw.get("personas", [])
    ]
    return PersonaManifest(
        personas=personas,
        shared_docs=[_resolve(str(d)) for d in raw.get("shared_docs", [])],
        allowlist_domains=[str(d) for d in raw.get("allowlist_domains", [])],
    )


def _write_embed_id(page_file: Path, embed_uuid: str) -> bool:
    """Write an embed UUID into a page file's data-embed-id attribute."""
    if not page_file.exists():
        logger.warning("embed writeback: %s not found", page_file)
        return False
    text = page_file.read_text()
    new_text, count = _EMBED_ID_RE.subn(
        f'data-embed-id="{embed_uuid}"', text
    )
    if not count:
        logger.warning("no data-embed-id found in %s", page_file.name)
        return False
    page_file.write_text(new_text)
    return True


def provision_persona(
    spec: PersonaSpec,
    client: AnythingLLMClient,
    shared_docs: list[Path],
    allowlist_domains: list[str],
    reset: bool = False,
) -> str:
    """Provision a single persona with an existing client.

    Returns the embed uuid (empty string if no embed was created).
    """
    prompt = spec.prompt_file.read_text()
    workspace = client.get_or_create_workspace(spec.slug)
    slug = str(workspace["slug"])

    client.set_system_prompt(slug, prompt)
    if reset:
        client.reset_workspace(slug)

    doc_paths: list[Path] = []
    if spec.backstory_file:
        doc_paths.append(spec.backstory_file)
    doc_paths.extend(shared_docs)
    doc_paths.extend(spec.extra_docs)

    locations: list[str] = []
    for doc in doc_paths:
        if not doc.exists():
            logger.warning("missing doc for %s: %s", spec.slug, doc)
            continue
        result = client.upload_document(doc)
        for document in result.get("documents", []):
            location = document.get("location")
            if location:
                locations.append(str(location))
    if locations:
        client.move_to_workspace(slug, locations)

    embed = client.create_embed(slug, allowlist_domains)
    embed_uuid = str(embed.get("uuid", ""))
    if embed_uuid and spec.page_file:
        _write_embed_id(spec.page_file, embed_uuid)
    return embed_uuid


def provision_personas(
    manifest: PersonaManifest,
    config: BotStashConfig,
    reset: bool = False,
) -> dict[str, str]:
    """Provision every persona in a manifest. Returns slug -> embed uuid."""
    if not config.url or not config.key:
        msg = (
            "AnythingLLM URL and API key are required. "
            "Set via .botstash.env, environment variables, or CLI flags."
        )
        raise ValueError(msg)

    embeds: dict[str, str] = {}
    with AnythingLLMClient(config.url, config.key) as client:
        for spec in manifest.personas:
            embeds[spec.slug] = provision_persona(
                spec,
                client,
                manifest.shared_docs,
                manifest.allowlist_domains,
                reset=reset,
            )
    return embeds
