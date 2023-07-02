from functools import partial
from pathlib import Path

import typer
from rich import print
from typing_extensions import Annotated
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from macmoji.config import (
    BASE_EMOJI_FONT_PATH,
    DEFAULT_ASSETS_PATH,
    DEFAULT_GENERATED_FONT_PATH,
    TTF_SIZE,
    TTX_SIZE,
)
from macmoji.converter import generate_assets
from macmoji.font import (
    base_emoji_process_cleanup,
    generate_base_emoji_ttf,
    generate_base_emoji_ttx,
    generate_ttf_from_ttx,
)
from macmoji.utils import ProgressFileTask

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
        False, "--verbose", "-v", help="Print ignored files to stdout."
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
    ignored_paths = generate_assets(input_dir, output_dir)

    print(
        f"Done! ({len(ignored_paths)} ignored paths)\n\nSaved assets to: {output_dir} "
    )
    if verbose:
        if ignored_paths:
            print(f"The following paths were ignored: {ignored_paths}")
        else:
            print(f"No files were ignored")
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

    with Progress() as progress:
        task_ttf = ProgressFileTask(
            description="Generating TTF files",
            progress=progress,
            target=partial(generate_base_emoji_ttf),
            output_file=BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttf",
            output_size=TTF_SIZE,
        )  # Dooesn't update incrementally, but still gives a slightly nicer progress bar than the alternative
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
    output_dir: Path = typer.Argument(
        DEFAULT_GENERATED_FONT_PATH,
        help="Path to the output directory of sized PNG assets.",
    ),
):
    """Generate emoji font from a PNG assets folder."""
    base_files(force=False)  # Make sure base files are generated

    print(f"Generating emoji font. This will most likely take a few minutes...\n")
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(
            spinner_name="aesthetic",
            style="bold magenta",
            finished_text="[bold green]▰▰▰▰▰▰▰[/]",
        ),
        TimeElapsedColumn(),
    ) as progress:
        # Doesn't use ProgressTask, since the output files can't be tracked while generating
        task_ttx_1 = progress.add_task(
            "Compiling AppleColorEmoji.ttx",
            total=1,
            start=False,
        )
        task_ttx_2 = progress.add_task(
            "Compiling .AppleColorEmojiUI.ttx",
            total=1,
            start=False,
        )

        progress.start_task(task_ttx_1)
        generate_ttf_from_ttx("AppleColorEmoji")
        progress.update(task_ttx_1, completed=1)

        progress.start_task(task_ttx_2)
        generate_ttf_from_ttx(".AppleColorEmojiUI")
        progress.update(task_ttx_2, completed=1)
