from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from rich.progress import (BarColumn, Progress, TaskProgressColumn, TextColumn,
                           TimeElapsedColumn, TimeRemainingColumn)


class FileType(str, Enum):
    PNG = ".png"
    SVG = ".svg"
    TTC = ".ttc"
    TTF = ".ttf"
    TTX = ".ttx"


class ProgressConfig:
    FULL = (
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    )
    DEFAULT = Progress.get_default_columns()
    TIME = (
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
    )


@dataclass
class AfdkoOptions:
    ttc_path: str
    report: bool


TTX_SIZE = 570000000  # Approximate size of the output TTX files
TTF_SIZE = 190000000  # Approximate size of the output TTF files

ASSET_SIZES = [20, 26, 32, 40, 48, 52, 64, 96, 160]  # Sizes of the Asset pngs
ASSET_FILE_NAME = "{unicode} {size}.png"

DEFAULT_SAVE_PATH = Path(
    "~/Library/Application Support/com.gustavwilliam.MacMoji"
).expanduser()
DEFAULT_ASSETS_PATH = DEFAULT_SAVE_PATH / "generated-assets"
DEFAULT_GENERATED_FONT_PATH = DEFAULT_SAVE_PATH / "Apple Color Emoji.ttc"
BASE_EMOJI_FONT_PATH = DEFAULT_SAVE_PATH / "base-emoji-font"
