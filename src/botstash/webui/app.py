"""FastAPI + Jinja2 WebUI."""

from __future__ import annotations

import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from botstash import __version__
from botstash.classifier.auto import VALID_TYPES, VALID_TYPES_ORDERED
from botstash.config import load_config
from botstash.models import read_tags, write_tags
from botstash.pipeline import run_embed, run_extract

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_SESSIONS_DIR = Path(tempfile.gettempdir()) / "botstash_sessions"


def create_app() -> FastAPI:
    """Create the BotStash FastAPI application."""
    app = FastAPI(title="BotStash", version=__version__)
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    templates.env.globals["botstash_version"] = __version__

    @app.get("/", response_class=HTMLResponse)
    async def upload_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "upload.html")

    @app.post("/extract")
    async def extract_action(
        request: Request,
        content_zip: UploadFile = File(...),  # noqa: B008
    ) -> HTMLResponse:
        form = await request.form()
        include_answers = form.get("include_answers") == "on"
        # Unchecked checkboxes are absent from form data, so absence
        # means the user turned recursion off
        recursive = form.get("recursive") == "on"

        session_id = str(uuid.uuid4())
        session_dir = _SESSIONS_DIR / session_id
        content_dir = session_dir / "content"
        content_dir.mkdir(parents=True, exist_ok=True)

        # Save and unzip uploaded content
        zip_path = session_dir / "upload.zip"
        with open(zip_path, "wb") as f:
            f.write(await content_zip.read())

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(content_dir)

        # Run extraction
        staging = session_dir / "staging"
        tags = run_extract(
            content_dir,
            staging,
            recursive=recursive,
            include_answers=include_answers,
        )

        return templates.TemplateResponse(
            request,
            "review.html",
            context={
                "session_id": session_id,
                "tags": tags,
                "valid_types": list(VALID_TYPES_ORDERED),
            },
        )

    @app.post("/embed/{session_id}")
    async def embed_action(
        request: Request,
        session_id: str,
        workspace: str = Form(...),  # noqa: B008
        url: str = Form(""),  # noqa: B008
        key: str = Form(""),  # noqa: B008
    ) -> HTMLResponse:
        session_dir = _SESSIONS_DIR / session_id
        staging = session_dir / "staging"

        # Read form-modified tags
        form_data = await request.form()
        tags_path = staging / "tags.json"
        tags = read_tags(tags_path)

        for i, tag in enumerate(tags):
            new_type = form_data.get(f"type_{i}")
            new_title = form_data.get(f"title_{i}")
            if new_type and str(new_type) in VALID_TYPES:
                tag.type = str(new_type)
            if new_title:
                tag.title = str(new_title)
        write_tags(tags, tags_path)

        config = load_config(
            url_override=url or None,
            key_override=key or None,
        )

        try:
            slug = run_embed(staging, workspace, config)
            return templates.TemplateResponse(
                request,
                "result.html",
                context={
                    "workspace": workspace,
                    "slug": slug,
                    "success": True,
                    "message": f"Embedded {len(tags)} items.",
                },
            )
        except Exception as e:
            return templates.TemplateResponse(
                request,
                "result.html",
                context={
                    "workspace": workspace,
                    "slug": "",
                    "success": False,
                    "message": str(e),
                },
            )

    return app
