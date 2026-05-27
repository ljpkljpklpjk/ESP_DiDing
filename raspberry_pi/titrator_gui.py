#!/usr/bin/env python3
"""PySide6 upper-controller UI for the ESP32-S3 titrator lower controller."""

import argparse
import queue
import sys
from pathlib import Path

from serial_worker import AUTO_PORT, SerialWorker
from system_manager import DEFAULT_PROJECT_DIR


def main():
    parser = argparse.ArgumentParser(description="ESP32 自动滴定仪 SH800/Linux 上位机")
    parser.add_argument(
        "--port",
        default=AUTO_PORT,
        help="ESP32 serial port, or 'auto' to pick SH800 RS485/USB serial automatically",
    )
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR), help="Project directory")
    parser.add_argument("--log-dir", default=None, help="Paper-format data directory")
    parser.add_argument("--run-id", default=None, help="Run id used for CSV/JSONL filenames")
    args = parser.parse_args()

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError as exc:
        print("未找到 PySide6。SH800 请先安装 Python 3.12 和 PySide6。", file=sys.stderr)
        print("示例：python3.12 -m pip install --user pyserial PySide6", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    from qt_app import TitratorQtApp
    from qt_theme import apply_theme

    qt_app = QApplication(sys.argv)
    apply_theme(qt_app)

    rx_queue = queue.Queue()
    worker = SerialWorker(args.port, args.baudrate, rx_queue)
    try:
        worker.start()
    except Exception as exc:
        QMessageBox.critical(None, "串口打开失败", str(exc))
        return 1

    log_dir = Path(args.log_dir).expanduser().resolve() if args.log_dir else None
    window = TitratorQtApp(
        worker,
        Path(args.project_dir).expanduser().resolve(),
        log_dir=log_dir,
        run_id=args.run_id,
    )
    if worker.resolved_port:
        window.status_label.setText(f"已连接串口 {worker.resolved_port}，等待 ESP32 遥测...")
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
