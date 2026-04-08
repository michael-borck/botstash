"""Click-based CLI entry points."""

import click

from botstash import __version__


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
    click.echo("botstash run: not yet implemented")


@cli.command()
@click.argument("course_zip", type=click.Path(exists=True))
@click.argument("transcripts", type=click.Path(exists=True))
@click.option("--output", default="./staging", help="Output directory.")
def extract(course_zip: str, transcripts: str, output: str) -> None:
    """Extract and auto-classify content from a course export."""
    click.echo("botstash extract: not yet implemented")


@cli.command()
@click.argument("staging_dir", type=click.Path(exists=True))
@click.option("--workspace", required=True, help="AnythingLLM workspace name.")
@click.option("--tags", type=click.Path(exists=True), help="Path to tags.json.")
@click.option("--reset", is_flag=True, help="Clear workspace before uploading.")
def embed(staging_dir: str, workspace: str, tags: str | None, reset: bool) -> None:
    """Embed staged documents into an AnythingLLM workspace."""
    click.echo("botstash embed: not yet implemented")


@cli.command()
@click.argument("workspace")
def chatbot(workspace: str) -> None:
    """Retrieve the chatbot embed code for a workspace."""
    click.echo("botstash chatbot: not yet implemented")


@cli.command()
def init() -> None:
    """Scaffold a .botstash.env configuration file."""
    click.echo("botstash init: not yet implemented")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to.")
@click.option("--port", default=8000, help="Port to bind to.")
def serve(host: str, port: int) -> None:
    """Launch the BotStash WebUI."""
    click.echo("botstash serve: not yet implemented")
