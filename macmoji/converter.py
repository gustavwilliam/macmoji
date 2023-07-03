from pathlib import Path
from typing import List

import cairosvg
from PIL import Image
from rich import print

from macmoji.config import ASSET_SIZES, FileType
from macmoji.utils import asset_file_name

ALLOWED_INPUT_TYPES = [FileType.SVG, FileType.PNG]


def generate_assets(dir_path: Path, output_dir: Path) -> List[Path]:
    """
    Generate directory of sized PNG assets from directory of SVGs or PNGs.

    Returns a list of ignored files. Overwrites already existing files in output directory.
    """
    if not dir_path.is_dir():
        raise ValueError(f"{dir_path} is not a directory")
    if not any(dir_path.iterdir()):
        raise ValueError(f"{dir_path} does not contain any files")
    output_dir.mkdir(parents=True, exist_ok=True)

    ignored_paths = []
    for fp in dir_path.iterdir():
        if fp.is_dir():
            ignored_paths.append(fp)
            continue
        if fp.suffix not in ALLOWED_INPUT_TYPES:
            ignored_paths.append(fp)
            continue

        convert_function = svg2asset if fp.suffix == FileType.SVG else png2asset
        for size in ASSET_SIZES:
            output_path = output_dir / asset_file_name(fp.name, size)
            convert_function(fp, output_path, size)

    return ignored_paths


def svg2asset(path: Path, output_path: Path, size: int):
    """Create a PNG asset from an SVG file and save it at the given path."""
    cairosvg.svg2png(url=str(path), write_to=str(output_path), output_height=size)


def png2asset(path: Path, output_path: Path, size: int):
    """Create a PNG asset from a PNG file and save it at the given path."""
    with Image.open(path) as img:
        scale = size / max(img.size)
        scaled_img = img.resize((int(img.width * scale), int(img.height * scale)))
        scaled_img.save(output_path)
