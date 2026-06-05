import os
import subprocess

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot


class TaskSignals(QObject):
    finished = Signal(int, str)


class SystemTask(QRunnable):
    def __init__(self, func):
        super().__init__()
        self.func = func
        self.signals = TaskSignals()

    @Slot()
    def run(self):
        try:
            result = self.func()
            if isinstance(result, tuple):
                code, output = result
            else:
                code, output = 0, str(result)
        except Exception as exc:
            code, output = 1, str(exc)
        self.signals.finished.emit(code, output or "无输出")


class OtaSignals(QObject):
    line = Signal(str)
    finished = Signal(int, str)


class OtaTask(QRunnable):
    def __init__(self, cmd, cwd):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd
        self.signals = OtaSignals()

    @Slot()
    def run(self):
        last_line = ""
        code = 1
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            process = subprocess.Popen(
                self.cmd,
                cwd=self.cwd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                env=env,
            )
            assert process.stdout is not None
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                last_line = line
                self.signals.line.emit(line)
            code = process.wait()
        except Exception as exc:
            last_line = str(exc)
            code = 1
        self.signals.finished.emit(code, last_line or "无输出")


def thread_pool():
    return QThreadPool.globalInstance()
