#!/usr/bin/env python3
"""PySide6 upper-controller UI for the ESP32-S3 titrator — Windows edition."""

import argparse
import queue
import sys
from pathlib import Path


def _setup_path():
    """Add raspberry_pi/ to sys.path so shared modules can be imported."""
    repo_root = Path(__file__).resolve().parents[1]
    shared = repo_root / "raspberry_pi"
    if str(shared) not in sys.path:
        sys.path.insert(0, str(shared))
    # Also add the windows/ directory itself
    windows_dir = repo_root / "windows"
    if str(windows_dir) not in sys.path:
        sys.path.insert(0, str(windows_dir))


def main():
    _setup_path()

    from windows_serial_worker import AUTO_PORT, SerialWorker
    from windows_system_manager import DEFAULT_PROJECT_DIR

    parser = argparse.ArgumentParser(description="ESP32 自动滴定仪 Windows 上位机")
    parser.add_argument(
        "--port",
        default=AUTO_PORT,
        help="ESP32 serial port, or 'auto' to pick COM port automatically",
    )
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument(
        "--project-dir", default=str(DEFAULT_PROJECT_DIR), help="Project directory"
    )
    parser.add_argument(
        "--log-dir", default=None, help="Paper-format data directory"
    )
    parser.add_argument(
        "--run-id", default=None, help="Run id used for CSV/JSONL filenames"
    )
    parser.add_argument(
        "--group", default=None, help="Experiment group, for example G1"
    )
    parser.add_argument(
        "--repeat", type=int, default=None, help="Experiment repeat index"
    )
    parser.add_argument(
        "--control-mode",
        default="normal_dosing",
        help="Control mode written to dataset",
    )
    parser.add_argument("--target-ph-low", type=float, default=6.8)
    parser.add_argument("--target-ph-high", type=float, default=7.2)
    parser.add_argument("--target-tds-mg-l", type=float, default=350.0)
    parser.add_argument("--target-concentration-mg-l", type=float, default=8.0)
    parser.add_argument("--duration-s", type=int, default=None)
    parser.add_argument("--sample-interval-s", type=int, default=1)
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=0,
        help="TCP relay port for LAN telemetry forwarding (0 = disabled)",
    )
    args = parser.parse_args()

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError as exc:
        print("未找到 PySide6。请先安装依赖：", file=sys.stderr)
        print("  pip install pyserial PySide6", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    from windows_qt_app import TitratorQtApp
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
        group=args.group,
        repeat=args.repeat,
        control_mode=args.control_mode,
        target_ph_low=args.target_ph_low,
        target_ph_high=args.target_ph_high,
        target_tds_mg_l=args.target_tds_mg_l,
        target_concentration_mg_l=args.target_concentration_mg_l,
        duration_s=args.duration_s,
        sample_interval_s=args.sample_interval_s,
        tcp_port=args.tcp_port,
    )
    if worker.resolved_port:
        window.status_label.setText(
            f"已连接串口 {worker.resolved_port}，等待 ESP32 遥测..."
        )
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
