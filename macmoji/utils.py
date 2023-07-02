import time
from contextlib import suppress
from functools import partial
from pathlib import Path
from threading import Thread

from rich.progress import Progress

from macmoji.config import ASSET_FILE_NAME


class ProgressTask:
    def __init__(
        self,
        description: str,
        progress: Progress,
        target: partial,
        output_file: Path,
        output_size: int,
    ) -> None:
        self.description = description
        self.progress = progress
        self.target = target
        self.output_file = output_file
        self.output_size = output_size
        self._task = self.progress.add_task(description, total=output_size)
        self._progress_active = False
        self._target_thread = Thread(target=self.target)
        self._progress_thread = Thread(target=self._progress_runner)

    def _progress_runner(self) -> None:
        while self._progress_active:
            with suppress(FileNotFoundError):
                new_size = self.output_file.stat().st_size
                self.progress.update(self._task, completed=new_size)
            time.sleep(0.1)

        # Ensure progress bar is at 100% when task is complete, even if `output_size` wasn't exact
        self.progress.update(self._task, completed=self.output_size)

    def start(self) -> None:
        self._progress_active = True
        self._target_thread.start()
        self._progress_thread.start()

    def join(self) -> None:
        self._target_thread.join()
        self._progress_active = False
        self._progress_thread.join()


def asset_file_name(unicode: str, size: int):
    return ASSET_FILE_NAME.format(unicode=unicode, size=size)
