#!/usr/bin/env python3
"""Build and publish the ESP32 OTA firmware artifact into the repository."""

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ENV = "esp32s3box_ota"
DEFAULT_VERSION = "v2026.05.16.5"


def default_project_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def find_platformio(explicit: str | None) -> str:
    if explicit:
        return explicit
    for candidate in ("platformio", "pio"):
        path = shutil.which(candidate)
        if path:
            return path
    windows_path = Path.home() / ".platformio" / "penv" / "Scripts" / "platformio.exe"
    if windows_path.exists():
        return str(windows_path)
    raise RuntimeError("未找到 platformio，请安装 PlatformIO 或用 --platformio 指定路径")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ESP32 OTA firmware.bin and copy it to firmware/ for release.")
    parser.add_argument("--project-dir", default=str(default_project_dir()), help="PlatformIO project directory")
    parser.add_argument("--env", default=DEFAULT_ENV, help="PlatformIO environment")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="Firmware version recorded in version.json")
    parser.add_argument("--description", default="预编译 ESP32 OTA 固件", help="Firmware description")
    parser.add_argument("--platformio", default=None, help="Path to platformio executable")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    platformio = find_platformio(args.platformio)
    build_cmd = [platformio, "run", "-d", str(project_dir), "-e", args.env]

    print("开始编译 ESP32 OTA 固件:")
    print(" ".join(build_cmd))
    completed = subprocess.run(build_cmd, cwd=project_dir, check=False)
    if completed.returncode != 0:
        return completed.returncode

    source = project_dir / ".pio" / "build" / args.env / "firmware.bin"
    if not source.exists():
        print(f"未找到编译产物: {source}")
        return 1

    release_dir = project_dir / "firmware" / args.env
    release_dir.mkdir(parents=True, exist_ok=True)
    target = release_dir / "firmware.bin"
    shutil.copy2(source, target)

    metadata = {
        "version": args.version,
        "environment": args.env,
        "filename": "firmware.bin",
        "size_bytes": target.stat().st_size,
        "built_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "description": args.description,
    }
    version_file = release_dir / "version.json"
    version_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"已发布固件: {target}")
    print(f"已写入版本信息: {version_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
