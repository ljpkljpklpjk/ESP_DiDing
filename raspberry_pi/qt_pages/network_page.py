from qt_widgets import ValueCard, input_row, make_button, make_line_edit, make_panel, page_widget


class NetworkPage:
    def __init__(self, app):
        self.app = app
        self.root, layout = page_widget()

        status_panel, status_layout = make_panel("树莓派 WiFi")
        self.status = ValueCard("当前状态", "未刷新")
        status_layout.addWidget(self.status)
        layout.addWidget(status_panel)

        control_panel, control_layout = make_panel("网络控制")
        self.ssid_edit = make_line_edit("Lab807_2.4G")
        self.password_edit = make_line_edit("", password=True)
        control_layout.addLayout(input_row("SSID", self.ssid_edit)[0])
        control_layout.addLayout(input_row("密码", self.password_edit)[0])
        control_layout.addWidget(make_button("连接 WiFi", lambda: app.connect_wifi(self.ssid_edit.text(), self.password_edit.text()), True))
        control_layout.addWidget(make_button("刷新 WiFi 状态", app.refresh_wifi_status))
        control_layout.addWidget(make_button("打开 WiFi", app.wifi_on))
        control_layout.addWidget(make_button("关闭 WiFi", app.wifi_off))
        layout.addWidget(control_panel)
        layout.addStretch(1)

    def set_status(self, text):
        self.status.set_value(text)
