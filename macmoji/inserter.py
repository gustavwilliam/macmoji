from pathlib import Path
import xml.etree.ElementTree as ET

from macmoji.config import ASSET_SIZES
from macmoji.utils import reformat_emoji_name


def _hex_to_png(out: str = "img.png", input_path: str = "data.txt"):
    """
    Converts a hexadecimal string to a PNG file.

    Only intended for testing purposes. Do not use in production.
    """
    with open(out, "wb") as f:
        with open(input_path, "r") as hex_file:
            hex = hex_file.read().replace("\n", "").replace(" ", "")
        print(hex)
        f.write(bytes.fromhex(hex))


def png_to_hex(input_path: Path) -> str:
    """
    Converts a PNG file to a hexadecimal string.

    Only intended for testing purposes. Do not use in production.
    """
    with open(input_path, "rb") as f:
        return f.read().hex()


def assets_info(
    assets_dir: Path,
) -> tuple[dict[str, dict[int, Path]], list[tuple[Path, str]]]:
    """
    Returns a tuple with information about the assets, and a list of ignored paths and the reasons.

    Example return value:
    (
        {
            "1F600": {
                20: Path("1F600 20.png"),
                ...
            },
            ...
        },
        [
            (Path("homework-folder"), "is a directory"),
            ...
        ]
    )
    """
    info: dict[str, dict[int, Path]] = {}
    ignored_paths: list[tuple[Path, str]] = []

    for asset_path in assets_dir.iterdir():
        if not asset_path.is_file():
            ignored_paths.append((asset_path, "is a directory"))
            continue

        try:
            raw_name, size = asset_path.stem.split(" ")
            size = int(size)
        except ValueError:
            ignored_paths.append(
                (asset_path, f"has invalid file name '{asset_path.stem}'")
            )
            continue
        name = reformat_emoji_name(raw_name)

        if name not in info:
            info[name] = {}
        if size not in info[name]:
            info[name][size] = asset_path

    filtered_info = {}
    for key, asset in info.items():
        # If the correct sizes aren't provided, the emoji assets are incomplete/invalid
        # Without *all* sizes, some sizes of the emoji would show up as the original
        # Apple emoji. It's better to let the user re-generate the proper assets.
        if set(asset.keys()) == set(
            ASSET_SIZES
        ):  # TODO: filter out invalid emoji names
            filtered_info[key] = asset
        else:
            for path in asset.values():
                ignored_paths.append((path, "has missing/invalid sizes"))

    return (filtered_info, ignored_paths)


def insert_all_emojis(
    assets_dir: Path,
    ttx_in: Path,
    ttx_out: Path,
) -> tuple[list[str], list[tuple[Path, str]]]:
    """Inserts PNG emoji assets for all emoji into a TTX file's ElementTree.

    Requires the TTX file to be parsed as an `ElementTree` before being passed.
    This helps limit the numer of times the TTX file is parsed and saved.
    """
    successful: list[str] = []
    ignored: list[tuple[Path, str]] = []

    tree = ET.parse(ttx_in)
    try:
        root = tree.getroot()
    except ET.ParseError as e:
        raise ValueError(
            f"Can't parse TTX file '{ttx_in}'. Try regenerating base files by running `macmoji create base-files`."
        ) from e
    if (strikes := root.findall("./sbix/strike")) is None:
        raise ValueError(
            f"Invalid TTX file '{ttx_in}' with no SBIX strikes. Try regenerating base files by running `macmoji create base-files`."
        )

    assets, asset_ignores = assets_info(assets_dir)
    ignored.extend(asset_ignores)
    for name, size_paths in assets.items():
        insert_emoji(strikes, name, size_paths)

    tree.write(ttx_out)
    return successful, ignored


def insert_emoji(strikes: list[ET.Element], name: str, size_paths: dict[int, Path]):
    """Inserts PNG emoji assets for emoji into a TTX file's ElementTree.

    Requires the TTX file to be parsed as an `ElementTree` before being passed.
    This helps limit the numer of times the TTX file is parsed and saved.
    """
    for strike, size in zip(strikes, ASSET_SIZES):
        glyph = strike.find(f"./glyph[@name='{name}']/hexdata")
        if glyph is None:
            raise ValueError(
                f"Invalid TTX file with no '{name}' `glyph` of size {size}. Try regenerating base files by running `macmoji create base-files`."
            )
        glyph.text = png_to_hex(size_paths[size])
