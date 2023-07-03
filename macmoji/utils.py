import functools
import xml.etree.ElementTree as ET
import inspect
import sys
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager, suppress
from functools import partial
from pathlib import Path
from threading import Thread
from typing import Callable, Generator, Iterator
import emoji

from rich.progress import Progress

from macmoji.config import (
    ASSET_FILE_NAME,
    BASE_EMOJI_FONT_PATH,
    DEFAULT_SAVE_PATH,
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


class ProgressTask(ABC):
    def __init__(
        self,
        description: str,
        progress: Progress,
        target: partial,
    ) -> None:
        """
        Abstract base class for threaded rich progress bar tasks.

        Adds a task to a rich progress bar, and starts a thread to run a target function.
        While the function is running, a loop is run to update the progress bar. When the
        function is complete, the progress bar is updated to 100%.
        """
        self.description = description
        self.progress = progress
        self.target = target
        self.task = self.progress.add_task(description, total=None)
        self._progress_active = False
        self._target_thread = Thread(target=self.target)
        self._progress_thread = Thread(target=self._progress_runner)

    def _progress_runner(self) -> None:
        while self._progress_active:
            self.progress_loop()
            time.sleep(0.1)

        # Ensure progress bar is at 100% when task is complete, even if `task.total` isn't accurate
        if self.progress.tasks[self.task].total is None:
            self.progress.update(self.task, total=1)
            self.progress.update(self.task, completed=1)
        else:
            self.progress.update(
                self.task, completed=self.progress.tasks[self.task].total
            )

    @abstractmethod
    def progress_loop(self) -> None:
        """Loop to update progress bar. This function is looped while progress is active."""
        return

    def start(self) -> None:
        """Start the progress bar and start threads for target and progress bar."""
        self._progress_active = True
        self._target_thread.start()
        self._progress_thread.start()

    def join(self) -> None:
        """
        Wait for target and progress bar to finish.

        This function blocks until both target thread is complete, similar to `threading.Thread.join()`
        (since that's literally what it does, as well as some other things).
        """
        self._target_thread.join()
        self._progress_active = False
        self._progress_thread.join()


class ProgressFileTask(ProgressTask):
    def __init__(
        self,
        description: str,
        progress: Progress,
        target: partial,
        output_file: Path,
        output_size: int,
    ) -> None:
        """Keeps track of file size compared to final output size and updates progress bar accordingly, while running a target function."""
        super().__init__(description, progress, target)
        self.output_file = output_file
        self.output_size = output_size
        self.progress.update(self.task, total=self.output_size)

    def progress_loop(self) -> None:
        with suppress(FileNotFoundError):  # File to track has not been created yet
            new_size = self.output_file.stat().st_size
            self.progress.update(self.task, completed=new_size)


class ProgressSimpleTask(ProgressTask):
    def __init__(
        self,
        description: str,
        progress: Progress,
        target: partial,
    ) -> None:
        """Simple progress bar task that runs a target function, with a simple animated progress bar."""
        super().__init__(description, progress, target)
        # Since `ProgressTask.task` total is set to `None` by default, the progress bar will be animated.
        # Could also set `start` to `False` for similar effect, but that would stop TimeElapsedColumn from updating.

    def progress_loop(self) -> None:
        pass


class ProgressCompletedTask(ProgressTask):
    def __init__(
        self,
        description: str,
        progress: Progress,
    ) -> None:
        """
        Simple progress bar task that is immediately completed without the need to run anything.

        Useful for tasks that are already completed, but should still get added to the progress bar.
        """
        super().__init__(description, progress, partial(lambda: None))
        self.progress.update(self.task, total=1)
        self.progress.update(self.task, completed=1)

    def progress_loop(self) -> None:
        pass


def asset_file_name(unicode: str, size: int):
    """Returns the file name of an asset file used for generating fonts."""
    return ASSET_FILE_NAME.format(unicode=unicode, size=size)


def _get_valid_emoji_names() -> Generator[str, None, None]:
    """Extract all valid emoji names from TTX files."""
    root = ET.parse(BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttx").getroot()

    if not (glyphParent := root.find("GlyphOrder")):
        raise ValueError("Invalid/incomplete TTX file. Missing `GlyphOrder` element.")
    if not (glyphs := glyphParent.iter("GlyphID")):
        raise ValueError("Invalid/incomplete TTX file. Missing `GlyphID` elements.")

    for glyph in glyphs:
        if not (name := glyph.get("name")):
            raise ValueError("Invalid/incomplete TTX file. Missing glyph name.")
        yield name


@functools.cache
def valid_emoji_names() -> frozenset[str]:
    """
    Returns a frozenset of all valid emoji names.

    The function uses `@functools.cache` to avoid having to open the cache file every
    time the function is called. If you modify the TTX files, make sure to clear run
    `functools.cache_clear()` to clear the cache before relying on this function.

    ---

    `name` is the name of the emoji as used by Apple in the TTX files. The
    general format is : `uXXXXX.0-6.MWBGLR`, with the following meanings:
        - `uXXXXX`: Unicode codepoint of the base emoji, ignoring leading zeroes.
            Codepoint are allowed to have less than 5 digits is all 5 aren't needed.
        - `0-6`: Skintone modifiers. Only 0-5 (going from lightest to darkest)
            are used in most emojis (see note about 6 below). Multiple can ve used
            at once in some emojis.
        - `MWBG`: Gender modifiers. M=Male, F=Female, B=Boy, G=Girl, L=Left, R=Right.
            Multiple can be used at once in some emojis.

    Examples of valid `name` and their meanings:
        - `u1F385.2`: Santa Claus, Medium-Light Skin Tone
        - `u1F3C3.0.M`: Man Running Facing Right, No Skin Tone
        - `u1F469_u1F91D_u1F468.55`: Woman and Man Holding Hands: Dark Skin Tone

    TTGlyph outlines under `glyf` and control characters can't currently be modified using
    MacMoji. Most emojis can be changed completely fine without this though.

    Note: for `u1F9D1_u1F91D_u1F9D1.XX`, X is 1-6 instead of 0-5, where the meaning
    of 6 is the same as 0 in the rest of the formats. From my observations,
    these are the only emojis with 6 modifiers.
    """
    file_path = DEFAULT_SAVE_PATH / "valid_emoji_names.txt"

    if file_path.is_file():
        return frozenset(file_path.read_text().splitlines())
    else:
        with file_path.open("w") as f:
            names = frozenset(_get_valid_emoji_names())
            f.write("\n".join(names))  # Cache for next run

            return names


def is_valid_emoji(name):
    """
    Checks if an emoji name is valid based on emoji names in TTX files.

    ---

    `name` is the name of the emoji as used by Apple in the TTX files. The
    general format is : `uXXXXX.0-6.MWBGLR`, with the following meanings:
        - `uXXXXX`: Unicode codepoint of the base emoji, ignoring leading zeroes.
            Codepoint are allowed to have less than 5 digits is all 5 aren't needed.
        - `0-6`: Skintone modifiers. Only 0-5 (going from lightest to darkest)
            are used in most emojis (see note about 6 below). Multiple can ve used
            at once in some emojis.
        - `MWBG`: Gender modifiers. M=Male, F=Female, B=Boy, G=Girl, L=Left, R=Right.
            Multiple can be used at once in some emojis.

    Examples of valid `name` and their meanings:
        - `u1F385.2`: Santa Claus, Medium-Light Skin Tone
        - `u1F3C3.0.M`: Man Running Facing Right, No Skin Tone
        - `u1F469_u1F91D_u1F468.55`: Woman and Man Holding Hands: Dark Skin Tone

    TTGlyph outlines under `glyf` and control characters can't currently be modified using
    MacMoji. Most emojis can be changed completely fine without this though.

    Note: for `u1F9D1_u1F91D_u1F9D1.XX`, X is 1-6 instead of 0-5, where the meaning
    of 6 is the same as 0 in the rest of the formats. From my observations,
    these are the only emojis with 6 modifiers.
    """
    return name in valid_emoji_names()
