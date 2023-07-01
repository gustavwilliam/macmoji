import typer
from rich import print


app = typer.Typer()


@app.callback()
def main() -> None:
    """Utilities to create assets and emoji fonts."""
    return


@app.command()
def assets():
    """Generate folder with correctly sized PNG-files, from SVG/PNG source files."""
    raise NotImplementedError()


@app.command()
def font():
    """Generate emoji font from PNG assets folder."""
    raise NotImplementedError()
