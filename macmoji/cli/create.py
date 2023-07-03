from functools import partial
from pathlib import Path

import typer
from rich import print
from rich.progress import Progress
from typing_extensions import Annotated

from macmoji.config import (
    BASE_EMOJI_FONT_PATH,
    DEFAULT_ASSETS_PATH,
    DEFAULT_GENERATED_FONT_PATH,
    TTX_SIZE,
    ProgressConfig,
)
from macmoji.converter import generate_assets
from macmoji.font import (
    base_emoji_process_cleanup,
    generate_base_emoji_ttf,
    generate_base_emoji_ttx,
    generate_ttc_from_ttf,
    generate_ttf_from_ttx,
)
from macmoji.utils import ProgressCompletedTask, ProgressFileTask, ProgressSimpleTask

app = typer.Typer()


@app.callback()
def main() -> None:
    """Utilities to create assets and emoji fonts."""
    return


@app.command()
def assets(
    input_dir: Annotated[
        Path, typer.Argument(help="Path to directory of SVG or PNG source files.")
    ],
    output_dir: Path = typer.Argument(
        DEFAULT_ASSETS_PATH,
        help="Path to the output directory of sized PNG assets.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Print ignored files and why they were ignored to stdout.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing files in output directory without asking.",
    ),
):
    """Generate folder with correctly sized PNG-files, from SVG/PNG source files."""
    output_dir_empty = not any(output_dir.iterdir())
    if not output_dir_empty and not output_dir == DEFAULT_ASSETS_PATH and not force:
        typer.confirm(
            f"{output_dir} is not empty. Proceeding will overwrite existing files.",
            default=False,
            abort=True,
        )
    try:
        ignored_paths = generate_assets(input_dir, output_dir)
    except ValueError as e:
        raise typer.BadParameter(str(e))

    print(f"Done! Saved assets to: '{output_dir}'")
    if ignored_paths:
        print(
            "\nIgnored paths:",
            *(f"\n- '{path}' {reason}" for path, reason in ignored_paths),
        )
    if not output_dir_empty and not output_dir == DEFAULT_ASSETS_PATH:
        print(
            f"[bold yellow]\nWarning:[/bold yellow] saved to non-empty directory. Previously existent files may interfere with the assets when generating the font."
        )


@app.command()
def base_files(
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

    with Progress(*ProgressConfig.FULL) as progress:
        task_ttf = ProgressSimpleTask(
            description="Generating TTF files",
            progress=progress,
            target=partial(generate_base_emoji_ttf),
        )
        task_ttx_1 = ProgressFileTask(
            description="Decompiling AppleColorEmoji.ttf",
            progress=progress,
            target=partial(generate_base_emoji_ttx, "AppleColorEmoji"),
            output_file=BASE_EMOJI_FONT_PATH / "AppleColorEmoji-tmp.ttx",
            output_size=TTX_SIZE,
        )
        task_ttx_2 = ProgressFileTask(
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
def font(
    input_dir: Path = typer.Argument(
        default=DEFAULT_ASSETS_PATH,
        help="Path to directory with generated asset files.",
    ),
):
    """Generate emoji font from a PNG assets folder."""
    base_files(force=False)  # Make sure base files are generated

    # TODO: Insert assets into base files.

    with Progress(*ProgressConfig.TIME) as progress:
        _ = ProgressCompletedTask(
            description="Generating base emoji files",
            progress=progress,
        )
        task_ttx_1 = ProgressSimpleTask(
            description="Compiling AppleColorEmoji.ttx",
            progress=progress,
            target=partial(generate_ttf_from_ttx, "AppleColorEmoji"),
        )
        task_ttx_2 = ProgressSimpleTask(
            description="Compiling .AppleColorEmojiUI.ttx",
            progress=progress,
            target=partial(generate_ttf_from_ttx, ".AppleColorEmojiUI"),
        )
        task_ttc = ProgressFileTask(
            description="Generating TTC file",
            progress=progress,
            target=partial(generate_ttc_from_ttf),
            output_file=DEFAULT_GENERATED_FONT_PATH,
            output_size=190000000,
        )

        task_ttx_1.start()
        task_ttx_2.start()
        task_ttx_1.join()
        task_ttx_2.join()
        task_ttc.start()
        task_ttc.join()
