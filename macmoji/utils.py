import functools
import xml.etree.ElementTree as ET
import time
from abc import ABC, abstractmethod
from contextlib import suppress
from functools import partial
from pathlib import Path
from threading import Thread
from typing import Generator

from rich.progress import Progress
from rich.panel import Panel

from macmoji.config import (
    ASSET_FILE_NAME,
    BASE_EMOJI_FONT_PATH,
    DEFAULT_SAVE_PATH,
    TTX_SIZE,
    ProgressConfig,
)
from macmoji.font import (
    base_emoji_process_cleanup,
    generate_base_emoji_ttf,
    generate_base_emoji_ttx,
)


class ProgressPanel(Progress):
    def __init__(self, title: str, *args, **kwargs) -> None:
        self.title = title  # Throws AttributeError if this like is below the next
        super().__init__(*args, **kwargs)

    def get_renderables(self):
        yield Panel(
            self.make_tasks_table(self.tasks),
            title=f"[bold]{self.title}[/]",
            title_align="left",
            expand=False,
            highlight=True,
        )


class ProgressTask(ABC):
    def __init__(
        self,
        description: str,
        progress: Progress,
        target: partial,
        *,
        progress_runner: bool = True,
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
        self.progress_runner = progress_runner
        self.task = self.progress.add_task(description, total=None)
        self._progress_active = False
        self._target_thread = Thread(target=self.target)
        self._progress_thread = Thread(target=self._progress_runner)

    def _set_completed(self) -> None:
        """Set progress bar to 100%."""
        if self.progress.tasks[self.task].total is None:
            self.progress.update(self.task, total=1)
            self.progress.update(self.task, completed=1)
        else:
            self.progress.update(
                self.task, total=self.progress.tasks[self.task].completed
            )

    def _progress_runner(self) -> None:
        if not self.progress_runner:
            return
        while self._progress_active:
            self.progress_loop()
            time.sleep(0.1)

        self._set_completed()

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
        self._set_completed()

    def run(self) -> None:
        """Run target and progress bar until target is done. This is a blocking function."""
        self.start()
        self.join()


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
        super().__init__(description, progress, target, progress_runner=False)
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
        super().__init__(
            description,
            progress,
            partial(lambda: None),
            progress_runner=False,
        )
        self.progress.update(self.task, total=1)
        self.progress.update(self.task, completed=1)

    def progress_loop(self) -> None:
        pass


def asset_file_name(unicode: str, size: int):
    """Returns the file name of an asset file used for generating fonts."""
    return ASSET_FILE_NAME.format(unicode=unicode, size=size)


def base_files_exist() -> bool:
    """Returns `True` if the base emoji files have already been generated."""
    required_files = [
        BASE_EMOJI_FONT_PATH / "AppleColorEmoji.ttx",
        BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI.ttx",
    ]
    return all(map(Path.exists, required_files))


def generate_base_files(*, force: bool, terminal_output: bool = True) -> None:
    """
    Generate base emoji files from default emoji files.

    If `force` is `True`, the base files will be generated even if they already exist.
    """
    if not force and base_files_exist():
        base_emoji_process_cleanup()
        return

    if terminal_output:
        print("Generating emoji base files. This will only have to be done once.\n")

        with ProgressPanel("Generating base files", *ProgressConfig.FULL) as progress:
            ProgressSimpleTask(
                description="Generating TTF files",
                progress=progress,
                target=partial(generate_base_emoji_ttf),
            ).run()
            task_1 = ProgressFileTask(
                description="Decompiling AppleColorEmoji.ttf",
                progress=progress,
                target=partial(generate_base_emoji_ttx, "AppleColorEmoji"),
                output_file=BASE_EMOJI_FONT_PATH / "AppleColorEmoji-tmp.ttx",
                output_size=TTX_SIZE,
            )
            task_2 = ProgressFileTask(
                description="Decompiling .AppleColorEmojiUI.ttf",
                progress=progress,
                target=partial(generate_base_emoji_ttx, ".AppleColorEmojiUI"),
                output_file=BASE_EMOJI_FONT_PATH / ".AppleColorEmojiUI-tmp.ttx",
                output_size=TTX_SIZE,
            )
            task_1.run()
            task_2.run()
            task_1.join()
            task_2.join()

        base_emoji_process_cleanup()
        print("\nSuccessfully generated emoji base files and cleaned up!")
    else:
        generate_base_emoji_ttf()
        generate_base_emoji_ttx("AppleColorEmoji")
        generate_base_emoji_ttx(".AppleColorEmojiUI")
        base_emoji_process_cleanup()


def _get_valid_emoji_names() -> Generator[str, None, None]:
    """Extract all valid emoji names from TTX files."""
    generate_base_files(force=False)
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
    general format is: `uXXXXX.0-6.MWBGLR`, with the following meanings:
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

    if file_path.is_file() and file_path.stat().st_size > 0:
        return frozenset(file_path.read_text().splitlines())
    else:
        with file_path.open("w") as f:
            names = frozenset(_get_valid_emoji_names())
            f.write("\n".join(names))  # Cache for next run

            return names


def _codify(code: str) -> str:
    """
    uXXXXX -> uXXXXX, XXXXX -> uXXXXX, UXXXXX -> uXXXXX

    Works with X lowercase, uppercase or numeric, and with or without leading zeroes.
    """
    code = code.upper()
    if code[0] == "U":
        code = code[1:]
    code = code.lstrip("0")

    return f"u{code}"


def reformat_emoji_name(name: str) -> str:
    """
    Reformats name of an emoji to the correct capitalization and adds "u" if needed.

    ---

    Examples:
        - `u1F385` -> `u1F385`
        - `u1f385` -> `u1F385`
        - `1f385` -> `u1F385`
        - `U1F385` -> `u1F385`

    If the name contains multiple unicode codes, every one is reformatted:
        - `u1F469_u1F91D_u1F468` -> `u1F469_u1F91D_u1F468`
        - `u1f469_u1F91d_u1F468` -> `u1F469_u1F91D_u1F468`
        - `1f469_u1F91d_1f468` -> `u1F469_u1F91D_u1F468`
        - `U1f469_u1F91d_u1f468` -> `u1F469_u1F91D_u1F468`

    If the emoji name contains modifiers at the end, these remain unchanged:
        - `1f385.2` -> `u1F385.2`
        - `1f385_u1f3fb.2.M` -> `u1F385_u1F3FB.2.M`

    Note: the emojis used in the examples here are using made-up unicode codes
    that may or may not map to actual emojis.
    """

    modifiers = ""
    base_name = name
    if "." in name:
        try:
            base_name, modifiers = name.split(".", 1)
        except ValueError:
            raise ValueError(f"Invalid emoji name: '{name}' (modifiers)")

    codes = base_name.split("_")
    if "" in codes:
        raise ValueError(f"Invalid emoji name: '{name}' (codes)")

    code = "_".join(map(_codify, codes))
    return f"{code}{'.' if modifiers else ''}{modifiers}"


def is_valid_emoji(name: str) -> bool:
    """
    Checks if an emoji name is valid based on emoji names in TTX files.

    Please use `reformat_emoji_name` on the name before using this function,
    to ensure the name is in the correct format. Otherwise it will most likely
    be rejected.

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
