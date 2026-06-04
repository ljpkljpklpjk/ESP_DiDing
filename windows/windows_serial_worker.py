import json
import queue
import threading
import time

import serial
from serial.tools import list_ports


AUTO_PORT = "auto"


def _looks_like_usb_serial(port_info):
    """Detect USB-serial adapters (CP210x, CH340, etc.) on Windows."""
    device = port_info.device
    description = (port_info.description or "").lower()
    hwid = (port_info.hwid or "").lower()
    text = f"{description} {hwid}"
    # Windows COM ports
    if device.upper().startswith("COM"):
        return any(
            keyword in text
            for keyword in (
                "esp32",
                "usb serial",
                "cp210",
                "ch340",
                "wch",
                "silicon labs",
                "usb-serial",
                "ftdi",
                "arduino",
            )
        )
    return False


def _looks_like_rs485_serial(port_info):
    """Detect RS485/serial devices on Windows."""
    description = (port_info.description or "").lower()
    hwid = (port_info.hwid or "").lower()
    text = f"{description} {hwid}"
    return any(keyword in text for keyword in ("rs485", "rs-485", "serial port"))


def _port_score(port_info):
    """Score port priority — lower is preferred."""
    device = port_info.device
    description = (port_info.description or "").lower()
    hwid = (port_info.hwid or "").lower()
    text = f"{description} {hwid}"

    # USB-serial with explicit ESP32 or CP210/CH340 gets top priority
    if "esp32" in text:
        return 0
    if any(kw in text for kw in ("cp210", "ch340", "wch", "silicon labs")):
        return 1
    if _looks_like_usb_serial(port_info):
        return 2
    if "rs485" in text or "rs-485" in text:
        return 3
    if _looks_like_rs485_serial(port_info):
        return 20
    # Regular COM ports
    if device.upper().startswith("COM"):
        return 50
    return 100


def list_candidate_ports():
    """List serial ports likely to be the ESP32 device."""
    ports = [
        port
        for port in list_ports.comports()
        if _looks_like_usb_serial(port) or _looks_like_rs485_serial(port)
    ]
    if ports:
        return sorted(ports, key=lambda item: (_port_score(item), item.device))

    # Fallback: return all available COM ports
    all_ports = list(list_ports.comports())
    if all_ports:
        return sorted(all_ports, key=lambda item: (_port_score(item), item.device))

    return []


def resolve_serial_port(port: str):
    """Resolve 'auto' to the best candidate, or return the port as-is."""
    if port and port.lower() != AUTO_PORT:
        return port

    candidates = list_candidate_ports()
    if not candidates:
        raise RuntimeError(
            "未找到串口设备，请检查 USB 串口连接，或用 --port 手动指定串口（如 COM3）"
        )

    first = candidates[0]
    return first.device if hasattr(first, "device") else first


class SerialWorker:
    """Background serial I/O thread using JSON Lines protocol."""

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
        self._serial = serial.Serial(
            port=self.resolved_port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.2,
        )
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
