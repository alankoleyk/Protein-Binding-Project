"""Run backend calls in a worker; deliver their outcomes on the GUI thread."""

from itertools import count
from traceback import print_exc

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _Signals(QObject):
    finished = Signal(int, object, str)


class _Task(QRunnable):
    def __init__(self, job_id, work):
        super().__init__()
        self.job_id = job_id
        self.work = work
        self.signals = _Signals()

    def run(self):
        try:
            result = self.work()
        except Exception as exc:
            # This is the worker boundary: report failures instead of losing them in a thread.
            print_exc()
            self.signals.finished.emit(self.job_id, None, f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(self.job_id, result, "")


class QtTaskRunner(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._ids = count()
        self._pending = {}

    def submit(self, work, succeeded, failed):
        job_id = next(self._ids)
        task = _Task(job_id, work)
        self._pending[job_id] = (task, succeeded, failed)
        task.signals.finished.connect(self._finish)
        self.pool.start(task)

    @Slot(int, object, str)
    def _finish(self, job_id, result, error):
        _, succeeded, failed = self._pending.pop(job_id)
        if error:
            failed(error)
        else:
            succeeded(result)

    def wait_for_done(self):
        self.pool.waitForDone()
