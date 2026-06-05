#!/usr/bin/env python3
"""Upload a prebuilt firmware.bin to ESP32 ArduinoOTA without PlatformIO."""

import argparse
import hashlib
import os
import random
import socket
import sys
from pathlib import Path

FLASH = 0
AUTH = 200
CHUNK_SIZE = 1024

OTA_HINTS = (
    "可能原因：ESP32 在写入 OTA 时主动断开连接。",
    "请检查：1) 下位机串口日志里的 type=ota/error code；2) ESP32 与上位机是否在同一 WiFi 且信号稳定；",
    "3) 当前 USB 首次烧录的固件是否使用带 OTA 槽的分区表；4) OTA 密码是否为固件里的 AppConfig::OTA_PASSWORD。",
)


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as firmware:
        for chunk in iter(lambda: firmware.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def send_invitation(host: str, port: int, message: str, timeout: int, password: str, filename: str, size: int, md5: str) -> bool:
    remote = (host, port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.settimeout(timeout)
        for attempt in range(1, 11):
            print(f"发送 OTA 邀请 {attempt}/10 -> {host}:{port}", flush=True)
            udp.sendto(message.encode(), remote)
            try:
                data = udp.recv(128).decode().strip()
            except socket.timeout:
                continue
            if data == "OK":
                print("ESP32 已接受 OTA 邀请", flush=True)
                return True
            if data.startswith("AUTH"):
                if not password:
                    print("ESP32 要求 OTA 密码，但当前未提供密码", file=sys.stderr, flush=True)
                    return False
                nonce = data.split()[1]
                cnonce_text = f"{filename}{size}{md5}{host}"
                cnonce = hashlib.md5(cnonce_text.encode()).hexdigest()
                passmd5 = hashlib.md5(password.encode()).hexdigest()
                result = hashlib.md5(f"{passmd5}:{nonce}:{cnonce}".encode()).hexdigest()
                auth_message = f"{AUTH} {cnonce} {result}\n"
                print("正在认证 OTA 密码...", flush=True)
                udp.sendto(auth_message.encode(), remote)
                try:
                    auth_data = udp.recv(128).decode().strip()
                except socket.timeout:
                    print("OTA 认证无响应", file=sys.stderr, flush=True)
                    return False
                if auth_data == "OK":
                    print("OTA 认证成功", flush=True)
                    return True
                print(f"OTA 认证失败: {auth_data}", file=sys.stderr, flush=True)
                return False
            print(f"ESP32 OTA 响应异常: {data}", file=sys.stderr, flush=True)
            return False
    print("ESP32 未响应 OTA 邀请", file=sys.stderr, flush=True)
    return False


def print_transfer_error(message: str, sent: int, size: int, last_response: str = ""):
    percent = int(sent * 100 / size) if size else 0
    print(f"{message}，已发送 {sent}/{size} bytes ({percent}%)", file=sys.stderr, flush=True)
    if last_response:
        print(f"ESP32 最后响应: {last_response}", file=sys.stderr, flush=True)
    for hint in OTA_HINTS:
        print(hint, file=sys.stderr, flush=True)


def upload_firmware(host: str, esp_port: int, local_host: str, local_port: int, password: str, firmware_path: Path, timeout: int, chunk_size: int) -> int:
    firmware_path = firmware_path.expanduser().resolve()
    if not firmware_path.exists():
        print(f"未找到固件文件: {firmware_path}", file=sys.stderr, flush=True)
        return 1

    size = firmware_path.stat().st_size
    md5 = file_md5(firmware_path)
    print(f"固件文件: {firmware_path}", flush=True)
    print(f"固件大小: {size} bytes", flush=True)
    print(f"固件 MD5: {md5}", flush=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((local_host, local_port))
        actual_port = server.getsockname()[1]
        server.listen(1)
        server.settimeout(timeout)
        message = f"{FLASH} {actual_port} {size} {md5}\n"

        if not send_invitation(host, esp_port, message, timeout, password, str(firmware_path), size, md5):
            return 1

        print("等待 ESP32 建立上传连接...", flush=True)
        try:
            conn, addr = server.accept()
        except socket.timeout:
            print("ESP32 未建立上传连接", file=sys.stderr, flush=True)
            return 1

        with conn:
            print(f"ESP32 已连接: {addr[0]}:{addr[1]}", flush=True)
            conn.settimeout(timeout)
            sent = 0
            last_percent = -1
            last_response = ""
            try:
                with firmware_path.open("rb") as firmware:
                    while True:
                        chunk = firmware.read(chunk_size)
                        if not chunk:
                            break
                        conn.sendall(chunk)
                        response = conn.recv(16)
                        if not response:
                            print_transfer_error("OTA 上传连接已被 ESP32 关闭", sent, size, last_response)
                            return 1
                        last_response = response.decode(errors="replace").strip()
                        if last_response.startswith("ERROR"):
                            print_transfer_error(f"ESP32 返回 OTA 错误: {last_response}", sent, size, last_response)
                            return 1
                        sent += len(chunk)
                        percent = int(sent * 100 / size)
                        if percent != last_percent and (percent % 5 == 0 or percent == 100):
                            print(f"OTA 上传进度: {percent}%", flush=True)
                            last_percent = percent
            except socket.timeout:
                print("OTA 上传超时", file=sys.stderr, flush=True)
                return 1
            except (BrokenPipeError, ConnectionResetError) as exc:
                print_transfer_error(f"OTA 上传连接被 ESP32 中断: {exc}", sent, size, last_response)
                return 1
            except OSError as exc:
                print_transfer_error(f"OTA 上传网络错误: {exc}", sent, size, last_response)
                return 1

            print("OTA 上传完成，等待 ESP32 写入结果...", flush=True)
            if "OK" in last_response:
                print("OTA 完成，ESP32 将重启", flush=True)
                return 0
            try:
                result = conn.recv(64).decode(errors="replace")
            except socket.timeout:
                result = ""
            if "OK" in result:
                print("OTA 完成，ESP32 将重启", flush=True)
                return 0
            print(f"OTA 结果异常: {result}", file=sys.stderr, flush=True)
            return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload prebuilt firmware.bin to ESP32 via ArduinoOTA.")
    parser.add_argument("--host", required=True, help="ESP32 IP address")
    parser.add_argument("--file", required=True, help="Path to firmware.bin")
    parser.add_argument("--password", default="", help="ArduinoOTA password")
    parser.add_argument("--esp-port", type=int, default=3232, help="ESP32 OTA UDP port")
    parser.add_argument("--local-host", default="0.0.0.0", help="Local bind address")
    parser.add_argument("--local-port", type=int, default=0, help="Local TCP upload port, 0 means random")
    parser.add_argument("--timeout", type=int, default=10, help="Network timeout seconds")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="TCP upload chunk size bytes")
    args = parser.parse_args()

    local_port = args.local_port or random.randint(10000, 60000)
    return upload_firmware(
        host=args.host,
        esp_port=args.esp_port,
        local_host=args.local_host,
        local_port=local_port,
        password=args.password,
        firmware_path=Path(args.file),
        timeout=args.timeout,
        chunk_size=max(256, args.chunk_size),
    )


if __name__ == "__main__":
    raise SystemExit(main())
