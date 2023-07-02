import os
from pathlib import Path

from afdko import otc2otf
from fontTools import ttx

from macmoji.config import BASE_EMOJI_FONT_PATH, AfdkoOptions


def generate_base_emoji_ttf():
    """Generates base TTF files from default TTC emoji file."""
    options = AfdkoOptions("macmoji/base-emoji-font.ttc", False)
    otc2otf.run(options)
    os.replace(
        "macmoji/AppleColorEmoji.ttf", BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttf"
    )
    os.replace(
        "macmoji/.AppleColorEmojiUI.ttf",
        BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI.ttf",
    )


def generate_base_emoji_ttx(file_name: str):
    """Generates base TTX files from default TTF emoji files."""
    TMP_NAME = f"{file_name}-tmp.ttx"

    # Writing to temporary file first, so if the process is interrupted, the original file is not overwritten.
    ttx.ttDump(
        BASE_EMOJI_FONT_PATH / f"{file_name}.ttf",
        BASE_EMOJI_FONT_PATH / TMP_NAME,  # type: ignore
        ttx.Options([], 0),
    )
    os.replace(
        BASE_EMOJI_FONT_PATH / TMP_NAME,
        BASE_EMOJI_FONT_PATH / f"{file_name}.ttx",
    )


def generate_ttf_from_ttx(file_name: str):
    """Generates a TTF file from a TTX file."""
    ttx.ttCompile(
        BASE_EMOJI_FONT_PATH / f"{file_name}.ttx",
        BASE_EMOJI_FONT_PATH / f"{file_name}.ttf",  # type: ignore
        ttx.Options([], 0),
    )


def base_emoji_process_cleanup() -> int:
    """Removes temporary files generated during base emoji generation and returns memory cleared."""
    memory_cleared = 0
    for path in [
        BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttf",
        BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI.ttf",
        BASE_EMOJI_FONT_PATH / "AppleColorEmoji-tmp.ttx",
        BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI-tmp.ttx",
        Path("macmoji/AppleColorEmoji.ttf"),
        Path("macmoji/.AppleColorEmojiUI.ttf"),
    ]:
        if path.exists():
            memory_cleared += path.stat().st_size
            path.unlink()

    return memory_cleared
