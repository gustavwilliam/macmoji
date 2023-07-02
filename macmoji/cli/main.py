import importlib.metadata
from functools import partial
from pathlib import Path
from typing import Optional

import humanize
import typer
from rich import print
from rich.progress import Progress
from typing_extensions import Annotated

import macmoji.cli.create
from macmoji.config import BASE_EMOJI_FONT_PATH, DEFAULT_ASSETS_PATH, TTX_SIZE
from macmoji.font import (
    base_emoji_process_cleanup,
    generate_base_emoji_ttf,
    generate_base_emoji_ttx,
)
from macmoji.utils import ProgressTask

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
            BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttx",
            BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI.ttx",
        ]
        if all(map(Path.exists, required_files)):
            print("Emoji base files already generated, skipping.")
            return

    print("Generating emoji base files. This will most likely take a few minutes...\n")

    with Progress() as progress:
        task_ttf = ProgressTask(
            description="Generating TTF files",
            progress=progress,
            target=partial(generate_base_emoji_ttf),
            output_file=BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttf",
            output_size=TTX_SIZE,
        )  # Dooesn't update incrementally, but still gives a slightly nicer progress bar than the alternative
        task_ttx_1 = ProgressTask(
            description="Decompiling AppleColorEmoji.ttf",
            progress=progress,
            target=partial(generate_base_emoji_ttx, "AppleColorEmoji"),
            output_file=BASE_EMOJI_FONT_PATH / "AppleColorEmoji-tmp.ttx",
            output_size=TTX_SIZE,
        )
        task_ttx_2 = ProgressTask(
            description="Decompiling .AppleColorEmojiUI.ttf",
            progress=progress,
            target=partial(generate_base_emoji_ttx, ".AppleColorEmojiUI"),
            output_file=BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI-tmp.ttx",
            output_size=TTX_SIZE,
        )

        task_ttf.start()
        task_ttf.join()  # Wait for TTF generation to finish before starting TTX generation
        task_ttx_1.start()
        task_ttx_2.start()
        task_ttx_1.join()
        task_ttx_2.join()

    base_emoji_process_cleanup()
    print("\nSuccessfully generated emoji base files and cleaned up!")


@app.command()
def clear_cache(
    include_base_files: bool = typer.Option(
        False,
        "--include-base-files",
        help="Also clear the emoji base files. Frees more than 1GB of memory, but adds multiple minutes to the next time an emoji font is generated. This cannot be undone.",
    ),
) -> None:
    """Clears the cache of generated emoji assets."""
    memory_cleared = base_emoji_process_cleanup()

    for file in DEFAULT_ASSETS_PATH.iterdir():
        memory_cleared += file.stat().st_size
        file.unlink()
    if include_base_files:
        for file in BASE_EMOJI_FONT_PATH.iterdir():
            memory_cleared += file.stat().st_size
            file.unlink()

    if memory_cleared == 0:
        print("Looks like everything is cleared already!")
    else:
        print(f"Successfully cleared {humanize.naturalsize(memory_cleared)}.")


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
