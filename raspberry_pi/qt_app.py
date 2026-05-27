import json
import queue
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QTabWidget, QVBoxLayout, QWidget

from protocol import build_command, first_value, fmt_value
from qt_pages.control_page import ControlPage
from qt_pages.network_page import NetworkPage
from qt_pages.update_page import UpdatePage
from qt_widgets import append_log, make_button
from qt_workers import OtaTask, SystemTask, thread_pool
from system_manager import DEFAULT_OTA_PASSWORD, LinuxSystemManager
from telemetry_logger import TelemetryLogger


class TitratorQtApp(QMainWindow):
    def __init__(self, worker, project_dir: Path, log_dir: Path | None = None, run_id: str | None = None):
        super().__init__()
        self.worker = worker
        self.rx_queue = worker.rx_queue
        self.command_id = 1
        self.system = LinuxSystemManager(project_dir)
        self.ota_running = False
        self.ota_start_time = 0.0
        self.ota_last_output_time = 0.0
        self.pending_telemetry = None
        self.telemetry_logger = TelemetryLogger(project_dir, log_dir=log_dir, run_id=run_id)

        self.setWindowTitle("ESP32 自动滴定仪上位机")
        self.resize(1024, 640)
        self.setMinimumSize(760, 460)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        self.setCentralWidget(central)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 8, 12, 8)
        top_layout.setSpacing(8)
        title = QLabel("ESP32 自动滴定仪")
        title.setObjectName("titleLabel")
        self.status_label = QLabel("已启动，等待 ESP32 遥测...")
        self.ip_label = QLabel("ESP32 IP: --")
        self.status_label.setWordWrap(True)
        self.ip_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ip_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_layout.addWidget(title)
        top_layout.addStretch(1)
        top_layout.addWidget(self.ip_label, 0)
        top_layout.addWidget(self.status_label, 1)
        top_layout.addWidget(make_button("急停", self.emergency_stop, danger=True))
        root.addWidget(top_bar)

        self.tabs = QTabWidget()
        self.control_page = ControlPage(self)
        self.network_page = NetworkPage(self)
        self.update_page = UpdatePage(self, project_dir, DEFAULT_OTA_PASSWORD)
        self.tabs.addTab(self.control_page.root, "滴定控制")
        self.tabs.addTab(self.network_page.root, "网络设置")
        self.tabs.addTab(self.update_page.root, "系统更新")
        root.addWidget(self.tabs, 1)

        self.serial_timer = QTimer(self)
        self.serial_timer.timeout.connect(self.poll_serial)
        self.serial_timer.start(50)

        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.flush_telemetry)
        self.telemetry_timer.start(200)

        self.ota_heartbeat_timer = QTimer(self)
        self.ota_heartbeat_timer.timeout.connect(self.update_ota_heartbeat)

        self.refresh_wifi_status()

    def next_id(self):
        cid = self.command_id
        self.command_id += 1
        return cid

    @staticmethod
    def format_value(value, decimals):
        return fmt_value(value, decimals)

    def run_system_task(self, label, func, on_done):
        on_done(f"{label}中...")
        task = SystemTask(func)

        def finish(code, output):
            prefix = "完成" if code == 0 else "失败"
            on_done(f"{label}{prefix}: {output or '无输出'}")

        task.signals.finished.connect(finish)
        thread_pool().start(task)

    def send_cmd(self, cmd, **kwargs):
        payload = build_command(self.next_id(), cmd, **kwargs)
        try:
            self.worker.send(payload)
            self.log_serial("TX " + json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            QMessageBox.critical(self, "串口发送失败", str(exc))

    def set_slider_speed(self, speed):
        self.send_cmd("slider_speed", speed=float(speed))

    def set_slider_accel(self, accel):
        self.send_cmd("slider_accel", accel=float(accel))

    def move_slider_mm(self, mm):
        self.send_cmd("slider_move_mm", mm=float(mm))

    def move_slider_time(self, mm, sec):
        self.send_cmd("slider_move_time", mm=float(mm), sec=float(sec))

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

    def set_pwm1(self, percent):
        self.send_cmd("set_pwm1", percent=float(percent))

    def set_pump(self, percent):
        self.send_cmd("set_pump", percent=float(percent))

    def pump_stop(self):
        self.send_cmd("pump_stop")

    def reset_dose(self):
        self.send_cmd("reset_dose")

    def refresh_wifi_status(self):
        self.run_system_task("刷新 WiFi 状态", self.system.wifi_status, self.network_page.set_status)

    def wifi_on(self):
        self.run_system_task("打开 WiFi", self.system.wifi_on, self.network_page.set_status)

    def wifi_off(self):
        self.run_system_task("关闭 WiFi", self.system.wifi_off, self.network_page.set_status)

    def connect_wifi(self, ssid, password):
        self.run_system_task("连接 WiFi", lambda: self.system.connect_wifi(ssid.strip(), password), self.network_page.set_status)

    def check_project_update(self, project_dir):
        self.system.project_dir = Path(project_dir).expanduser().resolve()
        self.run_system_task("检查项目更新", self.system.check_git_update, self.update_page.set_status)

    def update_project(self, project_dir):
        self.system.project_dir = Path(project_dir).expanduser().resolve()
        self.run_system_task("更新上位机代码", self.system.update_project, self.update_page.set_status)

    def update_esp32_ota(self, project_dir, host, password):
        if self.ota_running:
            self.update_page.set_status("ESP32 OTA 正在运行，请等待当前任务完成")
            return
        host = host.strip()
        self.system.project_dir = Path(project_dir).expanduser().resolve()
        self.update_page.refresh_firmware()
        if not host:
            self.update_page.set_status("ESP32 OTA 更新失败: 请输入 ESP32 IP")
            return
        if not self.system.firmware_path().exists():
            self.update_page.set_status(f"ESP32 OTA 更新失败: 未找到预编译固件 {self.system.firmware_path()}")
            return

        cmd = self.system.ota_command(host, password)
        self.ota_running = True
        self.ota_start_time = time.time()
        self.ota_last_output_time = self.ota_start_time
        self.update_page.set_status("ESP32 OTA 更新中...")
        self.update_page.set_progress("准备上传预编译固件...")
        self.update_page.set_ota_running(True)
        self.update_page.log.clear()
        append_log(self.update_page.log, self.system.firmware_version_text(), max_lines=800)
        append_log(self.update_page.log, "执行命令: " + " ".join(cmd), max_lines=800)
        self.ota_heartbeat_timer.start(1000)

        task = OtaTask(cmd, self.system.project_dir)
        task.signals.line.connect(self.update_ota_progress)
        task.signals.finished.connect(self.finish_ota)
        thread_pool().start(task)

    def update_ota_progress(self, line):
        self.ota_last_output_time = time.time()
        progress = self.ota_progress_text(line)
        self.update_page.set_progress(progress)
        self.update_page.set_status(line)
        append_log(self.update_page.log, line, max_lines=800)

    def update_ota_heartbeat(self):
        if not self.ota_running:
            return
        now = time.time()
        elapsed = int(now - self.ota_start_time)
        idle = int(now - self.ota_last_output_time)
        self.update_page.set_progress(f"OTA 运行中，已用 {elapsed}s，最近输出 {idle}s 前")

    def finish_ota(self, code, last_line):
        self.ota_running = False
        self.ota_heartbeat_timer.stop()
        self.update_page.set_ota_running(False)
        if code == 0:
            self.update_page.set_progress("OTA 完成，等待 ESP32 重启并恢复遥测")
            self.update_page.set_status("ESP32 OTA 更新完成")
            append_log(self.update_page.log, "OTA 任务完成", max_lines=800)
        else:
            self.update_page.set_progress(f"OTA 失败: {last_line or '无输出'}")
            self.update_page.set_status("ESP32 OTA 更新失败")
            append_log(self.update_page.log, f"OTA 任务失败: {last_line or '无输出'}", max_lines=800)

    @staticmethod
    def ota_progress_text(line):
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
        if "success" in lower:
            return "OTA 成功"
        if "error" in lower or "failed" in lower:
            return "OTA 出错，请查看实时输出"
        return line

    def poll_serial(self):
        deadline = time.monotonic() + 0.02
        processed = 0
        while processed < 20 and time.monotonic() < deadline:
            try:
                msg = self.rx_queue.get_nowait()
            except queue.Empty:
                break
            self.handle_message(msg)
            processed += 1

    def handle_message(self, msg):
        msg_type = msg.get("type")
        if self.is_telemetry_message(msg):
            self.pending_telemetry = msg
            return
        self.log_serial("RX " + json.dumps(msg, ensure_ascii=False))
        if msg_type == "boot":
            self.status_label.setText("ESP32 已启动")
            if "slider" in msg:
                self.control_page.update_slider(msg["slider"])
        elif msg_type == "ack":
            self.status_label.setText(f"命令 {msg.get('id', '--')} 已确认")
        elif msg_type == "done":
            self.status_label.setText(f"命令 {msg.get('id', '--')} 完成 ok={msg.get('ok')}")
        elif msg_type == "error":
            self.status_label.setText(f"错误: {msg.get('code', msg.get('message', '--'))}")
        elif msg_type == "serial_error":
            self.status_label.setText(f"串口错误: {msg.get('message', '--')}")

    @staticmethod
    def is_telemetry_message(msg):
        if not isinstance(msg, dict):
            return False
        if msg.get("type") == "telemetry":
            return True
        telemetry_keys = (
            "ph", "pH", "voltage", "voltage_v", "temperature_c", "temp_c",
            "tds_ppm", "tds_voltage", "tof_distance_mm", "bme280_temperature_c",
            "bme280_humidity_percent", "bme280_pressure_hpa", "absorbance_au",
            "concentration", "flow_ml_min", "dosing_volume_ml",
            "pwm1_percent", "pump_percent", "as7341_intensity",
            "mlx90640_avg_temp_c", "slider", "wifi_connected", "ota_ready",
        )
        return any(key in msg for key in telemetry_keys)

    def update_telemetry(self, msg):
        ip = first_value(msg, "ip", "esp32_ip")
        if ip:
            self.ip_label.setText(f"ESP32 IP: {ip}")
            self.update_page.set_esp32_ip(ip)
        self.control_page.update_telemetry(msg)

    def flush_telemetry(self):
        if not self.pending_telemetry:
            return
        msg = self.pending_telemetry
        self.pending_telemetry = None
        self.log_serial("RX " + json.dumps(msg, ensure_ascii=False))
        self.telemetry_logger.write(msg)
        self.update_telemetry(msg)

    def log_serial(self, text):
        append_log(self.control_page.log, text)

    def closeEvent(self, event):
        self.worker.stop()
        self.telemetry_logger.close()
        event.accept()
