import typer
from rich import print
from typing import Optional
from typing_extensions import Annotated
from pathlib import Path
import importlib.metadata

import macmoji.tui.create

app = typer.Typer()
app.add_typer(macmoji.tui.create.app, name="create")


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
def install(
    font: Annotated[Path, typer.Argument(help="`.ttc` font file to install")],
) -> None:
    """Install an emoji font to the current user's font directory."""
    raise NotImplementedError()


@app.command()
def uninstall() -> None:
    """Uninstall active custom emoji font from the current user's font directory."""
    raise NotImplementedError()
