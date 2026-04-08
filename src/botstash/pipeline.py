"""Orchestrates the full extract-classify-embed pipeline."""

from __future__ import annotations

from pathlib import Path

from botstash.anythingllm.client import AnythingLLMClient
from botstash.classifier.auto import classify
from botstash.ingester.imscc import extract_imscc
from botstash.ingester.transcript import ingest_transcripts
from botstash.models import BotStashConfig, TagEntry, read_tags


def run_extract(
    course_zip: Path, transcripts: Path, output_dir: Path
) -> list[TagEntry]:
    """Extract content from a course export and transcripts, classify it.

    Returns the list of classified tag entries. Writes text files and
    tags.json to output_dir.
    """
    # Collect resources from both sources
    records = extract_imscc(course_zip, output_dir=output_dir)
    records.extend(ingest_transcripts(transcripts))

    # Classify and write to staging
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

    # Load tags
    actual_tags_path = tags_path or (staging_dir / "tags.json")
    tags = read_tags(actual_tags_path)

    with AnythingLLMClient(config.url, config.key) as client:
        # Get or create workspace
        ws = client.get_or_create_workspace(workspace)
        slug = ws["slug"]

        # Optionally reset
        if reset:
            client.reset_workspace(slug)

        # Upload each document and move to workspace
        for tag in tags:
            extracted_path = Path(tag.extracted_as)
            if not extracted_path.exists():
                continue

            result = client.upload_document(extracted_path)
            documents = result.get("documents", [])
            locations = [doc["location"] for doc in documents if "location" in doc]
            if locations:
                client.move_to_workspace(slug, locations)

    return slug


def run_full(
    course_zip: Path,
    transcripts: Path,
    workspace: str,
    config: BotStashConfig,
    keep_staging: bool = False,
) -> str:
    """Run the complete extract-classify-embed pipeline.

    Returns the workspace slug.
    """
    output_dir = Path("./staging")
    run_extract(course_zip, transcripts, output_dir)
    slug = run_embed(output_dir, workspace, config)

    if not keep_staging:
        # Keep tags.json, remove text files
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
