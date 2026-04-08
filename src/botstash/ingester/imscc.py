"""Unzip and walk IMSCC/common cartridge structure."""

from __future__ import annotations

import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from botstash.extractors import extract_file
from botstash.extractors.url_tracker import extract_urls, log_urls
from botstash.models import ResourceRecord

# Common IMSCC manifest namespaces
_MANIFEST_NS = [
    "http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1",
    "http://www.imsglobal.org/xsd/imsccv1p2/imscp_v1p1",
    "http://www.imsglobal.org/xsd/imsccv1p3/imscp_v1p1",
    "http://www.imsglobal.org/xsd/imscp_v1p1",
]


def _find_with_ns(root: ET.Element, local_name: str) -> list[ET.Element]:
    """Find elements by local name, trying all known namespaces."""
    results: list[ET.Element] = []
    # Try namespaced
    for ns in _MANIFEST_NS:
        results.extend(root.iter(f"{{{ns}}}{local_name}"))
    # Try without namespace
    results.extend(
        elem for elem in root.iter(local_name) if "}" not in elem.tag
    )
    return results


def _get_title(resource_elem: ET.Element, root: ET.Element) -> str:
    """Try to extract a human-readable title for a resource."""
    identifier = resource_elem.get("identifier", "")

    # Look for matching item in organization that references this resource
    for item in _find_with_ns(root, "item"):
        if item.get("identifierref") == identifier:
            for title_elem in _find_with_ns(item, "title"):
                if title_elem.text:
                    return title_elem.text.strip()

    # Fallback: use the href filename
    href = resource_elem.get("href", "")
    if href:
        return Path(href).stem.replace("_", " ").replace("-", " ")

    return identifier


def extract_imscc(
    zip_path: Path, output_dir: Path | None = None
) -> list[ResourceRecord]:
    """Extract resources from an IMSCC/common cartridge ZIP file.

    Parses imsmanifest.xml, walks all resources, and extracts text
    using the appropriate extractor for each file type.
    """
    records: list[ResourceRecord] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)  # noqa: S202

        # Find manifest
        manifest_path = tmp / "imsmanifest.xml"
        if not manifest_path.exists():
            return records

        tree = ET.parse(manifest_path)  # noqa: S314
        root = tree.getroot()

        # Process each resource
        for resource in _find_with_ns(root, "resource"):
            href = resource.get("href", "")
            res_type = resource.get("type", "")
            title = _get_title(resource, root)

            if not href:
                # Collect file hrefs from child <file> elements
                file_elems = _find_with_ns(resource, "file")
                if file_elems:
                    href = file_elems[0].get("href", "")

            if not href:
                continue

            file_path = tmp / href
            if not file_path.exists():
                continue

            # Handle HTML content items
            if file_path.suffix.lower() in (".html", ".htm"):
                html_content = file_path.read_text(errors="replace")

                # Track URLs found in HTML
                urls = extract_urls(html_content)
                if urls and output_dir:
                    log_urls(
                        urls, title, output_dir / "urls_log.txt"
                    )

                # For URL-only resources, record as video_url
                if urls and len(html_content.strip()) < 500:
                    for url in urls:
                        records.append(
                            ResourceRecord(
                                source_file=href,
                                extracted_text=url,
                                file_type="url",
                                title=title,
                            )
                        )
                    continue

            # Handle QTI assessments
            if "qti" in res_type.lower() or "assessment" in res_type.lower():
                # Find the actual QTI XML file
                qti_files = list((file_path.parent).glob("*.xml"))
                if file_path.suffix.lower() == ".xml":
                    qti_files = [file_path]
                for qf in qti_files:
                    from botstash.extractors.qti import extract_qti

                    try:
                        text = extract_qti(qf)
                        if text:
                            records.append(
                                ResourceRecord(
                                    source_file=href,
                                    extracted_text=text,
                                    file_type=".xml",
                                    title=title,
                                )
                            )
                    except ET.ParseError:
                        continue
                continue

            # Try standard extractors
            text = extract_file(file_path)
            if text:
                records.append(
                    ResourceRecord(
                        source_file=href,
                        extracted_text=text,
                        file_type=file_path.suffix.lower(),
                        title=title,
                    )
                )

    return records
