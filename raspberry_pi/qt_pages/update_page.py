from PySide6.QtWidgets import QLabel, QProgressBar

from qt_widgets import ValueCard, input_row, make_button, make_line_edit, make_log, make_panel, page_widget


class UpdatePage:
    def __init__(self, app, project_dir, ota_password):
        self.app = app
        self.root, layout = page_widget()

        info_panel, info_layout = make_panel("Gitee / OTA 更新")
        self.project_edit = make_line_edit(str(project_dir))
        self.host_edit = make_line_edit("")
        self.password_edit = make_line_edit(ota_password, password=True)
        self.status = ValueCard("更新状态", "未检查")
        self.progress_text = ValueCard("OTA 进度", "OTA 未开始")
        self.firmware = ValueCard("固件信息", app.system.firmware_version_text())
        info_layout.addLayout(input_row("项目路径", self.project_edit)[0])
        info_layout.addLayout(input_row("ESP32 IP", self.host_edit)[0])
        info_layout.addLayout(input_row("OTA 密码", self.password_edit)[0])
        info_layout.addWidget(self.firmware)
        info_layout.addWidget(self.status)
        info_layout.addWidget(self.progress_text)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        info_layout.addWidget(self.progress_bar)
        self.check_button = make_button("检查 Gitee 更新", lambda: app.check_project_update(self.project_edit.text()))
        self.update_button = make_button("从 Gitee 更新代码", lambda: app.update_project(self.project_edit.text()), True)
        self.ota_button = make_button("更新 ESP32 固件 OTA", lambda: app.update_esp32_ota(self.project_edit.text(), self.host_edit.text(), self.password_edit.text()), True)
        info_layout.addWidget(self.check_button)
        info_layout.addWidget(self.update_button)
        info_layout.addWidget(self.ota_button)
        layout.addWidget(info_panel)

        log_panel, log_layout = make_panel("OTA 实时输出")
        self.log = make_log()
        log_layout.addWidget(self.log)
        layout.addWidget(log_panel, 1)

    def set_esp32_ip(self, ip):
        if ip and not self.host_edit.text().strip():
            self.host_edit.setText(str(ip))

    def set_status(self, text):
        self.status.set_value(text)

    def set_progress(self, text):
        self.progress_text.set_value(text)

    def set_ota_running(self, running):
        self.ota_button.setEnabled(not running)
        if running:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)

    def refresh_firmware(self):
        self.firmware.set_value(self.app.system.firmware_version_text())
