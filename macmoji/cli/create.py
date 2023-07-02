from pathlib import Path
from typing import Optional

import typer
from rich import print
from typing_extensions import Annotated

from macmoji.config import DEFAULT_ASSETS_PATH, DEFAULT_GENERATED_FONT_PATH
from macmoji.converter import generate_assets

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
def font(
    input_dir: Optional[Path] = typer.Argument(
        default=DEFAULT_ASSETS_PATH,
        help="Path to directory with generated asset files.",
    ),
    output_dir: Optional[Path] = typer.Argument(
        DEFAULT_GENERATED_FONT_PATH,
        help="Path to the output directory of sized PNG assets.",
    ),
):
    """Generate emoji font from a PNG assets folder."""
    raise NotImplementedError()
