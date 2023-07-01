import typer
from pathlib import Path
from rich import print, logging
from typing import Optional
from typing_extensions import Annotated
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
        Path.cwd() / "macmoji-assets",
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
    if not output_dir_empty and not force:
        typer.confirm(
            f"{output_dir} is not empty. Proceeding will overwrite existing files.",
            default=False,
            abort=True,
        )
    ignored_paths = generate_assets(input_dir, output_dir)

    print(f"Done! Saved assets to: {output_dir} ({len(ignored_paths)} ignored paths)")
    print(
        f"[bold yellow]\nWarning:[/bold yellow] saved to non-empty directory. Previously existent files may interfere with the assets when generating the font."
    )
    if verbose:
        if ignored_paths:
            print(f"\nThe following paths were ignored: {ignored_paths}")
        else:
            print(f"\nNo files were ignored")


@app.command()
def font():
    """Generate emoji font from PNG assets folder."""
    raise NotImplementedError()
