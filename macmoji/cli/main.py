import typer
from rich import print
from typing import Optional
from typing_extensions import Annotated
from pathlib import Path
import importlib.metadata
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

import macmoji.cli.create
from macmoji.config import BASE_EMOJI_FONT_PATH
from macmoji.font import (
    generate_base_emoji_ttf,
    generate_base_emoji_ttx,
    base_emoji_process_cleanup,
)

app = typer.Typer()
app.add_typer(macmoji.cli.create.app, name="create")


def _version_callback(value: bool) -> None:
    if value:
        print(f"MacMoji {importlib.metadata.version('macmoji')}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show the application's version and exit.",
        callback=_version_callback,
        is_eager=True,
    )
) -> None:
    """Create custom emoji fonts for macOS."""
    return


@app.command()
def generate_base_files(
    force: bool = typer.Option(
        True,
        "--force/--no-force",
        help="Create new files even if there are already generated ones available.",
    ),
) -> None:
    """
    Generate base emoji files to base future fonts on. This is done automatically when creating your first font, but can be run manually if needed.
    """
    if not force:  # Exit if there are already generated files
        required_files = [
            BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttf",
            BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttx",
            BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI.ttf",
            BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI.ttx",
        ]
        if all(map(Path.exists, required_files)):
            print("Emoji base files already generated, skipping.")
            return

    print("Generating emoji base files. This will most likely take a few minutes...\n")
    with Progress(
        SpinnerColumn(
            spinner_name="aesthetic", finished_text="[progress.spinner]Done![/]"
        ),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
    ) as progress:
        task_ttf = progress.add_task("Generating base emoji TTF files", total=1)
        generate_base_emoji_ttf()
        progress.update(task_ttf, completed=1)

        task_ttx_1 = progress.add_task(
            "Decompiling AppleColorEmoji.ttf into TTX", total=1
        )
        generate_base_emoji_ttx("AppleColorEmoji")
        progress.update(task_ttx_1, completed=1)

        task_ttx_2 = progress.add_task(
            "Decompiling .AppleColorEmojiUI.ttf into TTX", total=1
        )
        generate_base_emoji_ttx(".AppleColorEmojiUI")
        progress.update(task_ttx_2, completed=1)

        cleanup = progress.add_task("Cleaning up", total=1)
        base_emoji_process_cleanup()
        progress.update(cleanup, completed=1)

    print("\nSuccessfully generated emoji base files!")


@app.command()
def install(
    font: Annotated[Path, typer.Argument(help="`.ttc` font file to install")],
) -> None:
    """Install an emoji font to the current user's font directory."""
    raise NotImplementedError()


@app.command()
def uninstall() -> None:
    """Uninstall active custom emoji font from the current user's font directory."""
    raise NotImplementedError()
