#!/usr/bin/env python3
"""Tkinter upper-controller UI for the ESP32-S3 titrator lower controller."""

import argparse
import json
import os
import queue
import shutil
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import serial


DEFAULT_OTA_PASSWORD = "lab80700"
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[1]
FIRMWARE_RELATIVE_PATH = Path("firmware/esp32s3box_ota/firmware.bin")
FIRMWARE_VERSION_RELATIVE_PATH = Path("firmware/esp32s3box_ota/version.json")
GITEE_REPO_URL = "https://gitee.com/bidi2004/diding.git"
GITEE_BRANCH = "codex/new_feature"
GITEE_REMOTE = "gitee"


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


class PiSystemManager:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def _run(self, cmd, cwd=None):
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return completed.returncode, completed.stdout.strip()

    def wifi_status(self):
        radio = "未知"
        connected_ssid = ""
        ip_addr = ""

        if shutil.which("nmcli"):
            radio_code, radio_out = self._run(["nmcli", "radio", "wifi"])
            if radio_code == 0 and radio_out:
                radio = radio_out

            code, out = self._run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev", "status"])
            if code == 0:
                for line in out.splitlines():
                    parts = line.split(":", 3)
                    if len(parts) == 4:
                        _, dev_type, state, connection = parts
                        if dev_type == "wifi" and state in ("connected", "已连接") and connection:
                            connected_ssid = connection
                            break

            if not connected_ssid:
                code, out = self._run(["nmcli", "-t", "-f", "ACTIVE,SSID", "connection", "show", "--active"])
                if code == 0:
                    for line in out.splitlines():
                        active, _, ssid = line.partition(":")
                        if active == "yes" and ssid:
                            connected_ssid = ssid
                            break

        if shutil.which("iwgetid"):
            code, out = self._run(["iwgetid", "-r"])
            if code == 0 and out:
                connected_ssid = out

        if shutil.which("hostname"):
            code, out = self._run(["hostname", "-I"])
            if code == 0 and out:
                ip_addr = out.split()[0]

        if connected_ssid:
            ip_text = f"，IP: {ip_addr}" if ip_addr else ""
            return f"WiFi: {radio}，当前连接: {connected_ssid}{ip_text}"
        return f"WiFi: {radio}，当前未连接"

    def wifi_on(self):
        return self._require_nmcli(["nmcli", "radio", "wifi", "on"])

    def wifi_off(self):
        return self._require_nmcli(["nmcli", "radio", "wifi", "off"])

    def connect_wifi(self, ssid: str, password: str):
        if not ssid:
            return 1, "请输入 WiFi 名称"
        cmd = ["nmcli", "dev", "wifi", "connect", ssid]
        if password:
            cmd.extend(["password", password])
        return self._require_nmcli(cmd)

    def ensure_gitee_remote(self):
        if not shutil.which("git"):
            return 1, "未找到 git"
        if not (self.project_dir / ".git").exists():
            return 1, f"当前项目路径不是 Git 仓库：{self.project_dir}"

        code, remotes = self._run(["git", "remote"], cwd=self.project_dir)
        if code != 0:
            return code, remotes

        remote_names = set(remotes.split())
        if GITEE_REMOTE in remote_names:
            code, out = self._run(["git", "remote", "set-url", GITEE_REMOTE, GITEE_REPO_URL], cwd=self.project_dir)
        else:
            code, out = self._run(["git", "remote", "add", GITEE_REMOTE, GITEE_REPO_URL], cwd=self.project_dir)
        if code != 0:
            return code, out

        self._run(["git", "fetch", GITEE_REMOTE, GITEE_BRANCH], cwd=self.project_dir)
        self._run(["git", "branch", "--set-upstream-to", f"{GITEE_REMOTE}/{GITEE_BRANCH}", GITEE_BRANCH], cwd=self.project_dir)
        return 0, f"已设置 Gitee 更新源：{GITEE_REPO_URL} 分支 {GITEE_BRANCH}"

    def check_git_update(self):
        if not shutil.which("git"):
            return 1, "未找到 git"
        self.ensure_gitee_remote()
        code, out = self._run(["git", "fetch", GITEE_REMOTE, GITEE_BRANCH], cwd=self.project_dir)
        if code != 0:
            return code, out
        _, local = self._run(["git", "rev-parse", "HEAD"], cwd=self.project_dir)
        _, remote = self._run(["git", "rev-parse", f"{GITEE_REMOTE}/{GITEE_BRANCH}"], cwd=self.project_dir)
        if local == remote:
            return 0, "当前已经是 Gitee 最新版本"
        return 0, f"Gitee 发现新版本：{local[:7]} -> {remote[:7]}"

    def update_project(self):
        if not shutil.which("git"):
            return 1, "未找到 git"
        code, out = self.ensure_gitee_remote()
        if code != 0:
            return code, out
        return self._run(["git", "pull", "--ff-only", GITEE_REMOTE, GITEE_BRANCH], cwd=self.project_dir)

    def firmware_path(self):
        return self.project_dir / FIRMWARE_RELATIVE_PATH

    def firmware_version_path(self):
        return self.project_dir / FIRMWARE_VERSION_RELATIVE_PATH

    def firmware_version_text(self):
        path = self.firmware_version_path()
        if not path.exists():
            return "未找到固件版本信息"
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return f"固件版本信息读取失败: {exc}"
        version = info.get("version", "未知版本")
        built_at = info.get("built_at", "未知时间")
        size = info.get("size_bytes", "未知大小")
        desc = info.get("description", "")
        return f"固件 {version}，构建时间 {built_at}，大小 {size} bytes，{desc}"

    def ota_command(self, host: str, password: str):
        return [
            "python3",
            str(self.project_dir / "raspberry_pi" / "ota_upload_bin.py"),
            "--host",
            host,
            "--file",
            str(self.firmware_path()),
            "--password",
            password,
        ]

    def ota_update(self, host: str, password: str):
        if not host:
            return 1, "请输入 ESP32 IP"
        if not self.firmware_path().exists():
            return 1, f"未找到预编译固件：{self.firmware_path()}"
        return self._run(self.ota_command(host, password))

    def _require_nmcli(self, cmd):
        if not shutil.which("nmcli"):
            return 1, "未找到 nmcli，请在树莓派上启用/安装 NetworkManager"
        return self._run(cmd)


