from functools import partial
from pathlib import Path
import shutil

import typer
from rich import print
from rich.progress import Progress
from typing_extensions import Annotated

from macmoji.config import (
    BASE_EMOJI_FONT_PATH,
    DEFAULT_ASSETS_PATH,
    DEFAULT_GENERATED_FONT_PATH,
    ProgressConfig,
)
from macmoji.converter import generate_assets
from macmoji.font import (
    base_emoji_process_cleanup,
    generate_ttc_from_ttf,
    generate_ttf_from_ttx,
)
from macmoji.utils import (
    ProgressCompletedTask,
    ProgressFileTask,
    ProgressSimpleTask,
    ProgressPanel,
    base_files_exist,
    generate_base_files,
)
from macmoji.inserter import insert_all_emojis

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
    if output_dir == DEFAULT_ASSETS_PATH:
        # Clear output directory if it's the MacMoji default (not user provided)
        shutil.rmtree(output_dir)
        output_dir.mkdir()
    try:
        n_successful, ignored_paths = generate_assets(input_dir, output_dir)
    except ValueError as e:
        raise typer.BadParameter(str(e))

    print(
        f"Done! Saved assets for {n_successful} emoji{'' if n_successful == 1 else 's'} to: '{output_dir}'"
    )
    if ignored_paths:
        print(
            "\nIgnored paths:",
            *(f"\n- [bold red]'{path}'[/] {reason}" for path, reason in ignored_paths),
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
    if not force and base_files_exist:
        print(
            "Base emoji files already exist. Use `--force` to overwrite them.",
        )
        return
    generate_base_files(force=force)


def _insert_emoji_runner(progress: Progress, assets_dir, ttx_in, ttx_out) -> None:
    successful, ignored = insert_all_emojis(assets_dir, ttx_in, ttx_out)
    if len(ignored) > 0:
        progress.console.print(
            "Paths to invalid files in assets:",
            *(f"\n- [bold red]{path}[/] {reason}" for path, reason in ignored),
        )
    # TODO: raise exception?


@app.command()
def font(
    input_dir: Path = typer.Argument(
        default=DEFAULT_ASSETS_PATH,
        help="Path to directory with generated asset files.",
    ),
):
    """Generate emoji font from a PNG assets folder."""
    # Run outside of Progress context since it generates its own progress bar
    base_files(force=False)

    print()  # Make space for progress bar
    with ProgressPanel("Generating font", *ProgressConfig.TIME) as progress:
        ProgressCompletedTask(
            description="Generating emoji base files",
            progress=progress,
        ).run()

        insert_1 = ProgressSimpleTask(
            description="Inserting into AppleColorEmoji.ttx",
            progress=progress,
            target=partial(
                _insert_emoji_runner,
                progress,
                input_dir,
                BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttx",
                ttx_usr_1 := (BASE_EMOJI_FONT_PATH / "AppleColorEmoji-usr.ttx"),
            ),
        )
        insert_2 = ProgressSimpleTask(
            description="Inserting into .AppleColorEmojiUI.ttx",
            progress=progress,
            target=partial(
                insert_all_emojis,
                input_dir,
                BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI.ttx",
                ttx_usr_2 := (BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI-usr.ttx"),
            ),
        )
        insert_1.run()
        insert_2.run()
        insert_1.join()
        insert_2.join()

        # Generating TTF from TTX files one at a time rather than in parallel, since
        # `generate_ttf_from_ttx` is accessing asset files, and it doesn't seem like
        # a nice idea to have multiple processes accessing the same file at the same
        # time.
        ProgressSimpleTask(
            description="Compiling AppleColorEmoji.ttx",
            progress=progress,
            target=partial(generate_ttf_from_ttx, ttx_usr_1.stem),
        ).run()
        ProgressSimpleTask(
            description="Compiling .AppleColorEmojiUI.ttx",
            progress=progress,
            target=partial(generate_ttf_from_ttx, ttx_usr_2.stem),
        ).run()
        ProgressFileTask(
            description="Generating TTC file",
            progress=progress,
            target=partial(generate_ttc_from_ttf),
            output_file=DEFAULT_GENERATED_FONT_PATH,
            output_size=190000000,
        ).run()

    base_emoji_process_cleanup()
