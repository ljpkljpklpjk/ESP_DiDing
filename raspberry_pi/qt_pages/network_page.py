from qt_widgets import ValueCard, input_row, make_button, make_line_edit, make_panel, page_widget


class NetworkPage:
    def __init__(self, app):
        self.app = app
        self.root, layout = page_widget()

        # ── ESP32 (下位机) WiFi ──────────────────────────────────────
        esp32_panel, esp32_layout = make_panel("ESP32 下位机 WiFi")
        self.esp32_status = ValueCard("当前连接", "等待遥测...")
        esp32_layout.addWidget(self.esp32_status)
        self.esp32_ssid = make_line_edit("")
        self.esp32_password = make_line_edit("", password=True)
        esp32_layout.addLayout(input_row("SSID", self.esp32_ssid)[0])
        esp32_layout.addLayout(input_row("密码", self.esp32_password)[0])
        esp32_layout.addWidget(
            make_button(
                "ESP32 连接 WiFi",
                lambda: app.connect_esp32_wifi(
                    self.esp32_ssid.text(), self.esp32_password.text()
                ),
                primary=True,
            )
        )
        layout.addWidget(esp32_panel)

        # ── SH800 (上位机) WiFi ──────────────────────────────────────
        status_panel, status_layout = make_panel("SH800 上位机 WiFi")
        self.status = ValueCard("当前状态", "未刷新")
        status_layout.addWidget(self.status)
        layout.addWidget(status_panel)

        control_panel, control_layout = make_panel("上位机网络控制")
        self.ssid_edit = make_line_edit("Lab807_2.4G")
        self.password_edit = make_line_edit("", password=True)
        control_layout.addLayout(input_row("SSID", self.ssid_edit)[0])
        control_layout.addLayout(input_row("密码", self.password_edit)[0])
        control_layout.addWidget(
            make_button(
                "连接 WiFi",
                lambda: app.connect_wifi(
                    self.ssid_edit.text(), self.password_edit.text()
                ),
                primary=True,
            )
        )
        control_layout.addWidget(make_button("刷新 WiFi 状态", app.refresh_wifi_status))
        control_layout.addWidget(make_button("打开 WiFi", app.wifi_on))
        control_layout.addWidget(make_button("关闭 WiFi", app.wifi_off))
        layout.addWidget(control_panel)
        layout.addStretch(1)

    def set_status(self, text):
        self.status.set_value(text)

    def set_esp32_status(self, text):
        self.esp32_status.set_value(text)
