#!/usr/bin/env python3
"""Tkinter upper-controller UI for the ESP32-S3 titrator lower controller."""

import argparse
import json
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import serial


class SerialWorker:
    def __init__(self, port: str, baudrate: int, rx_queue: queue.Queue):
        self.port = port
        self.baudrate = baudrate
        self.rx_queue = rx_queue
        self._serial = None
        self._thread = None
        self._running = threading.Event()
        self._write_lock = threading.Lock()

    def start(self):
        self._serial = serial.Serial(self.port, self.baudrate, timeout=0.2)
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


class TitratorApp(tk.Tk):
    def __init__(self, worker: SerialWorker):
        super().__init__()
        self.worker = worker
        self.rx_queue = worker.rx_queue
        self.command_id = 1

        self.title("ESP32 自动滴定仪上位机")
        self.geometry("900x620")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.ph_var = tk.StringVar(value="--")
        self.temp_var = tk.StringVar(value="--")
        self.voltage_var = tk.StringVar(value="--")
        self.pwm_var = tk.StringVar(value="0")
        self.pump_var = tk.StringVar(value="0")
        self.slider_pos_var = tk.StringVar(value="--")
        self.slider_target_var = tk.StringVar(value="--")
        self.slider_distance_var = tk.StringVar(value="--")
        self.slider_enabled_var = tk.StringVar(value="--")
        self.slider_moving_var = tk.StringVar(value="--")
        self.slider_speed_var = tk.StringVar(value="1000")
        self.slider_accel_var = tk.StringVar(value="500")
        self.move_mm_var = tk.StringVar(value="10")
        self.move_sec_var = tk.StringVar(value="20")
        self.status_var = tk.StringVar(value="已启动，等待 ESP32 遥测...")

        self._build_ui()
        self.after(100, self._poll_serial)

    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        telemetry = ttk.LabelFrame(root, text="状态读取", padding=10)
        telemetry.pack(fill=tk.X)

        self._label_row(telemetry, 0, "pH", self.ph_var, "温度 ℃", self.temp_var, "电压 V", self.voltage_var)
        self._label_row(telemetry, 1, "PWM1 %", self.pwm_var, "蠕动泵 %", self.pump_var, "连接", self.status_var)

        slider = ttk.LabelFrame(root, text="丝杆滑台", padding=10)
        slider.pack(fill=tk.X, pady=8)

        self._label_row(slider, 0, "当前位置", self.slider_pos_var, "目标位置", self.slider_target_var, "剩余步数", self.slider_distance_var)
        self._label_row(slider, 1, "已使能", self.slider_enabled_var, "运动中", self.slider_moving_var, "速度", self.slider_speed_var)

        controls = ttk.Frame(slider)
        controls.grid(row=2, column=0, columnspan=6, sticky="ew", pady=8)

        ttk.Label(controls, text="速度 steps/s").grid(row=0, column=0, padx=4)
        ttk.Entry(controls, textvariable=self.slider_speed_var, width=10).grid(row=0, column=1, padx=4)
        ttk.Button(controls, text="设置速度", command=self.set_slider_speed).grid(row=0, column=2, padx=4)

        ttk.Label(controls, text="加速度").grid(row=0, column=3, padx=4)
        ttk.Entry(controls, textvariable=self.slider_accel_var, width=10).grid(row=0, column=4, padx=4)
        ttk.Button(controls, text="设置加速度", command=self.set_slider_accel).grid(row=0, column=5, padx=4)

        move = ttk.Frame(slider)
        move.grid(row=3, column=0, columnspan=6, sticky="ew", pady=8)
        ttk.Label(move, text="距离 mm").grid(row=0, column=0, padx=4)
        ttk.Entry(move, textvariable=self.move_mm_var, width=10).grid(row=0, column=1, padx=4)
        ttk.Button(move, text="移动距离", command=self.move_slider_mm).grid(row=0, column=2, padx=4)
        ttk.Label(move, text="时间 s").grid(row=0, column=3, padx=4)
        ttk.Entry(move, textvariable=self.move_sec_var, width=10).grid(row=0, column=4, padx=4)
        ttk.Button(move, text="按时间移动", command=self.move_slider_time).grid(row=0, column=5, padx=4)

        actions = ttk.Frame(slider)
        actions.grid(row=4, column=0, columnspan=6, sticky="ew", pady=8)
        for idx, (text, cmd) in enumerate([
            ("使能", self.slider_enable),
            ("关闭使能", self.slider_disable),
            ("停止", self.slider_stop),
            ("立即停止", self.slider_halt),
            ("清零", self.slider_zero),
            ("急停", self.emergency_stop),
        ]):
            ttk.Button(actions, text=text, command=cmd).grid(row=0, column=idx, padx=4)

        pump_frame = ttk.LabelFrame(root, text="PWM / 蠕动泵", padding=10)
        pump_frame.pack(fill=tk.X, pady=8)
        ttk.Label(pump_frame, text="PWM1 %").grid(row=0, column=0, padx=4)
        ttk.Entry(pump_frame, textvariable=self.pwm_var, width=10).grid(row=0, column=1, padx=4)
        ttk.Button(pump_frame, text="设置 PWM1", command=self.set_pwm1).grid(row=0, column=2, padx=4)
        ttk.Label(pump_frame, text="蠕动泵 %").grid(row=0, column=3, padx=4)
        ttk.Entry(pump_frame, textvariable=self.pump_var, width=10).grid(row=0, column=4, padx=4)
        ttk.Button(pump_frame, text="设置蠕动泵", command=self.set_pump).grid(row=0, column=5, padx=4)
        ttk.Button(pump_frame, text="停止蠕动泵", command=self.pump_stop).grid(row=0, column=6, padx=4)

        log_frame = ttk.LabelFrame(root, text="通信日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(log_frame, height=12)
        self.log.pack(fill=tk.BOTH, expand=True)

    def _label_row(self, parent, row, label1, var1, label2, var2, label3, var3):
        labels = [(label1, var1), (label2, var2), (label3, var3)]
        for i, (label, var) in enumerate(labels):
            ttk.Label(parent, text=label).grid(row=row, column=i * 2, sticky="w", padx=4, pady=3)
            ttk.Label(parent, textvariable=var).grid(row=row, column=i * 2 + 1, sticky="w", padx=4, pady=3)

    def _next_id(self):
        cid = self.command_id
        self.command_id += 1
        return cid

    def send_cmd(self, cmd, **kwargs):
        payload = {"cmd": cmd, "id": self._next_id()}
        payload.update(kwargs)
        try:
            self.worker.send(payload)
            self._log("TX " + json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            messagebox.showerror("串口发送失败", str(exc))

    def set_slider_speed(self):
        self.send_cmd("slider_speed", speed=float(self.slider_speed_var.get()))

    def set_slider_accel(self):
        self.send_cmd("slider_accel", accel=float(self.slider_accel_var.get()))

    def move_slider_mm(self):
        self.send_cmd("slider_move_mm", mm=float(self.move_mm_var.get()))

    def move_slider_time(self):
        self.send_cmd("slider_move_time", mm=float(self.move_mm_var.get()), sec=float(self.move_sec_var.get()))

    def slider_enable(self):
        self.send_cmd("slider_enable")

    def slider_disable(self):
        self.send_cmd("slider_disable")

    def slider_stop(self):
        self.send_cmd("slider_stop")

    def slider_halt(self):
        self.send_cmd("slider_halt")

    def slider_zero(self):
        self.send_cmd("slider_zero")

    def emergency_stop(self):
        self.send_cmd("emergency_stop")

    def set_pwm1(self):
        self.send_cmd("set_pwm1", percent=float(self.pwm_var.get()))

    def set_pump(self):
        self.send_cmd("set_pump", percent=float(self.pump_var.get()))

    def pump_stop(self):
        self.send_cmd("pump_stop")

    def _poll_serial(self):
        while True:
            try:
                msg = self.rx_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_message(msg)
        self.after(100, self._poll_serial)

    def _handle_message(self, msg):
        self._log("RX " + json.dumps(msg, ensure_ascii=False))
        msg_type = msg.get("type")
        if msg_type == "telemetry":
            self._update_telemetry(msg)
        elif msg_type == "boot":
            self.status_var.set("ESP32 已启动")
            if "slider" in msg:
                self._update_slider(msg["slider"])
        elif msg_type == "ack":
            self.status_var.set(f"命令 {msg.get('id', '--')} 已确认")
        elif msg_type == "done":
            self.status_var.set(f"命令 {msg.get('id', '--')} 完成 ok={msg.get('ok')}")
        elif msg_type == "error":
            self.status_var.set(f"错误: {msg.get('code', msg.get('message', '--'))}")
        elif msg_type == "serial_error":
            self.status_var.set(f"串口错误: {msg.get('message', '--')}")

    def _update_telemetry(self, msg):
        self.ph_var.set(self._fmt(msg.get("ph"), 3))
        self.temp_var.set(self._fmt(msg.get("temperature_c"), 2))
        self.voltage_var.set(self._fmt(msg.get("voltage"), 6))
        self.pwm_var.set(self._fmt(msg.get("pwm1_percent"), 1))
        self.pump_var.set(self._fmt(msg.get("pump_percent"), 1))
        slider = msg.get("slider")
        if isinstance(slider, dict):
            self._update_slider(slider)

    def _update_slider(self, slider):
        self.slider_pos_var.set(str(slider.get("pos", "--")))
        self.slider_target_var.set(str(slider.get("target", "--")))
        self.slider_distance_var.set(str(slider.get("distance", "--")))
        self.slider_enabled_var.set(str(slider.get("enabled", "--")))
        self.slider_moving_var.set(str(slider.get("moving", "--")))
        if slider.get("speed") is not None:
            self.slider_speed_var.set(self._fmt(slider.get("speed"), 1))

    @staticmethod
    def _fmt(value, decimals):
        if value is None:
            return "--"
        try:
            return f"{float(value):.{decimals}f}"
        except (TypeError, ValueError):
            return str(value)

    def _log(self, text):
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def on_close(self):
        self.worker.stop()
        self.destroy()


def main():
    parser = argparse.ArgumentParser(description="ESP32 自动滴定仪树莓派上位机")
    parser.add_argument("--port", default="/dev/ttyACM0", help="ESP32 serial port")
    parser.add_argument("--baudrate", type=int, default=115200)
    args = parser.parse_args()

    rx_queue = queue.Queue()
    worker = SerialWorker(args.port, args.baudrate, rx_queue)
    try:
        worker.start()
    except Exception as exc:
        messagebox.showerror("串口打开失败", str(exc))
        return

    app = TitratorApp(worker)
    app.mainloop()


if __name__ == "__main__":
    main()
