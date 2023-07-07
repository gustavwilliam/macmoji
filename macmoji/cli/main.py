import importlib.metadata
import os
from pathlib import Path
from typing import Optional

import humanize
import typer
from rich import print

import macmoji.cli.create
from macmoji.config import (
    BASE_EMOJI_FONT_PATH,
    DEFAULT_ASSETS_PATH,
    DEFAULT_GENERATED_FONT_PATH,
    DEFAULT_SAVE_PATH,
)
from macmoji.font import base_emoji_process_cleanup

app = typer.Typer(no_args_is_help=True)
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
        "-v",
        help="Show the application's version and exit.",
        callback=_version_callback,
        is_eager=True,
    )
) -> None:
    """Create custom emoji fonts for macOS."""
    return


@app.command()
def clear_cache(
    clear_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Also clear the emoji base files. Frees more than 1GB of memory, but adds multiple minutes to the next time an emoji font is generated. This cannot be undone.",
    ),
) -> None:
    """Clears the cache of generated emoji assets."""
    memory_cleared = base_emoji_process_cleanup()

    for file in DEFAULT_ASSETS_PATH.iterdir():
        memory_cleared += file.stat().st_size
        file.unlink()
    if clear_all:
        for file in BASE_EMOJI_FONT_PATH.iterdir():
            memory_cleared += file.stat().st_size
            file.unlink()

        if (emoji_names_file := DEFAULT_SAVE_PATH / "valid_emoji_names.txt").exists():
            memory_cleared += emoji_names_file.stat().st_size
            emoji_names_file.unlink()

    if memory_cleared == 0:
        print("Looks like everything is cleared already!")
    else:
        print(f"Successfully cleared {humanize.naturalsize(memory_cleared)}.")


@app.command()
def install(
    font: Path = typer.Argument(
        DEFAULT_GENERATED_FONT_PATH,
        help="`.ttc` font file to install",
    ),
    output_dir: Path = typer.Option(
        Path("~/Library/Fonts").expanduser(),
        "--output-dir",
        "-o",
        help="Directory to install the font inside.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite active custom emoji font without asking.",
    ),
) -> None:
    """Install an emoji font to the current user's font directory."""
    output_path = output_dir / "Apple Color Emoji.ttc"
    font_at_output_path = output_path.exists()

    if not font.exists():
        raise typer.BadParameter(f"Font file '{font}' does not exist.")
    if not output_dir.is_dir():
        raise typer.BadParameter(
            f"Provided output directory '{output_dir}' is not a directory. Please create it or use a different directory before attempting to install."
        )
    if font_at_output_path and not force:
        if not typer.confirm(
            f"Custom emoji font already installed at '{output_path}', overwrite?"
        ):
            raise typer.Abort()

    os.replace(font, output_path)
    print(
        ("\n" if font_at_output_path else "")
        + f"Successfully installed at '{output_path}'!{' (1 font overwritten)' if font_at_output_path else ''}",
        "[bold yellow]\nWarning:[/] the emojis may not appear everywhere until you've restarted currently open applications or the computer.",
    )


@app.command()
def uninstall(
    font_path: Path = typer.Argument(
        Path("~/Library/Fonts/Apple Color Emoji.ttc").expanduser(),
        help="`.ttc` font file to install",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Uninstall active custom emoji font without asking for confirmation.",
    ),
) -> None:
    """Uninstall active custom emoji font from the current user's font directory."""
    if not font_path.exists():
        print(f"No custom emoji font installed, skipping.")
    if not force and not typer.confirm(
        f"Are you sure you want to uninstall the custom emoji font at '{font_path}'? This cannot be undone."
    ):
        raise typer.Abort()

    font_path.unlink()
    print(f"Successfully uninstalled custom emoji font.")
