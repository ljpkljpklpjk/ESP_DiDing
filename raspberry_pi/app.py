import json
import os
import queue
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from protocol import build_command, fmt_value
from system_manager import DEFAULT_OTA_PASSWORD, PiSystemManager
from tabs.control_tab import build_control_tab
from tabs.network_tab import build_network_tab
from tabs.update_tab import build_update_tab
from ui_helpers import configure_style


class TitratorApp(tk.Tk):
    def __init__(self, worker, project_dir: Path):
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
        self.mlx_temp_var = tk.StringVar(value="--")
        self.as7341_intensity_var = tk.StringVar(value="--")
        self.as7341_rate_var = tk.StringVar(value="--")
        self.sensor_status_var = tk.StringVar(value="--")
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
        self.log = None
        self.ota_log = None
        self.ota_progress_bar = None

        configure_style(self)
        self._build_ui()
        self.after(100, self._poll_serial)
        self.refresh_wifi_status()

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        control_tab = ttk.Frame(notebook, padding=10)
        network_tab = ttk.Frame(notebook, padding=10)
        update_tab = ttk.Frame(notebook, padding=10)
        notebook.add(control_tab, text="滴定控制")
        notebook.add(network_tab, text="网络设置")
        notebook.add(update_tab, text="系统更新")

        build_control_tab(self, control_tab)
        build_network_tab(self, network_tab)
        build_update_tab(self, update_tab)

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
        payload = build_command(self._next_id(), cmd, **kwargs)
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
        self.ph_var.set(fmt_value(msg.get("ph"), 3))
        self.temp_var.set(fmt_value(msg.get("temperature_c"), 2))
        self.voltage_var.set(fmt_value(msg.get("voltage"), 6))
        self.pwm_display_var.set(fmt_value(msg.get("pwm1_percent"), 1))
        self.pump_display_var.set(fmt_value(msg.get("pump_percent"), 1))
        self.mlx_temp_var.set(fmt_value(msg.get("mlx90640_avg_temp_c"), 2))
        self.as7341_intensity_var.set(fmt_value(msg.get("as7341_intensity"), 0))
        self.as7341_rate_var.set(fmt_value(msg.get("as7341_rate"), 1))
        self.sensor_status_var.set(
            f"AS7341={msg.get('as7341_ok', '--')} MLX90640={msg.get('mlx90640_ok', '--')}"
        )
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
            self.slider_speed_display_var.set(fmt_value(slider.get("speed"), 1))

    def _log(self, text):
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def on_close(self):
        self.worker.stop()
        self.destroy()
