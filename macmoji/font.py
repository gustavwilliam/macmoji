from contextlib import contextmanager
import inspect
import os
from pathlib import Path
import shutil
import sys
from typing import Callable, Iterator

from afdko import otc2otf, otf2otc
from fontTools import ttx

from macmoji.config import (
    BASE_EMOJI_FONT_PATH,
    DEFAULT_GENERATED_FONT_PATH,
    AfdkoOptions,
)


@contextmanager
def suppress_stdout(function: Callable) -> Iterator:
    """
    Suppress stdout from a function.

    Useful with functions that produce a lot of unwanted output to stdout.
    """
    _original_write = sys.stdout.write

    def write_hook(s: str) -> int:
        """Hook to replace stdout.write() with a function that filters out code from `function`."""
        if all(
            frame_info.frame.f_code is not function.__code__
            for frame_info in inspect.stack()
        ):
            # Process output from other function normally
            return _original_write(s)
        else:
            # Suppress output from `function`
            return 0

    sys.stdout.write = write_hook
    try:
        yield
    finally:
        # Restore stdout when exiting context manager
        sys.stdout.write = _original_write


def generate_base_emoji_ttf():
    """Generates base TTF files from default TTC emoji file."""
    # Copying the system emoji font to the base emoji font directory
    default_font = Path("/System/Library/Fonts/Apple Color Emoji.ttc")
    if not default_font.exists():
        raise FileNotFoundError(
            "System emoji font not found. This is either because you are not running macOS, or you have deleted the system emoji font (unlikely)."
        )

    shutil.copy(
        default_font,
        BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttc",
    )
    otc2otf.main([str(BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttc")])


def generate_base_emoji_ttx(file_name: str):
    """Generates base TTX files from default TTF emoji files."""
    TMP_NAME = f"{file_name}-tmp.ttx"

    # Writing to temporary file first, so if the process is interrupted, the
    # original file is not overwritten. Having an incomplete TTX file at the
    # destination would cause base-file generation without the `--force` flag
    # to view the TTX file as valid, therefore skipping generation, despite it
    # being incomplete/corrupted.
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


def generate_ttc_from_ttf():
    """Generates a TTC file from TTF files."""
    # Suppress stdout from otf2otc, as it prints a lot of unnecessary information
    with suppress_stdout(function=otf2otc.run):
        otf2otc.run(
            [
                "-o",
                str(DEFAULT_GENERATED_FONT_PATH),
                str(BASE_EMOJI_FONT_PATH / "AppleColorEmoji-usr.ttf"),
                str(BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI-usr.ttf"),
            ]
        )


def base_emoji_process_cleanup() -> int:
    """Removes temporary files generated during base emoji generation and returns memory cleared."""
    memory_cleared = 0
    for path in [
        BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttc",
        BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttf",
        BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI.ttf",
        BASE_EMOJI_FONT_PATH / "AppleColorEmoji-tmp.ttx",
        BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI-tmp.ttx",
        BASE_EMOJI_FONT_PATH / "AppleColorEmoji-usr.ttx",
        BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI-usr.ttx",
        BASE_EMOJI_FONT_PATH / "AppleColorEmoji-usr.ttf",
        BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI-usr.ttf",
    ]:
        if path.exists():
            memory_cleared += path.stat().st_size
            path.unlink()

    return memory_cleared
