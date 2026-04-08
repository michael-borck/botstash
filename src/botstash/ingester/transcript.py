"""VTT folder ingestion."""

from __future__ import annotations

from pathlib import Path

from botstash.extractors.vtt import extract_vtt
from botstash.models import ResourceRecord


def ingest_transcripts(folder_path: Path) -> list[ResourceRecord]:
    """Scan a folder for VTT files and extract text from each.

    Returns a list of ResourceRecord objects with file_type="vtt".
    """
    records: list[ResourceRecord] = []
    for vtt_file in sorted(folder_path.glob("*.vtt")):
        text = extract_vtt(vtt_file)
        title = vtt_file.stem.replace("_", " ").replace("-", " ").strip()
        records.append(
            ResourceRecord(
                source_file=vtt_file.name,
                extracted_text=text,
                file_type=".vtt",
                title=title,
            )
        )
    return records
