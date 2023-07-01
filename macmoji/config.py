from enum import Enum


class FileType(str, Enum):
    PNG = ".png"
    SVG = ".svg"
    TTC = ".ttc"
    TTF = ".ttf"
    TTX = ".ttx"


ASSET_SIZES = [20, 26, 32, 40, 48, 52, 64, 96, 160]  # Sizes of the Asset pngs
ASSET_FILE_NAME = "{unicode} {size}.png"
