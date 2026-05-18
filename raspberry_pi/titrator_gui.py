#!/usr/bin/env python3
"""PySide6 upper-controller UI for the ESP32-S3 titrator lower controller."""

import argparse
import queue
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from qt_app import TitratorQtApp
from qt_theme import apply_theme
from serial_worker import SerialWorker
from system_manager import DEFAULT_PROJECT_DIR


def main():
    parser = argparse.ArgumentParser(description="ESP32 自动滴定仪树莓派上位机")
    parser.add_argument("--port", default="/dev/ttyACM0", help="ESP32 serial port")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR), help="Project directory")
    args = parser.parse_args()

    qt_app = QApplication(sys.argv)
    apply_theme(qt_app)

    rx_queue = queue.Queue()
    worker = SerialWorker(args.port, args.baudrate, rx_queue)
    try:
        worker.start()
    except Exception as exc:
        QMessageBox.critical(None, "串口打开失败", str(exc))
        return 1

    window = TitratorQtApp(worker, Path(args.project_dir).expanduser().resolve())
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
