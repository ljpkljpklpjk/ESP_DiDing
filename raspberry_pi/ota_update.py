#!/usr/bin/env python3
"""Raspberry Pi bridge uploader for ESP32 ArduinoOTA firmware updates."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_OTA_PASSWORD = "lab80700"


def default_project_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def build_command(project_dir: Path, host: str, password: str) -> list[str]:
    return [
        "platformio",
        "run",
        "-d",
        str(project_dir),
        "-e",
        "esp32s3box_ota",
        "-t",
        "upload",
        "--upload-port",
        host,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the ESP32 firmware on the Raspberry Pi and upload it via ArduinoOTA."
    )
    parser.add_argument("--host", required=True, help="ESP32 IP address shown in telemetry")
    parser.add_argument(
        "--project-dir",
        default=str(default_project_dir()),
        help="PlatformIO project directory, defaults to the repository root",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_OTA_PASSWORD,
        help="ArduinoOTA password",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the PlatformIO command without running it",
    )
    args = parser.parse_args()

    if shutil.which("platformio") is None:
        print("未找到 platformio，请先在树莓派安装：pip3 install platformio", file=sys.stderr)
        return 1

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not (project_dir / "platformio.ini").exists():
        print(f"未找到 platformio.ini：{project_dir}", file=sys.stderr)
        return 1

    cmd = build_command(project_dir, args.host, args.password)
    print("即将执行 OTA 上传：")
    print(" ".join(cmd))

    if args.dry_run:
        return 0

    try:
        return subprocess.run(cmd, check=False).returncode
    except KeyboardInterrupt:
        print("OTA 上传已取消", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