class TitratorApp(tk.Tk):
    def __init__(self, worker: SerialWorker, project_dir: Path):
        super().__init__()
        self.worker = worker
        self.rx_queue = worker.rx_queue
        self.command_id = 1
        self.system = PiSystemManager(project_dir)

        self.title("ESP32 自动滴定仪上位机")
        self.geometry("1024x700")
        self.minsize(900, 620)
        self.configure(bg="#f3f6fb")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.ph_var = tk.StringVar(value="--")
        self.temp_var = tk.StringVar(value="--")
        self.voltage_var = tk.StringVar(value="--")
        self.pwm_display_var = tk.StringVar(value="0")
        self.pump_display_var = tk.StringVar(value="0")
        self.pwm_set_var = tk.StringVar(value="0")
        self.pump_set_var = tk.StringVar(value="0")
        self.slider_pos_var = tk.StringVar(value="--")
        self.slider_target_var = tk.StringVar(value="--")
        self.slider_distance_var = tk.StringVar(value="--")
        self.slider_enabled_var = tk.StringVar(value="--")
        self.slider_moving_var = tk.StringVar(value="--")
        self.slider_speed_display_var = tk.StringVar(value="1000")
        self.slider_speed_set_var = tk.StringVar(value="1000")
        self.slider_accel_var = tk.StringVar(value="500")
        self.move_mm_var = tk.StringVar(value="10")
        self.move_sec_var = tk.StringVar(value="20")
        self.status_var = tk.StringVar(value="已启动，等待 ESP32 遥测...")
        self.pi_wifi_status_var = tk.StringVar(value="未刷新")
        self.wifi_ssid_var = tk.StringVar(value="Lab807_2.4G")
        self.wifi_password_var = tk.StringVar(value="")
        self.update_status_var = tk.StringVar(value="未检查")
        self.ota_progress_var = tk.StringVar(value="OTA 未开始")
        self.project_dir_var = tk.StringVar(value=str(project_dir))
        self.esp32_ip_var = tk.StringVar(value="")
        self.ota_password_var = tk.StringVar(value=DEFAULT_OTA_PASSWORD)
        self.ota_running = False
        self.ota_start_time = 0.0
        self.ota_last_output_time = 0.0
        self.ota_button = None

        self._configure_style()
        self._build_ui()
        self.after(100, self._poll_serial)
        self.refresh_wifi_status()

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f3f6fb")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#f3f6fb", font=("Arial", 11))
        style.configure("Card.TLabel", background="#ffffff", font=("Arial", 11))
        style.configure("Value.TLabel", background="#ffffff", foreground="#1f2937", font=("Arial", 18, "bold"))
        style.configure("Title.TLabel", background="#f3f6fb", foreground="#0f172a", font=("Arial", 18, "bold"))
        style.configure("Subtle.TLabel", background="#ffffff", foreground="#64748b", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 11), padding=(12, 8))
        style.configure("Primary.TButton", font=("Arial", 11, "bold"), padding=(14, 9))
        style.configure("Danger.TButton", font=("Arial", 11, "bold"), padding=(14, 9), foreground="#b91c1c")
        style.configure("TEntry", padding=5)
        style.configure("TNotebook", background="#f3f6fb", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Arial", 12, "bold"), padding=(18, 10))
        style.configure("TLabelframe", background="#f3f6fb", padding=12)
        style.configure("TLabelframe.Label", background="#f3f6fb", foreground="#0f172a", font=("Arial", 12, "bold"))

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        control_tab = ttk.Frame(notebook, padding=10)
        network_tab = ttk.Frame(notebook, padding=10)
        update_tab = ttk.Frame(notebook, padding=10)
        notebook.add(control_tab, text="滴定控制")
        notebook.add(network_tab, text="网络设置")
        notebook.add(update_tab, text="系统更新")

        self._build_control_tab(control_tab)
        self._build_network_tab(network_tab)
        self._build_update_tab(update_tab)

    def _build_control_tab(self, root):
        ttk.Label(root, text="滴定控制", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        telemetry = ttk.Frame(root, style="TFrame")
        telemetry.pack(fill=tk.X)
        for col in range(6):
            telemetry.columnconfigure(col, weight=1)
        self._status_card(telemetry, 0, 0, "pH", self.ph_var)
        self._status_card(telemetry, 0, 1, "温度 ℃", self.temp_var)
        self._status_card(telemetry, 0, 2, "电压 V", self.voltage_var)
        self._status_card(telemetry, 0, 3, "PWM1 %", self.pwm_display_var)
        self._status_card(telemetry, 0, 4, "蠕动泵 %", self.pump_display_var)
        self._status_card(telemetry, 0, 5, "连接", self.status_var)

        slider = ttk.LabelFrame(root, text="丝杆滑台", padding=12)
        slider.pack(fill=tk.X, pady=12)
        for col in range(6):
            slider.columnconfigure(col, weight=1)
        self._value_cell(slider, 0, 0, "当前位置", self.slider_pos_var)
        self._value_cell(slider, 0, 1, "目标位置", self.slider_target_var)
        self._value_cell(slider, 0, 2, "剩余步数", self.slider_distance_var)
        self._value_cell(slider, 0, 3, "已使能", self.slider_enabled_var)
        self._value_cell(slider, 0, 4, "运动中", self.slider_moving_var)
        self._value_cell(slider, 0, 5, "当前速度", self.slider_speed_display_var)

        controls = ttk.Frame(slider)
        controls.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(12, 4))
        for col in range(10):
            controls.columnconfigure(col, weight=1)
        ttk.Label(controls, text="速度 steps/s").grid(row=0, column=0, padx=4, sticky="e")
        ttk.Entry(controls, textvariable=self.slider_speed_set_var, width=10).grid(row=0, column=1, padx=4, sticky="ew")
        ttk.Button(controls, text="设置速度", style="Primary.TButton", command=self.set_slider_speed).grid(row=0, column=2, padx=4)
        ttk.Label(controls, text="加速度").grid(row=0, column=3, padx=4, sticky="e")
        ttk.Entry(controls, textvariable=self.slider_accel_var, width=10).grid(row=0, column=4, padx=4, sticky="ew")
        ttk.Button(controls, text="设置加速度", command=self.set_slider_accel).grid(row=0, column=5, padx=4)
        ttk.Label(controls, text="距离 mm").grid(row=1, column=0, padx=4, pady=8, sticky="e")
        ttk.Entry(controls, textvariable=self.move_mm_var, width=10).grid(row=1, column=1, padx=4, pady=8, sticky="ew")
        ttk.Button(controls, text="移动距离", style="Primary.TButton", command=self.move_slider_mm).grid(row=1, column=2, padx=4, pady=8)
        ttk.Label(controls, text="时间 s").grid(row=1, column=3, padx=4, pady=8, sticky="e")
        ttk.Entry(controls, textvariable=self.move_sec_var, width=10).grid(row=1, column=4, padx=4, pady=8, sticky="ew")
        ttk.Button(controls, text="按时间移动", command=self.move_slider_time).grid(row=1, column=5, padx=4, pady=8)

        actions = ttk.Frame(slider)
        actions.grid(row=2, column=0, columnspan=6, sticky="ew", pady=8)
        for idx, (text, cmd, style_name) in enumerate([
            ("使能", self.slider_enable, "Primary.TButton"),
            ("关闭使能", self.slider_disable, "TButton"),
            ("停止", self.slider_stop, "TButton"),
            ("立即停止", self.slider_halt, "TButton"),
            ("清零", self.slider_zero, "TButton"),
            ("急停", self.emergency_stop, "Danger.TButton"),
        ]):
            actions.columnconfigure(idx, weight=1)
            ttk.Button(actions, text=text, style=style_name, command=cmd).grid(row=0, column=idx, padx=5, sticky="ew")

        pump_frame = ttk.LabelFrame(root, text="PWM / 蠕动泵", padding=12)
        pump_frame.pack(fill=tk.X, pady=(0, 12))
        for col in range(7):
            pump_frame.columnconfigure(col, weight=1)
        ttk.Label(pump_frame, text="PWM1 %").grid(row=0, column=0, padx=4, sticky="e")
        ttk.Entry(pump_frame, textvariable=self.pwm_set_var, width=10).grid(row=0, column=1, padx=4, sticky="ew")
        ttk.Button(pump_frame, text="设置 PWM1", style="Primary.TButton", command=self.set_pwm1).grid(row=0, column=2, padx=4)
        ttk.Label(pump_frame, text="蠕动泵 %").grid(row=0, column=3, padx=4, sticky="e")
        ttk.Entry(pump_frame, textvariable=self.pump_set_var, width=10).grid(row=0, column=4, padx=4, sticky="ew")
        ttk.Button(pump_frame, text="设置蠕动泵", style="Primary.TButton", command=self.set_pump).grid(row=0, column=5, padx=4)
        ttk.Button(pump_frame, text="停止蠕动泵", command=self.pump_stop).grid(row=0, column=6, padx=4)

        log_frame = ttk.LabelFrame(root, text="通信日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(log_frame, height=8, bg="#0f172a", fg="#e5e7eb", insertbackground="#e5e7eb", relief=tk.FLAT)
        self.log.pack(fill=tk.BOTH, expand=True)

    def _build_network_tab(self, root):
        ttk.Label(root, text="网络设置", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        frame = ttk.LabelFrame(root, text="树莓派 WiFi", padding=14)
        frame.pack(fill=tk.X)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        ttk.Label(frame, text="状态").grid(row=0, column=0, sticky="w", padx=4, pady=6)
        ttk.Label(frame, textvariable=self.pi_wifi_status_var, wraplength=760).grid(row=0, column=1, columnspan=4, sticky="ew", padx=4, pady=6)
        ttk.Button(frame, text="刷新状态", style="Primary.TButton", command=self.refresh_wifi_status).grid(row=1, column=0, padx=4, pady=8, sticky="ew")
        ttk.Button(frame, text="打开 WiFi", command=self.wifi_on).grid(row=1, column=1, padx=4, pady=8, sticky="ew")
        ttk.Button(frame, text="关闭 WiFi", command=self.wifi_off).grid(row=1, column=2, padx=4, pady=8, sticky="ew")
        ttk.Label(frame, text="WiFi 名称").grid(row=2, column=0, sticky="w", padx=4, pady=8)
        ttk.Entry(frame, textvariable=self.wifi_ssid_var, width=28).grid(row=2, column=1, sticky="ew", padx=4, pady=8)
        ttk.Label(frame, text="密码").grid(row=2, column=2, sticky="w", padx=4, pady=8)
        ttk.Entry(frame, textvariable=self.wifi_password_var, width=28, show="*").grid(row=2, column=3, sticky="ew", padx=4, pady=8)
        ttk.Button(frame, text="连接 WiFi", style="Primary.TButton", command=self.connect_wifi).grid(row=2, column=4, padx=4, pady=8, sticky="ew")

    def _build_update_tab(self, root):
        ttk.Label(root, text="系统更新", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        frame = ttk.LabelFrame(root, text="Gitee / OTA", padding=14)
        frame.pack(fill=tk.X)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        ttk.Label(frame, text="项目路径").grid(row=0, column=0, sticky="w", padx=4, pady=8)
        ttk.Entry(frame, textvariable=self.project_dir_var, width=70).grid(row=0, column=1, columnspan=3, sticky="ew", padx=4, pady=8)
        ttk.Label(frame, text="ESP32 IP").grid(row=1, column=0, sticky="w", padx=4, pady=8)
        ttk.Entry(frame, textvariable=self.esp32_ip_var, width=24).grid(row=1, column=1, sticky="ew", padx=4, pady=8)
        ttk.Label(frame, text="OTA 密码").grid(row=1, column=2, sticky="w", padx=4, pady=8)
        ttk.Entry(frame, textvariable=self.ota_password_var, width=24, show="*").grid(row=1, column=3, sticky="ew", padx=4, pady=8)
        ttk.Button(frame, text="检查 Gitee 更新", command=self.check_project_update).grid(row=2, column=0, padx=4, pady=10, sticky="ew")
        ttk.Button(frame, text="从 Gitee 更新代码", style="Primary.TButton", command=self.update_project).grid(row=2, column=1, padx=4, pady=10, sticky="ew")
        self.ota_button = ttk.Button(frame, text="更新 ESP32 固件 OTA", style="Primary.TButton", command=self.update_esp32_ota)
        self.ota_button.grid(row=2, column=2, padx=4, pady=10, sticky="ew")
        ttk.Label(frame, text="OTA 进度").grid(row=3, column=0, sticky="w", padx=4, pady=8)
        ttk.Label(frame, textvariable=self.ota_progress_var, wraplength=800).grid(row=3, column=1, columnspan=3, sticky="ew", padx=4, pady=8)
        self.ota_progress_bar = ttk.Progressbar(frame, mode="indeterminate")
        self.ota_progress_bar.grid(row=4, column=1, columnspan=3, sticky="ew", padx=4, pady=8)
        ttk.Label(frame, text="状态").grid(row=5, column=0, sticky="w", padx=4, pady=8)
        ttk.Label(frame, textvariable=self.update_status_var, wraplength=800).grid(row=5, column=1, columnspan=3, sticky="ew", padx=4, pady=8)

        log_frame = ttk.LabelFrame(root, text="OTA 实时输出", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.ota_log = tk.Text(log_frame, height=12, bg="#111827", fg="#d1d5db", insertbackground="#d1d5db", relief=tk.FLAT)
        self.ota_log.pack(fill=tk.BOTH, expand=True)

    def _status_card(self, parent, row, col, title, var):
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        ttk.Label(card, text=title, style="Subtle.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=var, style="Value.TLabel", wraplength=140).pack(anchor="w", pady=(5, 0))

    def _value_cell(self, parent, row, col, title, var):
        cell = ttk.Frame(parent, padding=8)
        cell.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        ttk.Label(cell, text=title).pack(anchor="w")
        ttk.Label(cell, textvariable=var, font=("Arial", 13, "bold")).pack(anchor="w", pady=(3, 0))

    def _label_row(self, parent, row, label1, var1, label2, var2, label3, var3):
        labels = [(label1, var1), (label2, var2), (label3, var3)]
        for i, (label, var) in enumerate(labels):
            ttk.Label(parent, text=label).grid(row=row, column=i * 2, sticky="w", padx=4, pady=3)
            ttk.Label(parent, textvariable=var).grid(row=row, column=i * 2 + 1, sticky="w", padx=4, pady=3)

    def _next_id(self):
        cid = self.command_id
        self.command_id += 1
        return cid

    def _run_system_task(self, label, func, status_var):
        status_var.set(f"{label}中...")

        def worker():
            try:
                result = func()
                if isinstance(result, tuple):
                    code, output = result
                else:
                    code, output = 0, str(result)
                prefix = "完成" if code == 0 else "失败"
                text = f"{label}{prefix}: {output or '无输出'}"
            except Exception as exc:
                text = f"{label}失败: {exc}"
            self.after(0, lambda: status_var.set(text))

        threading.Thread(target=worker, daemon=True).start()

    def send_cmd(self, cmd, **kwargs):
        payload = {"cmd": cmd, "id": self._next_id()}
        payload.update(kwargs)
        try:
            self.worker.send(payload)
            self._log("TX " + json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            messagebox.showerror("串口发送失败", str(exc))

    def set_slider_speed(self):
        self.send_cmd("slider_speed", speed=float(self.slider_speed_set_var.get()))

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
        self.send_cmd("set_pwm1", percent=float(self.pwm_set_var.get()))

    def set_pump(self):
        self.send_cmd("set_pump", percent=float(self.pump_set_var.get()))

    def pump_stop(self):
        self.send_cmd("pump_stop")

    def refresh_wifi_status(self):
        self._run_system_task("刷新 WiFi 状态", self.system.wifi_status, self.pi_wifi_status_var)

    def wifi_on(self):
        self._run_system_task("打开 WiFi", self.system.wifi_on, self.pi_wifi_status_var)

    def wifi_off(self):
        self._run_system_task("关闭 WiFi", self.system.wifi_off, self.pi_wifi_status_var)

    def connect_wifi(self):
        ssid = self.wifi_ssid_var.get().strip()
        password = self.wifi_password_var.get()
        self._run_system_task("连接 WiFi", lambda: self.system.connect_wifi(ssid, password), self.pi_wifi_status_var)

    def check_project_update(self):
        self.system.project_dir = Path(self.project_dir_var.get()).expanduser().resolve()
        self._run_system_task("检查项目更新", self.system.check_git_update, self.update_status_var)

    def update_project(self):
        self.system.project_dir = Path(self.project_dir_var.get()).expanduser().resolve()
        self._run_system_task("更新上位机代码", self.system.update_project, self.update_status_var)

    def _run_ota_task(self, host):
        if self.ota_running:
            self.update_status_var.set("ESP32 OTA 正在运行，请等待当前任务完成")
            return
        if not host:
            self.update_status_var.set("ESP32 OTA 更新失败: 请输入 ESP32 IP")
            return
        if not self.system.firmware_path().exists():
            self.update_status_var.set(f"ESP32 OTA 更新失败: 未找到预编译固件 {self.system.firmware_path()}")
            return

        password = self.ota_password_var.get()
        cmd = self.system.ota_command(host, password)
        firmware_info = self.system.firmware_version_text()
        self.ota_running = True
        self.ota_start_time = time.time()
        self.ota_last_output_time = self.ota_start_time
        self.update_status_var.set("ESP32 OTA 更新中...")
        self.ota_progress_var.set("准备上传预编译固件...")
        if self.ota_button:
            self.ota_button.state(["disabled"])
        self.ota_log.delete("1.0", tk.END)
        self._append_ota_log(firmware_info)
        self._append_ota_log("执行命令: " + " ".join(cmd))
        self.ota_progress_bar.start(10)
        self._update_ota_heartbeat()

        def worker():
            last_line = ""
            code = 1
            try:
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                process = subprocess.Popen(
                    cmd,
                    cwd=self.system.project_dir,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    env=env,
                )
                assert process.stdout is not None
                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    last_line = line
                    progress = self._ota_progress_text(line)
                    self.after(0, lambda p=progress, l=line: self._update_ota_progress(p, l))
                code = process.wait()
            except Exception as exc:
                last_line = str(exc)
                code = 1

            def finish():
                self.ota_running = False
                self.ota_progress_bar.stop()
                if self.ota_button:
                    self.ota_button.state(["!disabled"])
                if code == 0:
                    self.ota_progress_var.set("OTA 完成，等待 ESP32 重启并恢复遥测")
                    self.update_status_var.set("ESP32 OTA 更新完成")
                    self._append_ota_log("OTA 任务完成")
                else:
                    self.ota_progress_var.set(f"OTA 失败: {last_line or '无输出'}")
                    self.update_status_var.set("ESP32 OTA 更新失败")
                    self._append_ota_log(f"OTA 任务失败: {last_line or '无输出'}")

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def _update_ota_progress(self, progress, line):
        self.ota_last_output_time = time.time()
        self.ota_progress_var.set(progress)
        self.update_status_var.set(line)
        self._append_ota_log(line)

    def _update_ota_heartbeat(self):
        if not self.ota_running:
            return
        now = time.time()
        elapsed = int(now - self.ota_start_time)
        idle = int(now - self.ota_last_output_time)
        self.ota_progress_var.set(f"OTA 运行中，已用 {elapsed}s，最近输出 {idle}s 前")
        self.after(1000, self._update_ota_heartbeat)

    def _append_ota_log(self, text):
        self.ota_log.insert(tk.END, text + "\n")
        self.ota_log.see(tk.END)

    @staticmethod
    def _ota_progress_text(line):
        lower = line.lower()
        if "固件文件" in line or "固件大小" in line or "固件 md5" in lower:
            return "正在检查预编译固件..."
        if "发送 ota 邀请" in lower or "已接受 ota 邀请" in lower:
            return "正在连接 ESP32 OTA 服务..."
        if "认证" in line:
            return line
        if "等待 esp32 建立上传连接" in lower or "已连接" in line:
            return "ESP32 已连接，准备上传..."
        if "ota 上传进度" in lower:
            return line
        if "ota 上传完成" in lower:
            return "OTA 上传完成，等待写入结果..."
        if "ota 完成" in lower:
            return "OTA 完成，ESP32 将重启"
        if "processing esp32s3box_ota" in lower:
            return "正在准备 OTA 编译环境..."
        if "verbose mode can be enabled" in lower:
            return "PlatformIO 已开始执行..."
        if "building" in lower or "compiling" in lower:
            return "正在编译固件..."
        if "linking" in lower:
            return "正在链接固件..."
        if "checking size" in lower or "memory usage" in lower or lower.startswith("ram:") or lower.startswith("flash:"):
            return "正在检查固件大小..."
        if "configuring upload protocol" in lower:
            return "正在配置 OTA 上传协议..."
        if "uploading" in lower or "upload" in lower:
            return "正在 OTA 上传到 ESP32..."
        if "success" in lower:
            return "OTA/编译成功"
        if "error" in lower or "failed" in lower:
            return "OTA 出错，请查看实时输出"
        return line

    def update_esp32_ota(self):
        self.system.project_dir = Path(self.project_dir_var.get()).expanduser().resolve()
        host = self.esp32_ip_var.get().strip()
        self._run_ota_task(host)

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
        self.pwm_display_var.set(self._fmt(msg.get("pwm1_percent"), 1))
        self.pump_display_var.set(self._fmt(msg.get("pump_percent"), 1))
        ip = msg.get("ip")
        if ip:
            self.esp32_ip_var.set(str(ip))
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
            self.slider_speed_display_var.set(self._fmt(slider.get("speed"), 1))

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
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR), help="PlatformIO project directory")
    args = parser.parse_args()

    rx_queue = queue.Queue()
    worker = SerialWorker(args.port, args.baudrate, rx_queue)
    try:
        worker.start()
    except Exception as exc:
        messagebox.showerror("串口打开失败", str(exc))
        return

    app = TitratorApp(worker, Path(args.project_dir).expanduser().resolve())
    app.mainloop()


if __name__ == "__main__":
    main()
