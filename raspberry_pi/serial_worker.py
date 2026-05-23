import json
import queue
import threading
import time
from glob import glob

import serial
from serial.tools import list_ports


AUTO_PORT = "auto"
USB_PORT_PREFIXES = ("/dev/ttyACM", "/dev/ttyUSB")


def _looks_like_usb_serial(port_info):
    device = port_info.device
    description = (port_info.description or "").lower()
    hwid = (port_info.hwid or "").lower()
    text = f"{description} {hwid}"
    if device.startswith(USB_PORT_PREFIXES):
        return True
    return any(keyword in text for keyword in ("esp32", "usb serial", "cp210", "ch340", "wch", "silicon labs"))


def _port_score(port_info):
    device = port_info.device
    description = (port_info.description or "").lower()
    hwid = (port_info.hwid or "").lower()
    text = f"{description} {hwid}"

    if device.startswith("/dev/ttyACM"):
        return 0
    if device.startswith("/dev/ttyUSB"):
        return 1
    if _looks_like_usb_serial(port_info):
        return 2
    return 50


def list_candidate_ports():
    ports = [port for port in list_ports.comports() if _looks_like_usb_serial(port)]
    if ports:
        return sorted(ports, key=lambda item: (_port_score(item), item.device))

    devices = []
    for pattern in ("/dev/ttyACM*", "/dev/ttyUSB*"):
        devices.extend(glob(pattern))
    return sorted(set(devices))


def resolve_serial_port(port: str):
    if port and port.lower() != AUTO_PORT:
        return port

    candidates = list_candidate_ports()
    if not candidates:
        raise RuntimeError("未找到 ESP32 USB 串口，请检查 USB 连接，或用 --port 手动指定串口")

    first = candidates[0]
    return first.device if hasattr(first, "device") else first


class SerialWorker:
    def __init__(self, port: str, baudrate: int, rx_queue: queue.Queue):
        self.port = port
        self.baudrate = baudrate
        self.rx_queue = rx_queue
        self.resolved_port = None
        self._serial = None
        self._thread = None
        self._running = threading.Event()
        self._write_lock = threading.Lock()

    def start(self):
        self.resolved_port = resolve_serial_port(self.port)
        self._serial = serial.Serial(self.resolved_port, self.baudrate, timeout=0.2)
        self._running.set()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._serial and self._serial.is_open:
            self._serial.close()

    def send(self, payload: dict):
        if not self._serial or not self._serial.is_open:
            raise RuntimeError("serial port is not open")
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._write_lock:
            self._serial.write(line.encode("utf-8"))

    def _read_loop(self):
        while self._running.is_set():
            try:
                raw = self._serial.readline()
                if not raw:
                    continue
                text = raw.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    msg = json.loads(text)
                except json.JSONDecodeError:
                    msg = {"type": "raw", "line": text}
                self.rx_queue.put(msg)
            except Exception as exc:
                self.rx_queue.put({"type": "serial_error", "message": str(exc)})
                time.sleep(0.5)
