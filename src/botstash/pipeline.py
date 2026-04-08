"""Orchestrates the full extract-classify-embed pipeline."""

from __future__ import annotations

import logging
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from botstash.anythingllm.client import AnythingLLMClient
from botstash.classifier.auto import classify
from botstash.extractors import extract_file
from botstash.extractors.qti import extract_qti
from botstash.ingester.imscc import extract_imscc
from botstash.models import BotStashConfig, ResourceRecord, TagEntry, read_tags

logger = logging.getLogger(__name__)

_MAX_ZIP_DEPTH = 3


def scan_folder(
    root: Path,
    *,
    recursive: bool = True,
    include_answers: bool = False,
    _zip_depth: int = 0,
) -> list[ResourceRecord]:
    """Recursively scan a folder for extractable content.

    Handles:
    - .pdf, .docx, .pptx, .vtt: extract via extractor registry
    - .xml: try QTI extraction, skip if not QTI
    - .zip, .imscc: check for imsmanifest.xml (use IMSCC parser),
      otherwise unzip and recurse
    - All other files: skip silently

    Args:
        root: Directory to scan.
        recursive: Walk subdirectories (default True).
        include_answers: Include answer choices in quiz extraction.
        _zip_depth: Internal counter to prevent ZIP bombs.
    """
    records: list[ResourceRecord] = []

    if not root.is_dir():
        return records

    if recursive:
        all_files = sorted(root.rglob("*"))
    else:
        all_files = sorted(f for f in root.iterdir() if f.is_file())

    for file_path in all_files:
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()

        # ZIP / IMSCC archives
        if suffix in (".zip", ".imscc"):
            if _zip_depth >= _MAX_ZIP_DEPTH:
                logger.warning(
                    "Skipping %s: max ZIP nesting depth reached", file_path
                )
                continue
            records.extend(
                _process_zip(
                    file_path,
                    include_answers=include_answers,
                    zip_depth=_zip_depth,
                )
            )

        # XML files: try QTI extraction
        elif suffix == ".xml":
            try:
                text = extract_qti(
                    file_path, include_answers=include_answers
                )
                if text:
                    records.append(
                        ResourceRecord(
                            source_file=str(file_path),
                            extracted_text=text,
                            file_type=".xml",
                            title=file_path.stem.replace("_", " "),
                        )
                    )
            except ET.ParseError:
                pass

        # Standard extractable files
        elif suffix in (".pdf", ".docx", ".pptx", ".vtt"):
            text = extract_file(file_path)
            if text:
                records.append(
                    ResourceRecord(
                        source_file=str(file_path),
                        extracted_text=text,
                        file_type=suffix,
                        title=file_path.stem.replace("_", " ").replace(
                            "-", " "
                        ),
                    )
                )

    return records


def _process_zip(
    zip_path: Path,
    *,
    include_answers: bool = False,
    zip_depth: int = 0,
) -> list[ResourceRecord]:
    """Process a ZIP file — use IMSCC parser if manifest found, else recurse."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            has_manifest = "imsmanifest.xml" in zf.namelist()
    except zipfile.BadZipFile:
        logger.warning("Skipping invalid ZIP: %s", zip_path)
        return []

    if has_manifest:
        return extract_imscc(zip_path)

    # Not IMSCC — unzip to temp dir and scan contents
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)  # noqa: S202
        return scan_folder(
            tmp,
            recursive=True,
            include_answers=include_answers,
            _zip_depth=zip_depth + 1,
        )


def run_extract(
    source: Path,
    output_dir: Path,
    *,
    recursive: bool = True,
    include_answers: bool = False,
) -> list[TagEntry]:
    """Extract content from a source folder, classify it.

    Args:
        source: Directory (or single file) to scan.
        output_dir: Where to write extracted text and tags.json.
        recursive: Walk subdirectories.
        include_answers: Include quiz answer choices.

    Returns the list of classified tag entries.
    """
    records = scan_folder(
        source,
        recursive=recursive,
        include_answers=include_answers,
    )
    return classify(records, output_dir)


def run_embed(
    staging_dir: Path,
    workspace: str,
    config: BotStashConfig,
    tags_path: Path | None = None,
    reset: bool = False,
) -> str:
    """Upload staged documents to an AnythingLLM workspace.

    Returns the workspace slug.
    """
    if not config.url or not config.key:
        msg = (
            "AnythingLLM URL and API key are required. "
            "Set via .botstash.env, environment variables, or CLI flags."
        )
        raise ValueError(msg)

    actual_tags_path = tags_path or (staging_dir / "tags.json")
    tags = read_tags(actual_tags_path)

    with AnythingLLMClient(config.url, config.key) as client:
        ws = client.get_or_create_workspace(workspace)
        slug = ws["slug"]

        if reset:
            client.reset_workspace(slug)

        for tag in tags:
            extracted_path = Path(tag.extracted_as)
            if not extracted_path.exists():
                continue

            result = client.upload_document(extracted_path)
            documents = result.get("documents", [])
            locations = [
                doc["location"] for doc in documents if "location" in doc
            ]
            if locations:
                client.move_to_workspace(slug, locations)

    return slug


def run_full(
    source: Path,
    workspace: str,
    config: BotStashConfig,
    keep_staging: bool = False,
) -> str:
    """Run the complete extract-classify-embed pipeline.

    Returns the workspace slug.
    """
    output_dir = Path("./staging")
    run_extract(
        source,
        output_dir,
        recursive=config.recursive,
        include_answers=config.include_answers,
    )
    slug = run_embed(output_dir, workspace, config)

    if not keep_staging:
        for f in output_dir.iterdir():
            if f.name != "tags.json" and f.is_file():
                f.unlink()

    return slug


def get_chatbot_code(
    workspace: str, config: BotStashConfig
) -> str:
    """Retrieve the chatbot embed code for a workspace."""
    if not config.url or not config.key:
        msg = "AnythingLLM URL and API key are required."
        raise ValueError(msg)

    with AnythingLLMClient(config.url, config.key) as client:
        ws = client.get_workspace(workspace.lower().replace(" ", "-"))
        if not ws:
            msg = f"Workspace '{workspace}' not found."
            raise ValueError(msg)

        embed = client.get_embed_config(ws["slug"])
        if embed:
            return str(embed)

        return (
            f"Embed config not available via API.\n"
            f"Visit {config.url}/settings/embed to configure "
            f"and copy the embed code for workspace '{workspace}'."
        )
