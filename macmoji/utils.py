import inspect
import sys
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager, suppress
from functools import partial
from pathlib import Path
from threading import Thread
from typing import Callable, Iterator

from rich.progress import Progress

from macmoji.config import ASSET_FILE_NAME


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
