from abc import ABC, abstractmethod
import time
from contextlib import suppress
from functools import partial
from pathlib import Path
from threading import Thread

from rich.progress import Progress

from macmoji.config import ASSET_FILE_NAME


class ProgressTask(ABC):
    def __init__(
        self,
        description: str,
        progress: Progress,
        target: partial,
    ) -> None:
        self.description = description
        self.progress = progress
        self.target = target
        self.task = self.progress.add_task(description)
        self._progress_active = False
        self._target_thread = Thread(target=self.target)
        self._progress_thread = Thread(target=self._progress_runner)

    def _progress_runner(self) -> None:
        while self._progress_active:
            self.progress_loop()
            time.sleep(0.1)

        # Ensure progress bar is at 100% when task is complete, even if `task.total` isn't accurate
        self.progress.update(self.task, completed=self.progress.tasks[self.task].total)

    @abstractmethod
    def progress_loop(self) -> None:
        """Loop to update progress bar. This function is looped while progress is active."""
        return

    def start(self) -> None:
        self._progress_active = True
        self._target_thread.start()
        self._progress_thread.start()

    def join(self) -> None:
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
        super().__init__(description, progress, target)
        self.output_file = output_file
        self.output_size = output_size
        self.progress.update(self.task, total=self.output_size)

    def progress_loop(self) -> None:
        with suppress(FileNotFoundError):
            new_size = self.output_file.stat().st_size
            self.progress.update(self.task, completed=new_size)


def asset_file_name(unicode: str, size: int):
    return ASSET_FILE_NAME.format(unicode=unicode, size=size)
