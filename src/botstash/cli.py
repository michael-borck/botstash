"""Click-based CLI entry points."""

from __future__ import annotations

from pathlib import Path

import click

from botstash import __version__
from botstash.config import load_config


@click.group()
@click.version_option(version=__version__, prog_name="botstash")
def cli() -> None:
    """BotStash — LMS course content to AnythingLLM chatbot pipeline."""


@cli.command()
@click.argument("course_zip", type=click.Path(exists=True))
@click.argument("transcripts", type=click.Path(exists=True))
@click.option("--workspace", required=True, help="AnythingLLM workspace name.")
@click.option("--url", envvar="ANYTHINGLLM_URL", help="AnythingLLM instance URL.")
@click.option("--key", envvar="ANYTHINGLLM_KEY", help="AnythingLLM API key.")
@click.option("--keep-staging", is_flag=True, help="Keep staging files after embed.")
def run(
    course_zip: str,
    transcripts: str,
    workspace: str,
    url: str | None,
    key: str | None,
    keep_staging: bool,
) -> None:
    """Run the full extract-classify-embed pipeline."""
    from botstash.pipeline import run_full

    config = load_config(url_override=url, key_override=key)
    try:
        slug = run_full(
            Path(course_zip),
            Path(transcripts),
            workspace,
            config,
            keep_staging=keep_staging,
        )
        click.echo(f"Done! Workspace '{slug}' is ready.")
        click.echo(f"Run 'botstash chatbot {workspace}' to get the embed code.")
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command()
@click.argument("course_zip", type=click.Path(exists=True))
@click.argument("transcripts", type=click.Path(exists=True))
@click.option("--output", default="./staging", help="Output directory.")
def extract(course_zip: str, transcripts: str, output: str) -> None:
    """Extract and auto-classify content from a course export."""
    from botstash.pipeline import run_extract

    output_dir = Path(output)
    try:
        tags = run_extract(Path(course_zip), Path(transcripts), output_dir)
        click.echo(f"Extracted {len(tags)} items to {output_dir}/")
        for tag in tags:
            click.echo(f"  [{tag.type}] {tag.title}")
        click.echo(f"\nTags written to {output_dir / 'tags.json'}")
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command()
@click.argument("staging_dir", type=click.Path(exists=True))
@click.option("--workspace", required=True, help="AnythingLLM workspace name.")
@click.option("--tags", "tags_path", type=click.Path(exists=True))
@click.option("--reset", is_flag=True, help="Clear workspace before uploading.")
@click.option("--url", envvar="ANYTHINGLLM_URL", help="AnythingLLM instance URL.")
@click.option("--key", envvar="ANYTHINGLLM_KEY", help="AnythingLLM API key.")
def embed(
    staging_dir: str,
    workspace: str,
    tags_path: str | None,
    reset: bool,
    url: str | None,
    key: str | None,
) -> None:
    """Embed staged documents into an AnythingLLM workspace."""
    from botstash.pipeline import run_embed

    config = load_config(url_override=url, key_override=key)
    try:
        slug = run_embed(
            Path(staging_dir),
            workspace,
            config,
            tags_path=Path(tags_path) if tags_path else None,
            reset=reset,
        )
        click.echo(f"Embedded to workspace '{slug}'.")
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command()
@click.argument("workspace")
@click.option("--url", envvar="ANYTHINGLLM_URL", help="AnythingLLM instance URL.")
@click.option("--key", envvar="ANYTHINGLLM_KEY", help="AnythingLLM API key.")
def chatbot(workspace: str, url: str | None, key: str | None) -> None:
    """Retrieve the chatbot embed code for a workspace."""
    from botstash.pipeline import get_chatbot_code

    config = load_config(url_override=url, key_override=key)
    try:
        code = get_chatbot_code(workspace, config)
        click.echo(code)
    except Exception as e:
        raise click.ClickException(str(e)) from e


@cli.command()
def init() -> None:
    """Scaffold a .botstash.env configuration file."""
    env_path = Path(".botstash.env")
    if env_path.exists():  # noqa: SIM102
        if not click.confirm(".botstash.env exists. Overwrite?"):
            return

    url = click.prompt("AnythingLLM URL", default="http://localhost:3001")
    key = click.prompt("AnythingLLM API key")

    env_path.write_text(
        f"ANYTHINGLLM_URL={url}\nANYTHINGLLM_KEY={key}\n"
    )
    click.echo(f"Written to {env_path}")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to.")
@click.option("--port", default=8000, help="Port to bind to.")
def serve(host: str, port: int) -> None:
    """Launch the BotStash WebUI."""
    try:
        import uvicorn

        from botstash.webui.app import create_app

        app = create_app()
        uvicorn.run(app, host=host, port=port)
    except ImportError as e:
        raise click.ClickException(
            "WebUI dependencies missing. Install with: pip install botstash[webui]"
        ) from e
