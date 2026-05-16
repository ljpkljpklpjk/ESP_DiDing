#!/usr/bin/env python3
"""Upload the repository's prebuilt ESP32 firmware.bin via ArduinoOTA."""

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_OTA_PASSWORD = "lab80700"
FIRMWARE_RELATIVE_PATH = Path("firmware/esp32s3box_ota/firmware.bin")


def default_project_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def build_command(project_dir: Path, host: str, password: str) -> list[str]:
    return [
        sys.executable,
        str(project_dir / "raspberry_pi" / "ota_upload_bin.py"),
        "--host",
        host,
        "--file",
        str(project_dir / FIRMWARE_RELATIVE_PATH),
        "--password",
        password,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload the prebuilt ESP32 firmware from firmware/ via ArduinoOTA."
    )
    parser.add_argument("--host", required=True, help="ESP32 IP address shown in telemetry")
    parser.add_argument(
        "--project-dir",
        default=str(default_project_dir()),
        help="Project directory, defaults to the repository root",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_OTA_PASSWORD,
        help="ArduinoOTA password",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the upload command without running it",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    firmware = project_dir / FIRMWARE_RELATIVE_PATH
    if not firmware.exists():
        print(f"未找到预编译固件：{firmware}", file=sys.stderr)
        return 1

    cmd = build_command(project_dir, args.host, args.password)
    print("即将上传预编译 OTA 固件：")
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
