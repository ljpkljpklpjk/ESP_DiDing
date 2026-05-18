from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout

from qt_widgets import ValueCard, add_cards_grid, input_row, make_button, make_line_edit, make_log, make_panel, page_widget


class ControlPage:
    def __init__(self, app):
        self.app = app
        self.root, layout = page_widget()

        self.ph = ValueCard("pH", "--", "#0f4ea3")
        self.temp = ValueCard("DS18B20 ℃", "--")
        self.voltage = ValueCard("电压 V", "--")
        self.mlx_temp = ValueCard("MLX90640 ℃", "--", "#b45309")
        self.pwm = ValueCard("PWM1 %", "0")
        self.pump = ValueCard("蠕动泵 %", "0")
        self.as_intensity = ValueCard("AS7341 强度", "--")
        self.as_rate = ValueCard("AS7341 变化率", "--")
        add_cards_grid(layout, [self.ph, self.temp, self.voltage, self.mlx_temp, self.pwm, self.pump, self.as_intensity, self.as_rate], 4)

        sensor_panel, sensor_layout = make_panel("AS7341 原始通道")
        self.as_channels = []
        channel_grid = QGridLayout()
        channel_grid.setSpacing(8)
        for i in range(12):
            card = ValueCard(f"CH{i}", "0")
            self.as_channels.append(card)
            channel_grid.addWidget(card, i // 6, i % 6)
        sensor_layout.addLayout(channel_grid)
        layout.addWidget(sensor_panel)

        slider_panel, slider_layout = make_panel("丝杆滑台")
        self.slider_pos = ValueCard("当前位置", "--")
        self.slider_target = ValueCard("目标位置", "--")
        self.slider_distance = ValueCard("剩余步数", "--")
        self.slider_enabled = ValueCard("已使能", "--")
        self.slider_moving = ValueCard("运动中", "--")
        self.slider_speed = ValueCard("当前速度", "1000")
        add_cards_grid(slider_layout, [self.slider_pos, self.slider_target, self.slider_distance, self.slider_enabled, self.slider_moving, self.slider_speed], 6)

        self.speed_edit = make_line_edit("1000")
        self.accel_edit = make_line_edit("500")
        self.mm_edit = make_line_edit("10")
        self.sec_edit = make_line_edit("20")
        slider_layout.addLayout(input_row("速度 steps/s", self.speed_edit, "设置速度", lambda: app.set_slider_speed(self.speed_edit.text()), True)[0])
        slider_layout.addLayout(input_row("加速度", self.accel_edit, "设置加速度", lambda: app.set_slider_accel(self.accel_edit.text()))[0])
        slider_layout.addLayout(input_row("距离 mm", self.mm_edit, "移动距离", lambda: app.move_slider_mm(self.mm_edit.text()), True)[0])
        slider_layout.addLayout(input_row("时间 s", self.sec_edit, "按时间移动", lambda: app.move_slider_time(self.mm_edit.text(), self.sec_edit.text()))[0])

        action_row = QHBoxLayout()
        for button in [
            make_button("使能", app.slider_enable, True),
            make_button("关闭使能", app.slider_disable),
            make_button("停止", app.slider_stop),
            make_button("立即停止", app.slider_halt),
            make_button("清零", app.slider_zero),
            make_button("急停", app.emergency_stop, danger=True),
        ]:
            action_row.addWidget(button)
        slider_layout.addLayout(action_row)
        layout.addWidget(slider_panel)

        pump_panel, pump_layout = make_panel("PWM / 蠕动泵")
        self.pwm_edit = make_line_edit("0")
        self.pump_edit = make_line_edit("0")
        pump_layout.addLayout(input_row("PWM1 %", self.pwm_edit, "设置 PWM1", lambda: app.set_pwm1(self.pwm_edit.text()), True)[0])
        pump_layout.addLayout(input_row("蠕动泵 %", self.pump_edit, "设置蠕动泵", lambda: app.set_pump(self.pump_edit.text()), True)[0])
        pump_layout.addWidget(make_button("停止蠕动泵", app.pump_stop))
        layout.addWidget(pump_panel)

        log_panel, log_layout = make_panel("通信日志")
        self.log = make_log()
        log_layout.addWidget(self.log)
        layout.addWidget(log_panel, 1)

    def update_telemetry(self, msg):
        self.ph.set_value(self.app.format_value(msg.get("ph"), 3))
        self.temp.set_value(self.app.format_value(msg.get("temperature_c"), 2))
        self.voltage.set_value(self.app.format_value(msg.get("voltage"), 6))
        self.mlx_temp.set_value(self.app.format_value(msg.get("mlx90640_avg_temp_c"), 2))
        self.pwm.set_value(self.app.format_value(msg.get("pwm1_percent"), 1))
        self.pump.set_value(self.app.format_value(msg.get("pump_percent"), 1))
        self.as_intensity.set_value(self.app.format_value(msg.get("as7341_intensity"), 0))
        self.as_rate.set_value(self.app.format_value(msg.get("as7341_rate"), 1))
        channels = msg.get("as7341_channels")
        if isinstance(channels, list):
            for card, value in zip(self.as_channels, channels):
                card.set_value(value)
        slider = msg.get("slider")
        if isinstance(slider, dict):
            self.update_slider(slider)

    def update_slider(self, slider):
        self.slider_pos.set_value(slider.get("pos", "--"))
        self.slider_target.set_value(slider.get("target", "--"))
        self.slider_distance.set_value(slider.get("distance", "--"))
        self.slider_enabled.set_value(slider.get("enabled", "--"))
        self.slider_moving.set_value(slider.get("moving", "--"))
        self.slider_speed.set_value(self.app.format_value(slider.get("speed"), 1))
